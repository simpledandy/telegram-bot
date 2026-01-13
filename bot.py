import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN
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


# 1. Clean join / leave
@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    for user in message.new_chat_members:
        invite = getattr(message, "invite_link", None)
        if invite and invite.creator:
            db.increment_invite(invite.creator.id, message.chat.id)
        else:
            logger.info(
                "Join without invite_link creator: chat_id=%s user_id=%s",
                message.chat.id,
                user.id,
            )
    await message.delete()


@dp.message(F.left_chat_member)
async def on_user_leave(message: Message):
    await message.delete()


# 2. Anti-link
@dp.message(
    (F.text & ~F.text.startswith("/")) | (F.caption & ~F.caption.startswith("/"))
)
async def anti_link_and_ads(message: Message):
    if await is_admin(message):
        return

    text = message.text or message.caption or ""
    if LINK_REGEX.search(text):
        await message.delete()
        return


# 3. Stats command
async def send_stats(message: Message):
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
        await message.reply("No invite data yet.")
        return

    text = "Invite leaderboard:\\n"
    for user_id, count in stats:
        text += f"- {user_id}: {count}\\n"

    logger.info("Stats sent: chat_id=%s rows=%d", message.chat.id, len(stats))
    await message.reply(text)


@dp.message(Command("stats"))
async def stats_command(message: Message):
    await send_stats(message)


if __name__ == "__main__":
    dp.run_polling(bot)
