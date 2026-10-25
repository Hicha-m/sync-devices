# Protocol draft (not implemented)

## Channel types

- **HTTPS API**: authenticated pairing, space/room listing, text history and message creation. All persistent text goes through this API.
- **Authenticated WebSocket**: server-to-client notifications, online presence, WebRTC signaling (offer / answer / ICE), not binary media.
- **WebRTC RTCDataChannel**: direct file bytes between authorized source and recipient, split into bounded chunks.

## Sending a text message

```text
device -> server: SEND_MESSAGE {room_id, client_message_id, body}
server: validate device signature/session; check nonrevoked owner and room membership
server: transaction -> insert once, assign seq, commit
server -> device: MESSAGE_ACK {message_id, seq}
server -> online room members: MESSAGE_CREATED {message_id, seq}
later device -> server: GET_MESSAGES(room_id, after_seq)
server -> later device: authorized messages in seq order
```

Never trust `author_user_id` supplied by the client. Derive user identity from the authenticated device. A retry with `client_message_id` must be safe and return the original message.

## Sending a file

```text
source -> server: POST_METADATA {room_id, filename, size, mime, sha256?}
server -> room: ATTACHMENT_POSTED (metadata only)
receiver -> server: REQUEST_PEER_CONNECTION {attachment_id}
server: authenticate both devices and verify recipient's room access
server: forward ephemeral SDP/ICE only
source <-> receiver: WebRTC secure DataChannel, chunked bytes
receiver: verify final SHA-256 before marking complete
```

Receiver must not execute downloaded files automatically. Sanitize filenames for display and path usage. Validate negotiated transfer IDs, peer identity, claimed metadata and attachment access.

## Resume contract (later milestone)

Store transfer progress locally (not on server). A resumed session must reauthorize both peers and negotiate which chunks already exist; verify completed bytes before trusting the result. A reconnect **alone** does not provide resumability.

## Open issues

- Public-key pairing flow, challenge/response, short-lived sessions and revocation.
- Browser storage/file-streaming API capability matrix for Safari/iPadOS.
- Cross-client reliable delivery and performance tests for 1 GiB+ files.
- One sender -> many receivers: initially independent P2P connections; explicit sender bandwidth cost.
