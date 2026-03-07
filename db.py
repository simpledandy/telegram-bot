import asyncio
import asyncpg
from datetime import datetime

from config import DATABASE_URL

_POOL = None
_INIT_DONE = False
_INIT_LOCK = asyncio.Lock()


DB_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS invites (
        user_id BIGINT,
        chat_id BIGINT,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, chat_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invite_events (
        id BIGSERIAL PRIMARY KEY,
        chat_id BIGINT NOT NULL,
        event_type TEXT NOT NULL,
        actor_id BIGINT,
        target_id BIGINT,
        invite_creator_id BIGINT,
        invite_link TEXT,
        created_at TEXT NOT NULL
    )
    """,
]


async def _get_pool():
    global _POOL
    if _POOL is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _POOL = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _POOL


async def _ensure_schema():
    global _INIT_DONE
    if _INIT_DONE:
        return

    async with _INIT_LOCK:
        if _INIT_DONE:
            return
        pool = await _get_pool()
        async with pool.acquire() as conn:
            for statement in DB_SCHEMA:
                await conn.execute(statement)
        _INIT_DONE = True


async def increment_invite(user_id, chat_id):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO invites (user_id, chat_id, count)
            VALUES ($1, $2, 1)
            ON CONFLICT (user_id, chat_id)
            DO UPDATE SET count = invites.count + 1
            """,
            user_id,
            chat_id,
        )


async def get_invite_stats(chat_id):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT user_id, count
            FROM invites
            WHERE chat_id = $1
            ORDER BY count DESC
            """,
            chat_id,
        )


async def log_event(
    *,
    chat_id,
    event_type,
    actor_id=None,
    target_id=None,
    invite_creator_id=None,
    invite_link=None,
    created_at=None,
):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO invite_events (
                chat_id,
                event_type,
                actor_id,
                target_id,
                invite_creator_id,
                invite_link,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            chat_id,
            event_type,
            actor_id,
            target_id,
            invite_creator_id,
            invite_link,
            created_at or datetime.utcnow().isoformat(),
        )


async def get_recent_events(chat_id, limit=20):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT created_at, event_type, actor_id, target_id, invite_creator_id, invite_link
            FROM invite_events
            WHERE chat_id = $1
            ORDER BY id DESC
            LIMIT $2
            """,
            chat_id,
            limit,
        )


async def get_event_count(chat_id):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT COUNT(*)
            FROM invite_events
            WHERE chat_id = $1
            """,
            chat_id,
        )
        return row[0] if row else 0


async def get_events_page(chat_id, limit=10, offset=0):
    await _ensure_schema()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT created_at, event_type, actor_id, target_id, invite_creator_id, invite_link
            FROM invite_events
            WHERE chat_id = $1
            ORDER BY id DESC
            LIMIT $2 OFFSET $3
            """,
            chat_id,
            limit,
            offset,
        )
