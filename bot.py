import html
import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN, ALLOWED_CHAT_IDS
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


def is_allowed_chat(message: Message):
    return ALLOWED_CHAT_IDS is None or message.chat.id in ALLOWED_CHAT_IDS


# 1. Clean join / leave
@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    if not is_allowed_chat(message):
        return
    for user in message.new_chat_members:
        invite = getattr(message, "invite_link", None)
        if invite and invite.creator:
            db.increment_invite(invite.creator.id, message.chat.id)
            continue
        adder = message.from_user
        if adder and adder.id != user.id:
            db.increment_invite(adder.id, message.chat.id)
        else:
            logger.info(
                "Join without invite/adder: chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )
    await message.delete()


@dp.message(F.left_chat_member)
async def on_user_leave(message: Message):
    if not is_allowed_chat(message):
        return
    await message.delete()


# 2. Anti-link (group/supergroup only)
@dp.message(
    ((F.chat.type == "group") | (F.chat.type == "supergroup"))
    & ((F.text & ~F.text.startswith("/")) | (F.caption & ~F.caption.startswith("/")))
)
async def anti_link_and_ads(message: Message):
    if (message.forward_origin or message.forward_from_chat) and message.chat.type == "private":
        return
    if not is_allowed_chat(message):
        return
    if await is_admin(message):
        return

    text = message.text or message.caption or ""
    if LINK_REGEX.search(text):
        await message.delete()
        return


# 3. Stats command
async def send_stats(message: Message):
    if not is_allowed_chat(message):
        return
    logger.info(
        "Stats request: chat_id=%s from_user=%s sender_chat=%s text=%r",
        message.chat.id,
        message.from_user.id if message.from_user else None,
        message.sender_chat.id if message.sender_chat else None,
        message.text,
    )
    if not await is_admin(message):
        logger.info("Stats denied (not admin): chat_id=%s", message.chat.id)
        return

    stats = db.get_invite_stats(message.chat.id)
    if not stats:
        logger.info("Stats empty: chat_id=%s", message.chat.id)
        await message.reply("Hozircha taklif yoki qo'shish bo'yicha ma'lumot yo'q.")
        return

    text = "Taklif va qo'shish reytingi:\n"
    for idx, (user_id, count) in enumerate(stats, start=1):
        try:
            member = await bot.get_chat_member(message.chat.id, user_id)
            name = member.user.full_name
        except Exception:
            name = str(user_id)
        safe_name = html.escape(name)
        text += f'{idx}) <a href="tg://user?id={user_id}">{safe_name}</a> - {count}\n'

    logger.info("Stats sent: chat_id=%s rows=%d", message.chat.id, len(stats))
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command("stats"))
async def stats_command(message: Message):
    if message.chat.type in ["group", "supergroup"] and not await is_admin(message):
        await warn_and_cleanup_non_admin_command(message)
        return
    await send_stats(message)
    if message.chat.type in ["group", "supergroup"]:
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)


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


@dp.message(
    F.forward_origin
    | F.forward_from_chat
    | F.forward_from
    | F.forward_sender_name
    | F.forward_date
)
async def forward_info(message: Message):
    if message.chat.type != "private" and not is_allowed_chat(message):
        return

    logger.info(
        "Forward handler: chat_id=%s type=%s has_origin=%s has_from_chat=%s has_from=%s has_sender_name=%s has_date=%s",
        message.chat.id,
        message.chat.type,
        bool(getattr(message, "forward_origin", None)),
        bool(getattr(message, "forward_from_chat", None)),
        bool(getattr(message, "forward_from", None)),
        bool(getattr(message, "forward_sender_name", None)),
        bool(getattr(message, "forward_date", None)),
    )

    parts = ["Yuborilgan xabar ma'lumotlari:"]

    origin = getattr(message, "forward_origin", None)
    if origin:
        origin_type = getattr(origin, "type", None)
        parts.append(f"Manba turi: {origin_type}")

        origin_sender = getattr(origin, "sender_user", None)
        if origin_sender:
            parts.append(f"Manba foydalanuvchi ID: {origin_sender.id}")
            parts.append(f"Manba ism: {origin_sender.full_name}")

        origin_chat = getattr(origin, "sender_chat", None)
        if origin_chat:
            parts.append(f"Manba chat ID: {origin_chat.id}")
            if origin_chat.title:
                parts.append(f"Manba chat nomi: {origin_chat.title}")
            if origin_chat.username:
                parts.append(f"Manba chat username: @{origin_chat.username}")

        origin_name = getattr(origin, "sender_user_name", None)
        if origin_name:
            parts.append(f"Manba ko'rsatilgan ism: {origin_name}")

    fchat = getattr(message, "forward_from_chat", None)
    if fchat:
        parts.append(f"Forward chat ID: {fchat.id}")
        if fchat.title:
            parts.append(f"Forward chat nomi: {fchat.title}")
        if fchat.username:
            parts.append(f"Forward chat username: @{fchat.username}")

    fuser = getattr(message, "forward_from", None)
    if fuser:
        parts.append(f"Forward foydalanuvchi ID: {fuser.id}")
        parts.append(f"Forward ism: {fuser.full_name}")

    fdate = getattr(message, "forward_date", None)
    if fdate:
        parts.append(f"Forward vaqti (UTC): {fdate.isoformat()}")

    fmsg_id = getattr(message, "forward_from_message_id", None)
    if fmsg_id:
        parts.append(f"Forward xabar ID: {fmsg_id}")

    fsender_name = getattr(message, "forward_sender_name", None)
    if fsender_name:
        parts.append(f"Forward yuboruvchi ismi: {fsender_name}")

    fsignature = getattr(message, "forward_signature", None)
    if fsignature:
        parts.append(f"Forward imzo: {fsignature}")

    parts.append(f"Joriy chat ID: {message.chat.id}")
    if len(parts) == 2 and message.chat.type == "private":
        try:
            await message.reply(
                "Forward ma'lumotlari topilmadi. "
                "Ehtimol, xabar himoyalangan yoki oddiy nusxa sifatida yuborilgan. "
                "Iltimos, xabarni aynan forward qilib yuboring."
            )
        except Exception:
            logger.exception(
                "Forward reply failed: chat_id=%s from_user=%s",
                message.chat.id,
                message.from_user.id if message.from_user else None,
            )
        logger.info(
            "Forward info missing: chat_id=%s from_user=%s",
            message.chat.id,
            message.from_user.id if message.from_user else None,
        )
        return

    try:
        await message.reply("\n".join(parts))
    except Exception:
        logger.exception(
            "Forward reply failed: chat_id=%s from_user=%s",
            message.chat.id,
            message.from_user.id if message.from_user else None,
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


if __name__ == "__main__":
    dp.run_polling(bot)
