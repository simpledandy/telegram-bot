from aiogram import F
from aiogram.types import Message


def register_forward_handlers(dp, is_allowed_chat_id, logger):
    @dp.message(
        F.forward_origin
        | F.forward_from_chat
        | F.forward_from
        | F.forward_sender_name
        | F.forward_date
    )
    async def forward_info(message: Message):
        if message.chat.type != "private" and not is_allowed_chat_id(message.chat.id):
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
