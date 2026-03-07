from html import escape

from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, User

_permission_prompted_chats = set()

async def is_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]


async def is_admin_in_chat(user_id: int, chat_id: int, bot) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]


async def is_bot_admin(bot, chat_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, bot.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]


def mention_user(user: User) -> str:
    name = escape(user.full_name or "user")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def get_admin_or_creator_mention(bot, chat_id: int) -> str:
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except Exception:
        return ""
    creator = next((admin for admin in admins if admin.status == ChatMemberStatus.CREATOR), None)
    target = creator or (admins[0] if admins else None)
    if not target:
        return ""
    return mention_user(target.user)


def should_prompt_permission(chat_id: int) -> bool:
    if chat_id in _permission_prompted_chats:
        return False
    _permission_prompted_chats.add(chat_id)
    return True
