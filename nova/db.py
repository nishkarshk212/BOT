"""SQLite persistence for Nova.

Stores per-user economy/state and per-chat free-chat history in a single
local file so the bot survives restarts without external services.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from . import config

_lock = threading.Lock()


def _db_path() -> Path:
    return Path(config.DATA_DIR) / config.DB_PATH


@contextmanager
def _conn():
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_db_path(), timeout=30)
    try:
        c.row_factory = sqlite3.Row
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with _lock, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                coins INTEGER NOT NULL DEFAULT 0,
                gems INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_chat INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_streak_day TEXT,
                inventory TEXT NOT NULL DEFAULT '{}',
                properties TEXT NOT NULL DEFAULT '[]',
                pets TEXT NOT NULL DEFAULT '[]',
                stats TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS history (
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                ts TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_chat ON history(chat_id, ts)"
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
        )


# ----------------------------- Users -----------------------------
def get_user(user_id: int, username=None, first_name=None) -> dict:
    with _lock, _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (id, username, first_name, coins, gems) "
                "VALUES (?,?,?,?,?)",
                (user_id, username, first_name, config.START_COINS, config.START_GEMS),
            )
            row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        else:
            # keep username/first_name fresh
            if (username and row["username"] != username) or (
                first_name and row["first_name"] != first_name
            ):
                c.execute(
                    "UPDATE users SET username=?, first_name=? WHERE id=?",
                    (username, first_name, user_id),
                )
        return dict(row)


def update_user(user_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with _lock, _conn() as c:
        c.execute(f"UPDATE users SET {cols} WHERE id=?", (*fields.values(), user_id))


def get_json(user: dict, key: str, default):
    try:
        return json.loads(user.get(key, "null") or "null") or default
    except (json.JSONDecodeError, TypeError):
        return default


def set_json(user_id: int, key: str, value) -> None:
    update_user(user_id, **{key: json.dumps(value)})


# --------------------------- Chat history ------------------------
def add_history(chat_id: int, role: str, content: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO history (chat_id, role, content) VALUES (?,?,?)",
            (chat_id, role, content),
        )
        # trim
        c.execute(
            "DELETE FROM history WHERE chat_id=? AND ts <= ("
            "SELECT ts FROM history WHERE chat_id=? ORDER BY ts DESC "
            f"LIMIT 1 OFFSET {config.MAX_HISTORY*2})",
            (chat_id, chat_id),
        )


def get_history(chat_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM history WHERE chat_id=? ORDER BY ts ASC",
            (chat_id,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ------------------------------ Meta --------------------------------
def meta_get(key: str, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


def meta_set(key: str, value) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )
