from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.db import get_premium_users
from bot.models.usermood import UserMood
from bot.db import engine
from sqlmodel import Session
import asyncio

scheduler = AsyncIOScheduler()

async def send_daily_mood_poll(bot):
    users = get_premium_users()
    for user in users:
        try:
            keyboard = {
                "inline_keyboard": [[
                    {"text": str(i), "callback_data": f"mood_{i}"} for i in range(1,6)
                ]]
            }
            await bot.send_message(
                user.telegram_id,
                "Какое у тебя настроение сегодня? (1-5)",
                reply_markup=keyboard
            )
            await asyncio.sleep(0.5)  # чтобы не спамить сервер
        except Exception as e:
            print(f"Ошибка при отправке опроса пользователю {user.telegram_id}: {e}")

def start_mood_scheduler(bot):
    """
    Запуск APScheduler для ежедневной отправки опроса настроения премиум-пользователям.
    """
    # Запуск каждый день в 12:00
    scheduler.add_job(send_daily_mood_poll, 'cron', hour=12, minute=0, args=[bot])
    scheduler.start()
