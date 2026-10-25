"""AUTH-001: small, explicit bearer-token authentication with one-time pairing.

Device identity is proven by possession of its issued random credential, NOT by the
(unverified) client-supplied identity_public_key. Treat the credential as a password.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .db import connect

SESSION_TTL = timedelta(hours=24)
INVITE_TTL = timedelta(minutes=5)
PLATFORMS = {"windows", "linux", "android", "ipados", "other"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(value: datetime | None = None) -> str:
    return (value or now()).isoformat(timespec="microseconds")


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def token() -> str:
    return secrets.token_urlsafe(32)


@contextmanager
def database(path: str | Path):
    db = connect(path)
    try:
        yield db
    finally:
        db.close()


class DeviceInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    platform: str
    identity_public_key: str = Field(min_length=32, max_length=512)


class BootstrapInput(DeviceInput):
    bootstrap_secret: str
    username: str = Field(min_length=3, max_length=40)
    display_name: str = Field(min_length=1, max_length=80)


class NewUserInput(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    display_name: str = Field(min_length=1, max_length=80)


class InviteInput(BaseModel):
    user_id: str


class ClaimInput(DeviceInput):
    pairing_code: str


class LoginInput(BaseModel):
    device_id: str
    device_secret: str


def create_app(
    database_path: str | Path = "local/sync-devices.db",
    bootstrap_secret: str | None = None,
    allow_insecure_http: bool = False,
) -> FastAPI:
    """Development can allow HTTP explicitly; deployment must use HTTPS.

    In production, configure a trusted TLS-terminating reverse proxy that forwards
    requests using HTTPS. Do not pass allow_insecure_http=True on LAN interfaces.
    """
    path = database_path
    configured_secret = bootstrap_secret if bootstrap_secret is not None else os.getenv("SYNC_BOOTSTRAP_SECRET", "")
    if not configured_secret or len(configured_secret) < 32:
        raise RuntimeError("Set SYNC_BOOTSTRAP_SECRET to at least 32 random characters")
    app = FastAPI(title="Sync Devices authentication", version="0.1.0")
    with database(path):
        pass  # schema migrations completed at startup

    @app.middleware("http")
    async def require_https(request: Request, call_next):
        if not allow_insecure_http and request.url.scheme != "https":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"detail": "HTTPS required"})
        return await call_next(request)

    def actor(db: sqlite3.Connection, authorization: str | None):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer authentication required")
        raw = authorization[len("Bearer "):]
        if len(raw) < 32 or len(raw) > 256:
            raise HTTPException(401, "Invalid session")
        result = db.execute(
            """SELECT d.id AS device_id, u.id AS user_id, u.is_admin, s.expires_at
               FROM auth_sessions s
               JOIN devices d ON d.id=s.device_id
               JOIN users u ON u.id=d.owner_user_id
               WHERE s.token_hash=? AND d.revoked_at IS NULL""",
            (fingerprint(raw),),
        ).fetchone()
        if result is None or result["expires_at"] <= stamp():
            raise HTTPException(401, "Invalid or expired session")
        return result

    def admin(db, authorization):
        current = actor(db, authorization)
        if not current["is_admin"]:
            raise HTTPException(403, "Administrator required")
        return current

    def create_device(db, user_id: str, data: DeviceInput):
        if data.platform not in PLATFORMS:
            raise HTTPException(422, "Unsupported platform")
        device_id = str(uuid.uuid4())
        credential = token()
        session = token()
        db.execute(
            "INSERT INTO devices(id,owner_user_id,name,platform,identity_public_key) "
            "VALUES (?,?,?,?,?)",
            (device_id, user_id, data.name, data.platform, data.identity_public_key),
        )
        db.execute(
            "INSERT INTO device_credentials(device_id,secret_hash,created_at) VALUES (?,?,?)",
            (device_id, fingerprint(credential), stamp()),
        )
        db.execute(
            "INSERT INTO auth_sessions(token_hash,device_id,expires_at,created_at) VALUES (?,?,?,?)",
            (fingerprint(session), device_id, stamp(now() + SESSION_TTL), stamp()),
        )
        return {"device_id": device_id, "device_secret": credential, "access_token": session,
                "expires_in_seconds": int(SESSION_TTL.total_seconds())}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/auth/bootstrap", status_code=201)
    def bootstrap(data: BootstrapInput):
        if not secrets.compare_digest(data.bootstrap_secret, configured_secret):
            raise HTTPException(403, "Invalid bootstrap secret")
        with database(path) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                    raise HTTPException(409, "Instance already initialized")
                user_id = str(uuid.uuid4())
                db.execute(
                    "INSERT INTO users(id,username,display_name,is_admin) VALUES (?,?,?,1)",
                    (user_id, data.username, data.display_name),
                )
                result = create_device(db, user_id, data)
                db.commit()
                return {"user_id": user_id, **result}
            except sqlite3.IntegrityError:
                db.rollback()
                raise HTTPException(409, "Device identity or username already exists")
            except Exception:
                db.rollback()
                raise

    @app.post("/auth/login")
    def login(data: LoginInput):
        with database(path) as db:
            row = db.execute(
                """SELECT c.secret_hash FROM device_credentials c
                   JOIN devices d ON d.id=c.device_id
                   WHERE c.device_id=? AND d.revoked_at IS NULL""",
                (data.device_id,),
            ).fetchone()
            if row is None or not secrets.compare_digest(row["secret_hash"], fingerprint(data.device_secret)):
                raise HTTPException(401, "Invalid device credentials")
            session = token()
            db.execute(
                "INSERT INTO auth_sessions(token_hash,device_id,expires_at,created_at) VALUES (?,?,?,?)",
                (fingerprint(session), data.device_id, stamp(now() + SESSION_TTL), stamp()),
            )
            db.commit()
            return {"access_token": session, "expires_in_seconds": int(SESSION_TTL.total_seconds())}

    @app.get("/auth/me")
    def me(authorization: str | None = Header(default=None)):
        with database(path) as db:
            me = actor(db, authorization)
            return {"user_id": me["user_id"], "device_id": me["device_id"],
                    "is_admin": bool(me["is_admin"])}

    @app.post("/admin/users", status_code=201)
    def add_user(data: NewUserInput, authorization: str | None = Header(default=None)):
        with database(path) as db:
            admin(db, authorization)
            user_id = str(uuid.uuid4())
            try:
                db.execute(
                    "INSERT INTO users(id,username,display_name) VALUES (?,?,?)",
                    (user_id, data.username, data.display_name),
                )
                db.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Username already taken")
            return {"user_id": user_id}

    @app.post("/auth/pairing-invites", status_code=201)
    def invite(data: InviteInput, authorization: str | None = Header(default=None)):
        with database(path) as db:
            current = admin(db, authorization)
            if not db.execute("SELECT 1 FROM users WHERE id=?", (data.user_id,)).fetchone():
                raise HTTPException(404, "User not found")
            invitation = token()
            expiry = stamp(now() + INVITE_TTL)
            db.execute(
                "INSERT INTO pairing_invites(token_hash,target_user_id,created_by_device_id,expires_at) "
                "VALUES (?,?,?,?)",
                (fingerprint(invitation), data.user_id, current["device_id"], expiry),
            )
            db.commit()
            return {"pairing_code": invitation, "expires_at": expiry}

    @app.post("/auth/pair", status_code=201)
    def pair(data: ClaimInput):
        if len(data.pairing_code) < 32 or len(data.pairing_code) > 256:
            raise HTTPException(401, "Invalid or expired pairing code")
        with database(path) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    """SELECT i.target_user_id FROM pairing_invites i
                       JOIN devices d ON d.id=i.created_by_device_id
                       WHERE i.token_hash=? AND i.used_at IS NULL AND i.expires_at>?
                         AND d.revoked_at IS NULL""",
                    (fingerprint(data.pairing_code), stamp()),
                ).fetchone()
                if row is None:
                    raise HTTPException(401, "Invalid or expired pairing code")
                result = create_device(db, row["target_user_id"], data)
                db.execute(
                    "UPDATE pairing_invites SET used_at=? WHERE token_hash=?",
                    (stamp(), fingerprint(data.pairing_code)),
                )
                db.commit()
                return result
            except sqlite3.IntegrityError:
                db.rollback()
                raise HTTPException(409, "Device identity already registered")
            except Exception:
                db.rollback()
                raise

    @app.get("/auth/devices")
    def devices(authorization: str | None = Header(default=None)):
        with database(path) as db:
            current = actor(db, authorization)
            rows = db.execute(
                "SELECT id,name,platform,paired_at,revoked_at FROM devices "
                "WHERE owner_user_id=? ORDER BY paired_at",
                (current["user_id"],),
            ).fetchall()
            return {"devices": [dict(row) for row in rows]}

    @app.post("/auth/devices/{device_id}/revoke")
    def revoke(device_id: str, authorization: str | None = Header(default=None)):
        with database(path) as db:
            current = actor(db, authorization)
            row = db.execute("SELECT owner_user_id,revoked_at FROM devices WHERE id=?", (device_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Device not found")
            if row["owner_user_id"] != current["user_id"] and not current["is_admin"]:
                raise HTTPException(403, "Cannot revoke another user's device")
            if row["revoked_at"] is None:
                db.execute("UPDATE devices SET revoked_at=? WHERE id=?", (stamp(), device_id))
                db.execute("DELETE FROM auth_sessions WHERE device_id=?", (device_id,))
                db.execute("DELETE FROM device_credentials WHERE device_id=?", (device_id,))
                db.execute("DELETE FROM pairing_invites WHERE created_by_device_id=? AND used_at IS NULL", (device_id,))
                db.commit()
            return {"revoked": True, "device_id": device_id}

    return app
