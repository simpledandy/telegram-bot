import sqlite3
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


