# Working rules for Sync Devices

- First read `README.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md` and `docs/SECURITY.md`.
- Prioritize the target server: 500 MB RAM, 16 GB disk, low idle CPU and a small number of LAN users.
- No binary attachments on the central server. No accidental buffering of complete files in server memory. Signaling is control-plane only.
- Keep the text-message history durable on server-side SQLite; each device must be able to fetch missed messages.
- Treat every device as an independently authenticated endpoint. Never trust a client-supplied user ID, room ID, filename or availability claim without authorization checks.
- Room membership is checked on **every** read, send, signaling and attachment operation. Never expose offers/ICE candidates to unauthorized peers.
- Never open unauthenticated WebSocket endpoints to the LAN. HTTPS is required for remote clients/PWA; loopback developer testing is the only exception.
- Do not add a TURN relay or cloud dependency without a separate design decision. On blocked networks explain that direct P2P is unavailable.
- Use database migrations when altering the schema; do not rewrite v1 in place after it is deployed.
- Add regression tests for all important access-control, idempotency and conflict scenarios.
- Work in small tested increments. State what is implemented versus merely documented.
