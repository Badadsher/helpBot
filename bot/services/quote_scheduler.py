from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.db import get_premium_users
from bot.services.gpt_client import ask_gpt
import random
import asyncio

scheduler = AsyncIOScheduler()

async def generate_quote():
    prompt = (
        "Сгенерируй короткую философски мотивирующую цитату для человека, "
        "которая вдохновляет на действия и позитивные изменения. "
        "Должна быть уникальной, лаконичной и мотивирующей."
    )
    messages = [
        {"role": "system", "content": "Ты генератор мотивационных цитат."},
        {"role": "user", "content": prompt}
    ]
    return await ask_gpt(messages)


async def send_daily_quotes(bot):
    users = get_premium_users()  # просто вызов, без await
    for user in users:
        try:
            quote = await generate_quote()
            await bot.send_message(user.telegram_id, f"✨ Мотивация на сегодня:\n{quote}")
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"Ошибка при отправке цитаты пользователю {user.telegram_id}: {e}")



def start_scheduler(bot):
    """
    Запуск APScheduler для ежедневной отправки премиум-цитат.
    """
    scheduler.add_job(send_daily_quotes, 'interval', hours=24, args=[bot])
    scheduler.start()
