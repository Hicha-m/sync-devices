# Roadmap and acceptance checks

- [x] **FND-001** Define data model for users, devices, spaces, rooms, messages, attachment metadata and cursors.
- [x] **FND-002** SQLite v1 schema with referential constraints, indexes, retry uniqueness and stdlib unit tests.
- [ ] **AUTH-001** First-run admin bootstrap and authenticated device pairing with revoke support.
- [ ] **API-001** Authenticated room read/write API and idempotent text send.
- [ ] **SYNC-001** Server-assigned cursor replay after an hour offline; no lost or duplicate messages.
- [ ] **SIGNAL-001** Authenticated WebSocket and WebRTC signaling (no file relaying).
- [ ] **P2P-001** Direct encrypted WebRTC DataChannel for a photo and a file between two desktops.
- [ ] **P2P-002** Bounded memory, integrity hash, progress UI and interruption recovery.
- [ ] **PWA-001** Install and test on Windows, Linux, Android and iPad; trusted local HTTPS.
- [ ] **QA-001** Browser E2E (Playwright), disconnect/reconnect, permissions, P2P failure, server RAM/disk budget.
- [ ] **OPS-001** Minimal Docker Compose, backup/restore and health/monitoring.

## First vertical slice (after foundation)

Two paired browsers in one room exchange a text message. Close a browser, send a message, reopen it and assert exactly-once history replay. Add WebRTC file transfer only after this passes.

## Acceptance criteria for server constraints

Measure server idle RSS and disk size, memory during signaling bursts and memory usage while a multi-GB transfer is in progress. Server traffic for binary payloads must remain **zero**; if P2P fails, display an explicit failure rather than silently proxying.
