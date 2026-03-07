import logging
import re

from aiogram import Router, F
from aiogram.types import Message

from messages import MESSAGES
from utils.permissions import (
    get_admin_or_creator_mention,
    is_admin,
    mention_user,
    should_prompt_permission,
)

router = Router()
logger = logging.getLogger(__name__)

LINK_REGEX = re.compile(r"(https?://|t\.me/|www\.)")


@router.message(
    ((F.chat.type == "group") | (F.chat.type == "supergroup"))
    & ((F.text & ~F.text.startswith("/")) | (F.caption & ~F.caption.startswith("/")))
)
async def anti_link_and_ads(message: Message):
    if await is_admin(message):
        return

    text = message.text or message.caption or ""
    if LINK_REGEX.search(text):
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete link message: chat_id=%s", message.chat.id)
            if should_prompt_permission(message.chat.id):
                admin_mention = await get_admin_or_creator_mention(message.bot, message.chat.id)
                if not admin_mention:
                    admin_mention = "admin"
                await message.answer(
                    MESSAGES["permission_required"].format(admin=admin_mention),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            return
        if message.from_user:
            await message.answer(
                MESSAGES["ads_warning"].format(user=mention_user(message.from_user)),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
