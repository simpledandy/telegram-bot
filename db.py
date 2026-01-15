import sqlite3
from datetime import datetime
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS invites (
    user_id INTEGER,
    chat_id INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, chat_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS invite_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_id INTEGER,
    target_id INTEGER,
    invite_creator_id INTEGER,
    invite_link TEXT,
    created_at TEXT NOT NULL
)
""")

conn.commit()


def increment_invite(user_id, chat_id):
    cur.execute("""
    INSERT INTO invites (user_id, chat_id, count)
    VALUES (?, ?, 1)
    ON CONFLICT(user_id, chat_id)
    DO UPDATE SET count = count + 1
    """, (user_id, chat_id))
    conn.commit()


def get_invite_stats(chat_id):
    cur.execute("""
    SELECT user_id, count FROM invites
    WHERE chat_id = ?
    ORDER BY count DESC
    """, (chat_id,))
    return cur.fetchall()


def log_event(
    *,
    chat_id,
    event_type,
    actor_id=None,
    target_id=None,
    invite_creator_id=None,
    invite_link=None,
):
    cur.execute(
        """
        INSERT INTO invite_events (
            chat_id,
            event_type,
            actor_id,
            target_id,
            invite_creator_id,
            invite_link,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            event_type,
            actor_id,
            target_id,
            invite_creator_id,
            invite_link,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()


def get_recent_events(chat_id, limit=20):
    cur.execute(
        """
        SELECT created_at, event_type, actor_id, target_id, invite_creator_id, invite_link
        FROM invite_events
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (chat_id, limit),
    )
    return cur.fetchall()


