from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TZ_PRESETS: list[tuple[str, str]] = [
    ("МСК (Europe/Moscow)", "Europe/Moscow"),
    ("Калининград (Europe/Kaliningrad)", "Europe/Kaliningrad"),
    ("Самара (Europe/Samara)", "Europe/Samara"),
    ("Екатеринбург (Asia/Yekaterinburg)", "Asia/Yekaterinburg"),
    ("Омск (Asia/Omsk)", "Asia/Omsk"),
    ("Новосибирск (Asia/Novosibirsk)", "Asia/Novosibirsk"),
    ("Иркутск (Asia/Irkutsk)", "Asia/Irkutsk"),
    ("Якутск (Asia/Yakutsk)", "Asia/Yakutsk"),
    ("Владивосток (Asia/Vladivostok)", "Asia/Vladivostok"),
    ("UTC", "UTC"),
    ("Алматы (Asia/Almaty)", "Asia/Almaty"),
    ("Ташкент (Asia/Tashkent)", "Asia/Tashkent"),
    ("Минск (Europe/Minsk)", "Europe/Minsk"),
    ("Киев (Europe/Kiev)", "Europe/Kiev"),
    ("Берлин (Europe/Berlin)", "Europe/Berlin"),
]

QUIET_PRESETS: list[tuple[str, str]] = [
    ("23:00 → 08:00", "23:00-08:00"),
    ("22:00 → 08:00", "22:00-08:00"),
    ("00:00 → 07:00", "00:00-07:00"),
    ("Отключить", "off"),
]


def reminder_actions(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"rem:cancel:{reminder_id}"),
            ]
        ]
    )



def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="settings:tz")],
            [InlineKeyboardButton(text="🌙 Тихие часы", callback_data="settings:quiet")],
        ]
    )


def tz_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"settings:tz:{value}")]
        for label, value in TZ_PRESETS
    ]
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiet_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"settings:quiet:{value}")]
        for label, value in QUIET_PRESETS
    ]
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_done_kb(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data=f"rem:done:{reminder_id}"),
                InlineKeyboardButton(text="⏰ +10 мин", callback_data=f"rem:snooze:{reminder_id}"),
            ]
        ]
    )
