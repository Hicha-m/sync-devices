-- AUTH-001 migration. No plaintext secrets stored. Public keys are unverified metadata in v2.
ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
  CHECK (is_admin IN (0, 1));

CREATE TABLE device_credentials (
  device_id TEXT PRIMARY KEY REFERENCES devices(id) ON DELETE RESTRICT,
  secret_hash TEXT NOT NULL UNIQUE CHECK (length(secret_hash) = 64),
  created_at TEXT NOT NULL
);

CREATE TABLE auth_sessions (
  token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
  device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_auth_sessions_device ON auth_sessions(device_id);

CREATE TABLE pairing_invites (
  token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
  target_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_by_device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
  expires_at TEXT NOT NULL,
  used_at TEXT
);
CREATE INDEX idx_pairing_invites_expiry ON pairing_invites(expires_at);
