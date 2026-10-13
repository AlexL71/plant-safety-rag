"""SQLite storage for chats, messages, admin reviews, settings and admin sessions.

One file (`web.db_path`), safe to use from several threads (one connection + a lock).
Users are anonymous: a random id in a browser cookie owns their chats.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL,
    created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS chats_user ON chats(user_id, updated);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL, text TEXT NOT NULL, payload TEXT, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS messages_chat ON messages(chat_id, id);
CREATE TABLE IF NOT EXISTS reviews (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL, note TEXT, reviewer TEXT, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_sessions (
    token TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL);
"""

VERDICTS = {"correct", "partial", "incorrect"}


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()

    # ---------------------------------------------------------------- helpers
    def _q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def _x(self, sql: str, args: tuple = ()) -> int:
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.lastrowid

    # ---------------------------------------------------------------- chats
    def create_chat(self, user_id: str, max_chats: int) -> dict[str, Any]:
        """New empty chat; deletes the user's oldest chats so at most `max_chats` remain."""
        now = time.time()
        chat_id = uuid.uuid4().hex
        with self.lock:
            old = self.db.execute("SELECT id FROM chats WHERE user_id=? ORDER BY updated DESC LIMIT -1 OFFSET ?",
                                  (user_id, max(0, max_chats - 1))).fetchall()
            for row in old:
                self.db.execute("DELETE FROM chats WHERE id=?", (row["id"],))
            self.db.execute("INSERT INTO chats VALUES (?,?,?,?,?)", (chat_id, user_id, "New chat", now, now))
            self.db.commit()
        return {"id": chat_id, "title": "New chat", "updated": now, "removed": len(old)}

    def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._q("SELECT c.id, c.title, c.updated, "
                       "(SELECT COUNT(*) FROM messages m WHERE m.chat_id=c.id AND m.role='user') AS turns "
                       "FROM chats c WHERE c.user_id=? ORDER BY c.updated DESC", (user_id,))
        return [dict(r) for r in rows]

    def get_chat(self, chat_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        rows = self._q("SELECT * FROM chats WHERE id=?" + (" AND user_id=?" if user_id else ""),
                       (chat_id, user_id) if user_id else (chat_id,))
        return dict(rows[0]) if rows else None

    def delete_chat(self, chat_id: str, user_id: str) -> None:
        self._x("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user_id))

    def touch_chat(self, chat_id: str, title: str | None = None) -> None:
        if title:
            self._x("UPDATE chats SET updated=?, title=? WHERE id=?", (time.time(), title, chat_id))
        else:
            self._x("UPDATE chats SET updated=? WHERE id=?", (time.time(), chat_id))

    # ---------------------------------------------------------------- messages
    def add_message(self, chat_id: str, role: str, text: str, payload: dict | None = None) -> int:
        return self._x("INSERT INTO messages (chat_id, role, text, payload, created) VALUES (?,?,?,?,?)",
                       (chat_id, role, text, json.dumps(payload, ensure_ascii=False) if payload else None, time.time()))

    def messages(self, chat_id: str) -> list[dict[str, Any]]:
        rows = self._q("SELECT * FROM messages WHERE chat_id=? ORDER BY id", (chat_id,))
        return [{**dict(r), "payload": json.loads(r["payload"]) if r["payload"] else None} for r in rows]

    def history(self, chat_id: str) -> list[tuple[str, str]]:
        """(question, answer) pairs in order, for rewriting follow-up questions."""
        pairs, pending = [], None
        for m in self.messages(chat_id):
            if m["role"] == "user":
                pending = m["text"]
            elif m["role"] == "assistant" and pending is not None:
                pairs.append((pending, m["text"]))
                pending = None
        return pairs

    def count_turns(self, chat_id: str) -> int:
        return self._q("SELECT COUNT(*) AS n FROM messages WHERE chat_id=? AND role='user'", (chat_id,))[0]["n"]

    # ---------------------------------------------------------------- admin: answers & reviews
    def list_answers(self, limit: int, offset: int, verdict: str | None = None) -> list[dict[str, Any]]:
        where, args = "WHERE a.role='assistant'", []
        if verdict == "unreviewed":
            where += " AND r.verdict IS NULL"
        elif verdict in VERDICTS:
            where += " AND r.verdict=?"
            args.append(verdict)
        rows = self._q(
            "SELECT a.id, a.text, a.payload, a.created, a.chat_id, r.verdict, r.note, "
            "(SELECT u.text FROM messages u WHERE u.chat_id=a.chat_id AND u.role='user' AND u.id<a.id "
            " ORDER BY u.id DESC LIMIT 1) AS question "
            f"FROM messages a LEFT JOIN reviews r ON r.message_id=a.id {where} ORDER BY a.id DESC LIMIT ? OFFSET ?",
            (*args, limit, offset))
        return [{**dict(r), "payload": json.loads(r["payload"]) if r["payload"] else None} for r in rows]

    def get_answer(self, message_id: int) -> dict[str, Any] | None:
        rows = self.list_answers_by_id(message_id)
        return rows[0] if rows else None

    def list_answers_by_id(self, message_id: int) -> list[dict[str, Any]]:
        rows = self._q(
            "SELECT a.id, a.text, a.payload, a.created, a.chat_id, r.verdict, r.note, r.reviewer, r.updated AS reviewed, "
            "(SELECT u.text FROM messages u WHERE u.chat_id=a.chat_id AND u.role='user' AND u.id<a.id "
            " ORDER BY u.id DESC LIMIT 1) AS question "
            "FROM messages a LEFT JOIN reviews r ON r.message_id=a.id WHERE a.id=? AND a.role='assistant'", (message_id,))
        return [{**dict(r), "payload": json.loads(r["payload"]) if r["payload"] else None} for r in rows]

    def set_review(self, message_id: int, verdict: str, note: str, reviewer: str) -> None:
        if verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {sorted(VERDICTS)}")
        self._x("INSERT INTO reviews VALUES (?,?,?,?,?) ON CONFLICT(message_id) DO UPDATE SET "
                "verdict=excluded.verdict, note=excluded.note, reviewer=excluded.reviewer, updated=excluded.updated",
                (message_id, verdict, note, reviewer, time.time()))

    def stats(self) -> dict[str, Any]:
        one = lambda sql: self._q(sql)[0][0]  # noqa: E731
        return {
            "users": one("SELECT COUNT(DISTINCT user_id) FROM chats"),
            "chats": one("SELECT COUNT(*) FROM chats"),
            "questions": one("SELECT COUNT(*) FROM messages WHERE role='user'"),
            "answers": one("SELECT COUNT(*) FROM messages WHERE role='assistant'"),
            "refused": one("SELECT COUNT(*) FROM messages WHERE role='assistant' AND json_extract(payload,'$.refused')=1"),
            "reviews": {r[0]: r[1] for r in self._q("SELECT verdict, COUNT(*) FROM reviews GROUP BY verdict")},
        }

    # ---------------------------------------------------------------- settings
    def get_setting(self, key: str, default: str) -> str:
        rows = self._q("SELECT value FROM settings WHERE key=?", (key,))
        return rows[0]["value"] if rows else default

    def set_setting(self, key: str, value: str) -> None:
        self._x("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    # ---------------------------------------------------------------- admin sessions
    def new_session(self, username: str, hours: float) -> str:
        token = secrets.token_urlsafe(32)
        self._x("DELETE FROM admin_sessions WHERE expires < ?", (time.time(),))
        self._x("INSERT INTO admin_sessions VALUES (?,?,?)", (token, username, time.time() + hours * 3600))
        return token

    def session_user(self, token: str | None) -> str | None:
        if not token:
            return None
        rows = self._q("SELECT username FROM admin_sessions WHERE token=? AND expires > ?", (token, time.time()))
        return rows[0]["username"] if rows else None

    def end_session(self, token: str | None) -> None:
        if token:
            self._x("DELETE FROM admin_sessions WHERE token=?", (token,))
