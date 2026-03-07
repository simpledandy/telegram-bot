MESSAGES = {
    "non_admin_command_warning": "Iltimos, bu guruhda buyruqlar yubormang. Rahmat.",
    "stats_header": "Taklif va qo'shish reytingi:\n",
    "stats_empty": "Hozircha taklif yoki qo'shish bo'yicha ma'lumot yo'q.",
    "start_private": "Salom! Botga xush kelibsiz.",
    "chat_id_label": "Guruh ID: {chat_id}",
    "history_usage": "Foydalanish: /history <chat_id>",
    "history_bad_chat_id": "Chat ID noto'g'ri. Masalan: /history -1001234567890",
    "history_admin_only": "Bu buyruq faqat adminlar uchun.",
    "chat_not_found_or_no_perm": "Chat topilmadi yoki botda ruxsat yo'q.",
    "history_empty": "Hozircha tarix mavjud emas.",
    "permission_required": "Iltimos, ishlashim uchun admin huquqi bering 😊 {admin}",
    "ads_warning": "{user}, Iltimos, reklama tarqatmang! ❌",
    "group_onboarding": (
        "Assalomu alaykum! Men guruhingizni boshqarishingizga ko'maklashaman 😊\n"
        "Batafsil ma'lumot uchun botga o'tib /help buyrug'ini yuboring. ✨"
    ),
    "help_text": (
        "Quyidagi buyruqlar faqat guruh adminlari uchun:\n"
        "\n"
        "Guruhda yuboring:\n"
        "\n"
        "/stats — guruhdagi taklif/qo'shish reytingi. Natija botdan keladi.\n"
        "/chat_id — guruh ID sini botdan yuboradi.\n"
        "/history — tarix botdan keladi (10 tadan sahifalanadi).\n"
        "\n"
        "Botga yuboring:\n"
        "\n"
        "/history <chat_id> — tarixni 10 tadan sahifalaydi.\n"
        "/start — bot haqida qisqa ma'lumot.\n"
        "/help — ushbu qo'llanma.\n"
    ),
}

EVENT_TEMPLATES = {
    "join_invite": "{time} {target} havola orqali qo'shildi (muallif {actor})",
    "join_added": "{time} {actor} {target} ni qo'shdi",
    "join_unknown": "{time} {target} qo'shildi (noma'lum)",
    "leave_left": "{time} {target} chiqib ketdi",
    "leave_removed": "{time} {actor} {target} ni chiqarib yubordi",
    "ban": "{time} {actor} {target} ni taqiqladi",
    "unban": "{time} {actor} {target} ni taqiqdan chiqardi",
}
