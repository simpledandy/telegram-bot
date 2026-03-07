import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from messages import MESSAGES
from services.history import format_event_line
from services.stats import build_stats_text
from utils.permissions import (
    get_admin_or_creator_mention,
    is_admin,
    is_admin_in_chat,
    should_prompt_permission,
)

router = Router()
logger = logging.getLogger(__name__)
HISTORY_PAGE_SIZE = 10


async def warn_and_cleanup_non_admin_command(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
    if message.from_user:
        try:
            await message.bot.send_message(
                message.from_user.id,
                MESSAGES["non_admin_command_warning"],
            )
        except Exception:
            logger.info(
                "Failed to DM non-admin warning: chat_id=%s user_id=%s",
                message.chat.id,
                message.from_user.id,
            )


async def maybe_prompt_permission(message: Message):
    if not should_prompt_permission(message.chat.id):
        return
    admin_mention = await get_admin_or_creator_mention(message.bot, message.chat.id)
    if not admin_mention:
        admin_mention = "admin"
    await message.answer(
        MESSAGES["permission_required"].format(admin=admin_mention),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def build_history_keyboard(chat_id: int, offset: int, total: int) -> InlineKeyboardMarkup | None:
    if total <= HISTORY_PAGE_SIZE:
        return None
    buttons = []
    if offset > 0:
        prev_offset = max(0, offset - HISTORY_PAGE_SIZE)
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"history:{chat_id}:{prev_offset}",
            )
        )
    if offset + HISTORY_PAGE_SIZE < total:
        next_offset = offset + HISTORY_PAGE_SIZE
        buttons.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=f"history:{chat_id}:{next_offset}",
            )
        )
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


async def build_history_text(bot, chat_id: int, offset: int) -> str:
    events = await db.get_events_page(chat_id, limit=HISTORY_PAGE_SIZE, offset=offset)
    if not events:
        return ""
    lines = []
    for event in events:
        lines.append(await format_event_line(bot, chat_id, event))
    return "\n".join(lines)


@router.message(Command("stats"))
async def stats_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
            await maybe_prompt_permission(message)
        text = await build_stats_text(message.bot, message.chat.id)
        if not text:
            await message.answer(MESSAGES["stats_empty"])
            return
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        return

    if not await is_admin(message):
        logger.info("Stats denied (not admin): chat_id=%s", message.chat.id)
        return
    text = await build_stats_text(message.bot, message.chat.id)
    if not text:
        await message.reply(MESSAGES["stats_empty"])
        return
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("start"))
async def start_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
            await maybe_prompt_permission(message)
        return
    await message.reply(MESSAGES["start_private"])


@router.message(Command("chat_id"))
async def chat_id_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
            await maybe_prompt_permission(message)
        if message.from_user:
            try:
                await message.bot.send_message(
                    message.from_user.id,
                    MESSAGES["chat_id_label"].format(chat_id=message.chat.id),
                )
            except Exception:
                logger.info(
                    "Failed to DM chat_id: chat_id=%s user_id=%s",
                    message.chat.id,
                    message.from_user.id,
                )
        return
    await message.reply(MESSAGES["chat_id_label"].format(chat_id=message.chat.id))


@router.message(Command("history"))
async def history_command(message: Message):
    if not message.from_user:
        return
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
            await maybe_prompt_permission(message)
        chat_id = message.chat.id
        total = await db.get_event_count(chat_id)
        text = await build_history_text(message.bot, chat_id, offset=0)
        if not text:
            await message.bot.send_message(message.from_user.id, MESSAGES["history_empty"])
            return
        keyboard = build_history_keyboard(chat_id, offset=0, total=total)
        await message.bot.send_message(
            message.from_user.id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply(MESSAGES["history_usage"])
        return

    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.reply(MESSAGES["history_bad_chat_id"])
        return

    try:
        if not await is_admin_in_chat(message.from_user.id, chat_id, message.bot):
            await message.reply(MESSAGES["history_admin_only"])
            return
    except Exception:
        await message.reply(MESSAGES["chat_not_found_or_no_perm"])
        return

    total = await db.get_event_count(chat_id)
    text = await build_history_text(message.bot, chat_id, offset=0)
    if not text:
        await message.reply(MESSAGES["history_empty"])
        return
    keyboard = build_history_keyboard(chat_id, offset=0, total=total)
    await message.reply(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


@router.message(Command("help"))
async def help_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message):
            await warn_and_cleanup_non_admin_command(message)
            return
        try:
            await message.delete()
        except Exception:
            logger.exception("Failed to delete command message: chat_id=%s", message.chat.id)
            await maybe_prompt_permission(message)
        if message.from_user:
            try:
                await message.bot.send_message(
                    message.from_user.id,
                    MESSAGES["help_text"],
                )
            except Exception:
                logger.info(
                    "Failed to DM help: chat_id=%s user_id=%s",
                    message.chat.id,
                    message.from_user.id,
                )
        return
    await message.reply(MESSAGES["help_text"])


@router.callback_query(F.data.startswith("history:"))
async def history_page_callback(callback: CallbackQuery):
    if not callback.data or not callback.from_user:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    try:
        chat_id = int(parts[1])
        offset = int(parts[2])
    except ValueError:
        await callback.answer()
        return

    try:
        if not await is_admin_in_chat(callback.from_user.id, chat_id, callback.bot):
            await callback.answer(MESSAGES["history_admin_only"], show_alert=True)
            return
    except Exception:
        await callback.answer(MESSAGES["chat_not_found_or_no_perm"], show_alert=True)
        return

    total = await db.get_event_count(chat_id)
    if total == 0:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(MESSAGES["history_empty"])
        return

    max_offset = max(0, ((total - 1) // HISTORY_PAGE_SIZE) * HISTORY_PAGE_SIZE)
    offset = max(0, min(offset, max_offset))
    text = await build_history_text(callback.bot, chat_id, offset=offset)
    keyboard = build_history_keyboard(chat_id, offset=offset, total=total)
    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
    await callback.answer()
