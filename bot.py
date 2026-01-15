import html
import logging
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN, ALLOWED_CHAT_IDS
from forward_info import register_forward_handlers
import db

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

LINK_REGEX = re.compile(r"(https?://|t\.me/|www\.)")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("ladybot")


async def is_admin(message: Message):
    if not message.from_user:
        return False
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]

async def is_admin_in_chat(user_id: int, chat_id: int):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]

async def warn_and_cleanup_non_admin_command(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
    if message.from_user:
        try:
            await bot.send_message(
                message.from_user.id,
                "Iltimos, bu guruhda buyruqlar yubormang. Rahmat.",
            )
        except Exception:
            logger.info(
                "Failed to DM non-admin warning: chat_id=%s user_id=%s",
                message.chat.id,
                message.from_user.id,
            )


def is_allowed_chat_id(chat_id: int):
    return ALLOWED_CHAT_IDS is None or chat_id in ALLOWED_CHAT_IDS


# 1. Clean join / leave
@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    if not is_allowed_chat_id(message.chat.id):
        return
    for user in message.new_chat_members:
        invite = getattr(message, "invite_link", None)
        if invite and invite.creator:
            db.increment_invite(invite.creator.id, message.chat.id)
            db.log_event(
                chat_id=message.chat.id,
                event_type="join_invite",
                actor_id=invite.creator.id,
                target_id=user.id,
                invite_creator_id=invite.creator.id,
                invite_link=getattr(invite, "invite_link", None),
            )
            continue
        adder = message.from_user
        if adder and adder.id != user.id:
            db.increment_invite(adder.id, message.chat.id)
            db.log_event(
                chat_id=message.chat.id,
                event_type="join_added",
                actor_id=adder.id,
                target_id=user.id,
            )
        else:
            logger.info(
                "Join without invite/adder: chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )
            db.log_event(
                chat_id=message.chat.id,
                event_type="join_unknown",
                target_id=user.id,
            )
    await message.delete()


@dp.message(F.left_chat_member)
async def on_user_leave(message: Message):
    if not is_allowed_chat_id(message.chat.id):
        return
    left = message.left_chat_member
    actor_id = message.from_user.id if message.from_user else None
    target_id = left.id if left else None
    if left and message.from_user and message.from_user.id != left.id:
        event_type = "leave_removed"
    else:
        event_type = "leave_left"
        actor_id = target_id
    db.log_event(
        chat_id=message.chat.id,
        event_type=event_type,
        actor_id=actor_id,
        target_id=target_id,
    )
    await message.delete()


@dp.chat_member()
async def on_chat_member_update(event):
    if not is_allowed_chat_id(event.chat.id):
        return
    if not event.old_chat_member or not event.new_chat_member:
        return
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    target_id = event.new_chat_member.user.id
    actor_id = event.from_user.id if event.from_user else None

    if new_status == ChatMemberStatus.KICKED:
        db.log_event(
            chat_id=event.chat.id,
            event_type="ban",
            actor_id=actor_id,
            target_id=target_id,
        )
        return

    if old_status == ChatMemberStatus.KICKED and new_status != ChatMemberStatus.KICKED:
        db.log_event(
            chat_id=event.chat.id,
            event_type="unban",
            actor_id=actor_id,
            target_id=target_id,
        )


# 2. Anti-link (group/supergroup only)
@dp.message(
    ((F.chat.type == "group") | (F.chat.type == "supergroup"))
    & ((F.text & ~F.text.startswith("/")) | (F.caption & ~F.caption.startswith("/")))
)
async def anti_link_and_ads(message: Message):
    if not is_allowed_chat_id(message.chat.id):
        return
    if await is_admin(message):
        return

    text = message.text or message.caption or ""
    if LINK_REGEX.search(text):
        await message.delete()
        return


# 3. Stats command
async def build_stats_text(chat_id: int):
    stats = db.get_invite_stats(chat_id)
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

    text = "Taklif va qo'shish reytingi:\n"
    for idx, (user_id, count, name) in enumerate(parts, start=1):
        safe_name = html.escape(name)
        text += f'{idx}) <a href="tg://user?id={user_id}">{safe_name}</a> - {count}\n'
    return text


def format_timestamp(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value


async def get_user_link(chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        name = member.user.full_name
    except Exception:
        name = str(user_id)
    safe_name = html.escape(name)
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


async def format_event_line(chat_id: int, event):
    created_at, event_type, actor_id, target_id, invite_creator_id, invite_link = event
    time_text = format_timestamp(created_at)

    actor = await get_user_link(chat_id, actor_id) if actor_id is not None else "noma'lum"
    target = await get_user_link(chat_id, target_id) if target_id is not None else "noma'lum"

    if event_type == "join_invite":
        text = f"{time_text} {target} havola orqali qo'shildi (muallif {actor})"
    elif event_type == "join_added":
        text = f"{time_text} {actor} {target} ni qo'shdi"
    elif event_type == "join_unknown":
        text = f"{time_text} {target} qo'shildi (noma'lum)"
    elif event_type == "leave_left":
        text = f"{time_text} {target} chiqib ketdi"
    elif event_type == "leave_removed":
        text = f"{time_text} {actor} {target} ni o'chirdi"
    elif event_type == "ban":
        text = f"{time_text} {actor} {target} ni bandi"
    elif event_type == "unban":
        text = f"{time_text} {actor} {target} ni bandan chiqardi"
    else:
        text = f"{time_text} {event_type}"

    if invite_link:
        safe_link = html.escape(invite_link)
        text += f' (<a href="{safe_link}">havola</a>)'
    return text

@dp.message(Command("stats"))
async def stats_command(message: Message):
    if not is_allowed_chat_id(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
        text = await build_stats_text(message.chat.id)
        if not text:
            await message.answer("Hozircha taklif yoki qo'shish bo'yicha ma'lumot yo'q.")
            return
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        return

    if not await is_admin(message):
        logger.info("Stats denied (not admin): chat_id=%s", message.chat.id)
        return
    text = await build_stats_text(message.chat.id)
    if not text:
        await message.reply("Hozircha taklif yoki qo'shish bo'yicha ma'lumot yo'q.")
        return
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(Command("start"))
async def start_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
        return
    await message.reply(
        "Salom! Forward qilingan xabarni yuboring, men undagi ma'lumotlarni ko'rsataman. "
        "Agar forward ma'lumotlari chiqmasa, xabar himoyalangan bo'lishi yoki nusxa qilib yuborilgan bo'lishi mumkin."
    )


@dp.message(Command("chat_id"))
async def chat_id_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
        if message.from_user:
            try:
                await bot.send_message(message.from_user.id, f"Guruh ID: {message.chat.id}")
            except Exception:
                logger.info(
                    "Failed to DM chat_id: chat_id=%s user_id=%s",
                    message.chat.id,
                    message.from_user.id,
                )
        return
    await message.reply(f"Guruh ID: {message.chat.id}")


@dp.message(Command("history"))
async def history_command(message: Message):
    if message.chat.type != "private":
        return
    if not message.from_user:
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("Foydalanish: /history <chat_id> [limit]")
        return

    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.reply("Chat ID noto'g'ri. Masalan: /history -1001234567890 20")
        return

    limit = 20
    if len(parts) >= 3:
        try:
            limit = max(1, min(200, int(parts[2])))
        except ValueError:
            await message.reply("Limit son bo'lishi kerak. Masalan: /history -1001234567890 20")
            return

    if not is_allowed_chat_id(chat_id):
        await message.reply("Bu chat ruxsat etilmagan.")
        return

    try:
        if not await is_admin_in_chat(message.from_user.id, chat_id):
            await message.reply("Bu buyruq faqat adminlar uchun.")
            return
    except Exception:
        await message.reply("Chat topilmadi yoki botda ruxsat yo'q.")
        return

    events = db.get_recent_events(chat_id, limit=limit)
    if not events:
        await message.reply("Hozircha tarix mavjud emas.")
        return

    lines = []
    for event in events:
        lines.append(await format_event_line(chat_id, event))

    await message.reply("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


if __name__ == "__main__":
    register_forward_handlers(
        dp=dp,
        is_allowed_chat_id=is_allowed_chat_id,
        logger=logger,
    )
    dp.run_polling(bot)
