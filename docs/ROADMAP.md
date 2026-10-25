# Roadmap and acceptance checks

- [x] **FND-001** Define data model for users, devices, spaces, rooms, messages, attachment metadata and cursors.
- [x] **FND-002** SQLite v1 schema with referential constraints, indexes, retry uniqueness and stdlib unit tests.
- [x] **AUTH-001 (API foundation)** Single-use bootstrap, admin-approved device pairing, sessions and revocation with integration tests.
- [ ] **AUTH-002 (hardening)** Rate limiting, security audit log, bootstrap secret rotation/removal, signed device public-key challenges, production HTTPS reverse proxy and safe PWA credential storage.
- [ ] **API-001** Authenticated room read/write API and idempotent text send.
- [ ] **SYNC-001** Server-assigned cursor replay after an hour offline; no lost or duplicate messages.
- [ ] **SIGNAL-001** Authenticated WebSocket and WebRTC signaling (no file relaying).
- [ ] **P2P-001** Direct encrypted WebRTC DataChannel for a photo and a file between two desktops.
- [ ] **P2P-002** Bounded memory, integrity hash, progress UI and interruption recovery.
- [ ] **PWA-001** Install and test on Windows, Linux, Android and iPad; trusted local HTTPS.
- [ ] **QA-001** Browser E2E (WebdriverIO), disconnect/reconnect, permissions, P2P failure, server RAM/disk budget.
- [ ] **OPS-001** Minimal Docker Compose, backup/restore and health/monitoring.

## First vertical slice

After authentication hardening, two paired browsers in one room exchange a text message. Close one browser, send a message, reopen it and assert exactly-once history replay. File transfer is a later milestone.
