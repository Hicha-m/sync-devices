"""AUTH-001 integration tests. Uses an isolated SQLite file per test."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sync_devices.auth import create_app, stamp
from sync_devices.db import connect

SECRET = "a" * 48


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "auth.db"
        self.client = TestClient(create_app(self.path, bootstrap_secret=SECRET, allow_insecure_http=True))
        self.client.__enter__()
        self.admin = self.bootstrap()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def device(self, name="Laptop", platform="linux", key="z" * 40):
        return {"name": name, "platform": platform, "identity_public_key": key}

    def bootstrap(self):
        response = self.client.post("/auth/bootstrap", json={
            **self.device(), "bootstrap_secret": SECRET, "username": "admin",
            "display_name": "Admin",
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def headers(self, session=None):
        return {"Authorization": "Bearer " + (session or self.admin["access_token"])}

    def pair(self, user_id=None):
        invite = self.client.post(
            "/auth/pairing-invites", headers=self.headers(),
            json={"user_id": user_id or self.admin["user_id"]},
        )
        self.assertEqual(invite.status_code, 201, invite.text)
        code = invite.json()["pairing_code"]
        response = self.client.post("/auth/pair", json={
            **self.device("Phone", "android", "y" * 40), "pairing_code": code,
        })
        return code, response

    def test_bootstrap_is_single_use(self):
        response = self.client.post("/auth/bootstrap", json={
            **self.device("Other", "linux", "x" * 40),
            "bootstrap_secret": SECRET, "username": "other", "display_name": "Other",
        })
        self.assertEqual(response.status_code, 409)

    def test_wrong_bootstrap_secret_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with TestClient(create_app(Path(directory) / "empty.db", bootstrap_secret=SECRET,
                                       allow_insecure_http=True)) as new_client:
                result = new_client.post("/auth/bootstrap", json={
                    **self.device(), "bootstrap_secret": "wrong",
                    "username": "admin", "display_name": "Admin",
                })
                self.assertEqual(result.status_code, 403)

    def test_requires_auth_for_device_list(self):
        self.assertEqual(self.client.get("/auth/devices").status_code, 401)
        self.assertEqual(self.client.get("/auth/devices", headers=self.headers("invalid" * 9)).status_code, 401)

    def test_admin_is_authenticated(self):
        response = self.client.get("/auth/me", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_admin"])

    def test_pairing_code_is_single_use(self):
        code, response = self.pair()
        self.assertEqual(response.status_code, 201, response.text)
        retry = self.client.post("/auth/pair", json={
            **self.device("Other", "windows", "x" * 40),
            "pairing_code": code,
        })
        self.assertEqual(retry.status_code, 401)

    def test_pairing_code_expiry(self):
        invitation = self.client.post("/auth/pairing-invites", headers=self.headers(),
                                      json={"user_id": self.admin["user_id"]}).json()
        db = connect(self.path)
        db.execute("UPDATE pairing_invites SET expires_at='2000-01-01T00:00:00+00:00'")
        db.commit()
        db.close()
        result = self.client.post("/auth/pair", json={
            **self.device("Tablet", "ipados", "k" * 40),
            "pairing_code": invitation["pairing_code"],
        })
        self.assertEqual(result.status_code, 401)

    def test_login_with_device_secret_and_reject_bad_secret(self):
        self.assertEqual(self.client.post("/auth/login", json={
            "device_id": self.admin["device_id"], "device_secret": "bad",
        }).status_code, 401)
        response = self.client.post("/auth/login", json={
            "device_id": self.admin["device_id"], "device_secret": self.admin["device_secret"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/auth/me", headers=self.headers(
            response.json()["access_token"])).status_code, 200)

    def test_expired_session_is_rejected(self):
        db = connect(self.path)
        db.execute("UPDATE auth_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
        db.commit()
        db.close()
        self.assertEqual(self.client.get("/auth/me", headers=self.headers()).status_code, 401)

    def test_revocation_prevents_login_and_existing_session(self):
        _, response = self.pair()
        phone = response.json()
        result = self.client.post("/auth/devices/" + phone["device_id"] + "/revoke",
                                  headers=self.headers())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get("/auth/me", headers=self.headers(
            phone["access_token"])).status_code, 401)
        self.assertEqual(self.client.post("/auth/login", json={
            "device_id": phone["device_id"], "device_secret": phone["device_secret"],
        }).status_code, 401)

    def test_only_admin_can_invite_and_add_users(self):
        created = self.client.post("/admin/users", json={
            "username": "guest", "display_name": "Guest",
        }, headers=self.headers())
        self.assertEqual(created.status_code, 201)
        _, phone = self.pair(created.json()["user_id"])
        self.assertEqual(phone.status_code, 201)
        guest = self.headers(phone.json()["access_token"])
        self.assertEqual(self.client.post("/admin/users", json={
            "username": "another", "display_name": "Another",
        }, headers=guest).status_code, 403)
        self.assertEqual(self.client.post("/auth/pairing-invites", json={
            "user_id": created.json()["user_id"],
        }, headers=guest).status_code, 403)

    def test_nonadmin_cannot_revoke_other_user(self):
        created = self.client.post("/admin/users", json={
            "username": "guest", "display_name": "Guest",
        }, headers=self.headers()).json()
        _, phone = self.pair(created["user_id"])
        response = self.client.post(
            "/auth/devices/" + self.admin["device_id"] + "/revoke",
            headers=self.headers(phone.json()["access_token"]),
        )
        self.assertEqual(response.status_code, 403)

    def test_secret_never_stored_in_plaintext(self):
        db = connect(self.path)
        rows = db.execute("SELECT secret_hash FROM device_credentials").fetchall()
        sessions = db.execute("SELECT token_hash FROM auth_sessions").fetchall()
        db.close()
        self.assertNotIn(self.admin["device_secret"], [x[0] for x in rows])
        self.assertNotIn(self.admin["access_token"], [x[0] for x in sessions])

    def test_requires_https_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            with TestClient(create_app(Path(directory) / "tls.db",
                                       bootstrap_secret=SECRET)) as client:
                self.assertEqual(client.get("/health").status_code, 403)
                self.assertEqual(client.get("/health", headers={"X-Forwarded-Proto": "https"}).status_code, 403)

    def test_device_identity_key_unique(self):
        _, phone = self.pair()
        self.assertEqual(phone.status_code, 201)
        invite = self.client.post("/auth/pairing-invites", headers=self.headers(),
                                  json={"user_id": self.admin["user_id"]}).json()
        response = self.client.post("/auth/pair", json={
            **self.device("Second phone", "android", "y" * 40),
            "pairing_code": invite["pairing_code"],
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post("/auth/pair", json={
            **self.device("Different device", "android", "v" * 40),
            "pairing_code": invite["pairing_code"],
        }).status_code, 201)


if __name__ == "__main__":
    unittest.main()
