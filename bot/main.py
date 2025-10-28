import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from sqlmodel import SQLModel

from bot.config import settings
from bot.db import engine
from bot.handlers import start, chat, payments   # импортируем оба роутера
from bot.services.quote_scheduler import start_scheduler
from bot.services.mood_scheduler import start_mood_scheduler
from bot.services.user_memory import update_summary_if_needed, get_summary, get_recent_messages
from bot.services.premium_checker import premium_checker


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(chat.router)
    dp.include_router(payments.router)
    # 1️⃣ Создаём таблицы в базе до любых операций
    SQLModel.metadata.create_all(engine)

   

    # Запуск планировщиков
    start_scheduler(bot)
    start_mood_scheduler(bot)
    asyncio.create_task(premium_checker(bot))
    print("🤖 Бот запущен и готов к работе")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
