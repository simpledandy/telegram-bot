import logging

from aiogram import Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, ChatMemberUpdated

import db
from messages import MESSAGES
from utils.permissions import (
    get_admin_or_creator_mention,
    should_prompt_permission,
)

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.new_chat_members)
async def on_user_join(message: Message):
    for user in message.new_chat_members:
        invite = getattr(message, "invite_link", None)
        if invite and invite.creator:
            await db.increment_invite(invite.creator.id, message.chat.id)
            await db.log_event(
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
            await db.increment_invite(adder.id, message.chat.id)
            await db.log_event(
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
            await db.log_event(
                chat_id=message.chat.id,
                event_type="join_unknown",
                target_id=user.id,
            )
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete join message: chat_id=%s", message.chat.id)
        if should_prompt_permission(message.chat.id):
            admin_mention = await get_admin_or_creator_mention(message.bot, message.chat.id)
            if not admin_mention:
                admin_mention = "admin"
            await message.answer(
                MESSAGES["permission_required"].format(admin=admin_mention),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )


@router.message(F.left_chat_member)
async def on_user_leave(message: Message):
    # Chat member updates also log leaves; avoid double-counting.
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete leave message: chat_id=%s", message.chat.id)
        if should_prompt_permission(message.chat.id):
            admin_mention = await get_admin_or_creator_mention(message.bot, message.chat.id)
            if not admin_mention:
                admin_mention = "admin"
            await message.answer(
                MESSAGES["permission_required"].format(admin=admin_mention),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated):
    if event.new_chat_member and event.new_chat_member.user.id == event.bot.id:
        if event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            await event.bot.send_message(event.chat.id, MESSAGES["group_onboarding"])
    if not event.old_chat_member or not event.new_chat_member:
        return
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    target_id = event.new_chat_member.user.id
    actor_id = event.from_user.id if event.from_user else None

    if new_status == ChatMemberStatus.KICKED:
        await db.log_event(
            chat_id=event.chat.id,
            event_type="ban",
            actor_id=actor_id,
            target_id=target_id,
        )
        return

    if new_status == ChatMemberStatus.LEFT:
        event_type = "leave_left"
        if actor_id is not None and actor_id != target_id:
            event_type = "leave_removed"
        await db.log_event(
            chat_id=event.chat.id,
            event_type=event_type,
            actor_id=actor_id if actor_id is not None else target_id,
            target_id=target_id,
        )
        return

    if old_status == ChatMemberStatus.KICKED and new_status != ChatMemberStatus.KICKED:
        await db.log_event(
            chat_id=event.chat.id,
            event_type="unban",
            actor_id=actor_id,
            target_id=target_id,
        )
