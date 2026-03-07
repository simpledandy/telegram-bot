import html
from datetime import datetime, timedelta, timezone

from messages import EVENT_TEMPLATES


def format_timestamp(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        adjusted_dt = dt + timedelta(hours=5)
        return adjusted_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


async def get_user_link(bot, chat_id: int, user_id: int) -> str:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        name = member.user.full_name
    except Exception:
        name = str(user_id)
    safe_name = html.escape(name)
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


async def format_event_line(bot, chat_id: int, event) -> str:
    created_at, event_type, actor_id, target_id, _invite_creator_id, invite_link = event
    time_text = format_timestamp(created_at)

    actor = (
        await get_user_link(bot, chat_id, actor_id)
        if actor_id is not None
        else "noma'lum"
    )
    target = (
        await get_user_link(bot, chat_id, target_id)
        if target_id is not None
        else "noma'lum"
    )

    template = EVENT_TEMPLATES.get(event_type)
    if template:
        text = template.format(time=time_text, actor=actor, target=target)
    else:
        text = f"{time_text} {event_type}"

    if invite_link:
        safe_link = html.escape(invite_link)
        text += f' (<a href="{safe_link}">havola</a>)'
    return text
