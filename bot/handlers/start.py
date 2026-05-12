from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards.reply import main_menu
from core import strings
from models.user import User

router = Router(name="start")


@router.message(CommandStart())
async def on_start(message: Message, user: User) -> None:
    await message.answer(
        strings.START_GREETING.format(name=user.first_name or "друг"),
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def on_help(message: Message) -> None:
    await message.answer(strings.HELP, parse_mode="HTML")
