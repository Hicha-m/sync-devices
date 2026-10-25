# Security baseline

**The repository currently contains a schema, not a secured chat service. Do not expose development prototypes on the public Internet.**

Threats and mitigations planned for implementation:

1. **Unauthorized neighbors on LAN**: explicit device pairing, per-device cryptographic identity, a revocable server-side record; never trust IP address as identity.
2. **Identity spoofing**: bind every authenticated connection to a device and its owner; derive authorship server-side rather than trusting JSON fields.
3. **Room information leakage**: check `room_members` for history, posting, metadata, presence and signaling. Limit metadata disclosure.
4. **Intercepted control plane**: TLS HTTPS/WSS with a trusted certificate; the production PWA needs a secure origin. Use short-lived sessions and CSRF protection for cookie-based endpoints.
5. **Untrusted filenames/files**: never execute files automatically; sanitize names and paths; bound metadata sizes; verify whole-file hash; validate transferred chunk boundaries.
6. **Resource exhaustion**: bounded message length, request rate, sockets and signal payloads; SQLite busy timeout, WAL checkpoints and disk quota/monitoring; do not proxy attachment bytes.
7. **Offline devices**: only text/metadata is durable on the server. Sender PWA must remain reachable to provide bytes, especially on iPad.
8. **Revocation**: disconnect revoked devices, reject their API/signaling events and invalidate sessions. Already-downloaded files cannot be revoked retroactively.
9. **Backups**: periodically back up SQLite with its consistent backup API, keep backup copies off-server when possible and test restoration.

**Privacy note:** the server can read message plaintext in v1. TLS is not end-to-end encryption. An E2EE design would require key distribution, multi-device history recovery and key rotation; it is not claimed here.
