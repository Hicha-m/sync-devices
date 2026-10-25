# Sync Devices

**A LAN-first community messenger with direct peer-to-peer file transfer.**

Target platforms: Windows, Linux, Android and iPad (first as a web app/PWA, without requiring a Mac).

## Core behavior

- A tiny always-on Linux server (target: **500 MB RAM, 16 GB storage**) owns accounts, devices, spaces, rooms, text messages, membership and attachment **metadata**.
- Every user's devices can retrieve missed messages after reconnecting, even when the sender is offline.
- File, photo and video **bytes never pass through or persist on the server**. They are offered directly from the source device to another via WebRTC DataChannels. When that device or its app is unavailable, new downloads are unavailable.
- A recipient who has already saved a file keeps their local copy.
- No artificial file-size cap is planned, but browser storage, disk capacity and iPadOS suspension are real limitations.
- P2P negotiation uses the server for WebSocket signaling only. There is **no TURN relay** in the LAN MVP. Failed P2P connections must fail visibly rather than silently proxy through the server.

## Status

**Foundation only, not yet a running chat application.** This branch defines the first SQLite schema and automated tests. Do not expose it publicly; authentication, transport and UI are upcoming milestones.

## Developer quick start

Python 3.11+; the database module uses only Python's standard library.

```bash
git clone https://github.com/Hicha-m/sync-devices.git
cd sync-devices
python -m unittest discover -s server/tests -v
```

To initialize a local SQLite file:

```bash
PYTHONPATH=server python -c "from sync_devices.db import connect; db=connect('local/sync-devices.db'); print('SQLite schema version:', db.execute('PRAGMA user_version').fetchone()[0]); db.close()"
```

The `local/` directory is ignored by Git.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database and entity model](docs/DATABASE.md)
- [P2P and synchronization protocol](docs/PROTOCOL.md)
- [Security and trust boundaries](docs/SECURITY.md)
- [Incremental roadmap](docs/ROADMAP.md)

## License

No license has been selected yet. All rights remain with the copyright holder until a license is added.
