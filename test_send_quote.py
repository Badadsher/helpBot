import asyncio
from bot.services.quote_scheduler import send_daily_quotes
from bot.services.mood_scheduler import send_daily_mood_poll
from aiogram import Bot
from bot.config import settings

async def test_quote():
    bot = Bot(token=settings.bot_token)
    await send_daily_quotes(bot)
    await send_daily_mood_poll(bot)
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_quote())
