# bot/services/premium_checker.py
from datetime import datetime, timedelta
from aiogram import Bot
from sqlmodel import Session, select
from bot.db import engine
from bot.models.user import User
import asyncio
async def premium_checker(bot: Bot):
    """
    Проверяет подписки пользователей:
    - за 2 дня до окончания отправляет предупреждение
    - по истечении срока отключает премиум и уведомляет
    """
    print("🔁 Premium checker started...")

    while True:
        now = datetime.utcnow()

        with Session(engine) as session:
            users = session.exec(
                select(User).where(User.is_premium == True)
            ).all()

            for user in users:
                if not user.premium_until:
                    continue

                days_left = (user.premium_until - now).days

                # 🔔 Напоминание за 2 дня до окончания
                if days_left == 2:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            "💎 Напоминаем: твоя премиум-подписка истекает через *2 дня*.\n\n"
                            "Продли, чтобы не потерять доступ к:\n"
                            "✨ ежедневным цитатам\n"
                            "📊 метрикам настроения\n"
                            "🚀 и безлимитному диалогу.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"⚠️ Ошибка отправки напоминания {user.telegram_id}: {e}")

                # ❌ Если срок истёк — отключаем
                if user.premium_until < now:
                    user.is_premium = False
                    user.premium_until = None
                    session.add(user)
                    session.commit()

                    try:
                        await bot.send_message(
                            user.telegram_id,
                            "💔 Срок твоей премиум-подписки истёк.\n\n"
                            "Ты можешь продлить её в разделе 💎 *Премиум подписка*.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"⚠️ Ошибка уведомления об окончании {user.telegram_id}: {e}")

        print("✅ Premium check completed.")
        await asyncio.sleep(24 * 60 * 60)  # 1 раз в сутки
