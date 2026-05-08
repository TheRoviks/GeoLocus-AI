from aiogram import Router

from bot.handlers import list as list_h
from bot.handlers import reminders, settings, start


def build_root_router() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(settings.router)
    root.include_router(list_h.router)
    root.include_router(reminders.router)  # catch-all last
    return root
