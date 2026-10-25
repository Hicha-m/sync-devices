# Sync Devices

**A LAN-first community messenger with direct peer-to-peer file transfer.**

Target platforms: Windows, Linux, Android and iPad (first as a PWA, without requiring a Mac).

- Lightweight always-on Linux server (target **500 MB RAM, 16 GB storage**) stores accounts, spaces, text messages and file metadata.
- Binary photos/videos/files **never** pass through the server: eventual transfer directly between authorized devices by WebRTC.
- Messages can be caught up after reconnecting; file downloads require the original sender app to be reachable.
- Current implementation: SQLite schema v2, device onboarding/auth API, and tests. **No chat UI, message API or P2P transfer exists yet.**

## Test

Python 3.11+:

```bash
python -m pip install -r server/requirements-dev.txt
python -m unittest discover -s server/tests -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database](docs/DATABASE.md)
- [Authentication and pairing](docs/AUTH.md)
- [Protocol](docs/PROTOCOL.md)
- [Security](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)

Do **not** expose this prototype to the Internet or untrusted LANs; see security hardening tasks before production deployment.
