"""Regression tests for the SQLite foundation; no third-party dependencies."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_devices.db import SCHEMA_VERSION, connect


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.db.execute(
            "INSERT INTO users(id, username, display_name) VALUES (?, ?, ?)",
            ("u1", "alice", "Alice"),
        )
        self.db.execute(
            "INSERT INTO devices(id, owner_user_id, name, platform, identity_public_key) "
            "VALUES (?, ?, ?, ?, ?)",
            ("d1", "u1", "Laptop", "linux", "public-key-1"),
        )
        self.db.execute(
            "INSERT INTO spaces(id, name, created_by_user_id) VALUES (?, ?, ?)",
            ("s1", "Home", "u1"),
        )
        self.db.execute(
            "INSERT INTO space_members(space_id, user_id, role) VALUES (?, ?, ?)",
            ("s1", "u1", "owner"),
        )
        self.db.execute(
            "INSERT INTO rooms(id, space_id, kind, name, created_by_user_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("r1", "s1", "channel", "general", "u1"),
        )
        self.db.execute(
            "INSERT INTO room_members(room_id, user_id) VALUES (?, ?)",
            ("r1", "u1"),
        )

    def tearDown(self):
        self.db.close()

    def insert_message(self, message_id, client_id, body="Hello"):
        return self.db.execute(
            "INSERT INTO messages(id, room_id, author_user_id, author_device_id, "
            "client_message_id, body) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, "r1", "u1", "d1", client_id, body),
        ).lastrowid

    def test_initializes_schema_v1_and_foreign_keys(self):
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_usernames_case_insensitive_unique(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO users(id, username, display_name) VALUES ('u2', 'ALICE', 'Bob')"
            )

    def test_device_must_belong_to_existing_user(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO devices(id, owner_user_id, name, platform, identity_public_key) "
                "VALUES ('d2', 'missing', 'Phone', 'android', 'public-key-2')"
            )

    def test_message_sequence_supports_offline_replay(self):
        first = self.insert_message("m1", "nonce1")
        second = self.insert_message("m2", "nonce2", "After an hour")
        received = [
            row["id"]
            for row in self.db.execute(
                "SELECT id FROM messages WHERE room_id = ? AND seq > ? ORDER BY seq",
                ("r1", first),
            )
        ]
        self.assertEqual(received, ["m2"])
        self.assertGreater(second, first)

    def test_same_device_retry_is_unique(self):
        self.insert_message("m1", "repeat-me")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_message("m2", "repeat-me")
        self.assertEqual(self.db.execute("SELECT count(*) FROM messages").fetchone()[0], 1)

    def test_attachment_is_metadata_only_and_requires_valid_message(self):
        self.insert_message("m1", "nonce1", None)
        self.db.execute(
            "INSERT INTO attachments(id, message_id, source_device_id, original_name, "
            "media_type, size_bytes, sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("a1", "m1", "d1", "movie.mkv", "video/x-matroska", 20_000_000_000, "a" * 64),
        )
        attachment = self.db.execute(
            "SELECT * FROM attachments WHERE id='a1'"
        ).fetchone()
        self.assertEqual(attachment["size_bytes"], 20_000_000_000)
        self.assertNotIn("data", attachment.keys())
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO attachments(id, message_id, source_device_id, original_name, "
                "media_type, size_bytes) VALUES ('a2', 'missing', 'd1', 'bad.bin', "
                "'application/octet-stream', 1)"
            )

    def test_bad_file_size_rejected(self):
        self.insert_message("m1", "nonce1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO attachments(id, message_id, source_device_id, original_name, "
                "media_type, size_bytes) VALUES ('a2', 'm1', 'd1', 'bad.bin', "
                "'application/octet-stream', -1)"
            )

    def test_dm_must_be_unnamed(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO rooms(id, space_id, kind, name, created_by_user_id) "
                "VALUES ('r2', 's1', 'dm', 'not allowed', 'u1')"
            )

    def test_file_storage_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subdir" / "chat.db"
            first = connect(path)
            first.execute(
                "INSERT INTO users(id, username, display_name) VALUES ('u2', 'bob', 'Bob')"
            )
            first.commit()
            first.close()
            second = connect(path)
            self.assertEqual(
                second.execute("SELECT username FROM users WHERE id='u2'").fetchone()[0],
                "bob",
            )
            second.close()

    def test_unknown_future_schema_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.db"
            db = connect(path)
            db.execute("PRAGMA user_version=999")
            db.close()
            with self.assertRaisesRegex(RuntimeError, "migration"):
                connect(path)


if __name__ == "__main__":
    unittest.main()
