# Architecture — ADR-001

## Decision

Use **hybrid centralized text + peer-to-peer binary transfer**.

The application is a home-LAN messenger, not a general-purpose file synchronizer yet. One always-on Linux server is the control plane, identity authority and durable home for text history. Windows, Linux, Android and iPad run clients; the initial cross-platform client will be a PWA.

```text
                         Linux server (500 MB RAM)
                      +-----------------------------+
                      | HTTPS PWA delivery          |
                      | authenticated API           |
                      | WebSocket signaling/presence|
                      | SQLite messages + metadata  |
                      +--------------+--------------+
                                     |
                       control plane / room sync
                       /                         \
             Windows or Linux                 Android or iPad
             PWA/device A                      PWA/device B
                       \                         /
                        ==== direct WebRTC ======
                         messages? NO: text is
                         persisted centrally.
                         binary files ONLY P2P.
```

## Responsibility split

| Data | Server | Source device | Receiving device |
|---|---|---|---|
| Users, room membership | SQLite, authoritative | Local cache | Local cache |
| Text messages | SQLite, authoritative | Optional cache | Optional cache |
| Message delivery cursor | SQLite | Local UX state | Local UX state |
| Attachment metadata (name, size, hash, source) | SQLite | Local manifest | Local cache |
| Binary file bytes | **Never** | Stored locally | Stored if downloaded |
| Connection presence | Volatile memory only | Heartbeat | Heartbeat |
| WebRTC SDP / ICE | Ephemeral forwarding only | Local | Local |

## Runtime target

- SQLite with WAL mode, short transactions, indexed incremental reads and regular backups.
- One small backend process. Avoid heavyweight queues, Redis, PostgreSQL and media transcoding.
- Stream file chunks directly between peers, with bounded DataChannel buffers and checksums.
- The server must never be a fallback media relay. A future opt-in always-on peer with large disk could provide replicas, but **not in the MVP**.
- Presence means **app reachable and authenticated**; device power-on alone is not sufficient.

## Limitations

- iPadOS can suspend an installed PWA in the background; the source must keep it active for reliable file sharing.
- WebRTC DataChannel access can be blocked by client isolation/firewalls. Direct P2P usually works on a normal LAN but is not guaranteed.
- A PWA needs a trusted secure origin (HTTPS on LAN in production) for browser capabilities. Local CA certificates require trust configuration on clients.
- No TURN relay in v1 means some network topologies cannot transfer files.
- Text history is not end-to-end encrypted in v1: it is protected in transit by TLS, and readable by the server administrator. Revisit E2EE as a dedicated design project.

## MVP boundaries

The current branch ships only the data model and tests. Implement pairing/authentication before any chat or signaling APIs are exposed.
