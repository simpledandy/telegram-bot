import html
import logging

import db
from messages import MESSAGES

logger = logging.getLogger("ladybot")


async def build_stats_text(bot, chat_id: int):
    stats = await db.get_invite_stats(chat_id)
    if not stats:
        logger.info("Stats empty: chat_id=%s", chat_id)
        return None

    parts = []
    for user_id, count in stats:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            name = member.user.full_name
        except Exception:
            name = str(user_id)
        parts.append((user_id, count, name))

    text = MESSAGES["stats_header"]
    for idx, (user_id, count, name) in enumerate(parts, start=1):
        safe_name = html.escape(name)
        text += f'{idx}) <a href="tg://user?id={user_id}">{safe_name}</a> - {count}\n'
    return text
