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


def list_item_actions(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"list:del:{reminder_id}")]
        ]
    )


def pagination(page: int, total_pages: int) -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []
    if page > 1:
        row.append(InlineKeyboardButton(text="←", callback_data=f"list:page:{page - 1}"))
    row.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        row.append(InlineKeyboardButton(text="→", callback_data=f"list:page:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


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
