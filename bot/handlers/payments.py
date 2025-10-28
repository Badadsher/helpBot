from aiogram import Router, types
from datetime import datetime, timedelta
from sqlmodel import Session, select
from bot.db import engine
from bot.models.user import User
from bot.models.payment import PaymentHistory
from bot.config import settings

router = Router()

# ===============================
# Создание счета на премиум
# ===============================
@router.callback_query(lambda c: c.data.startswith("buy_premium_"))
async def buy_premium(callback: types.CallbackQuery):
    await callback.answer()  # убираем "крутилку" у кнопки
    plan = callback.data.split("_")[2]  # 1m / 3m / 12m

    plan_map = {
        "1m": {"days": 30, "price": 99_00, "title": "Премиум на 1 месяц"},
        "3m": {"days": 90, "price": 990_00, "title": "Премиум на 3 месяца"},
        "12m": {"days": 365, "price": 4990_00, "title": "Премиум на 12 месяцев"},
    }

    info = plan_map.get(plan)
    if not info:
        await callback.message.answer("❌ Неверный тип подписки.")
        return

    # Получаем внутренний ID пользователя
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == callback.from_user.id)).first()
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден в базе.")
            return
        user_db_id = user.id

    # Отправляем счет с payload = внутренний ID
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=info["title"],
        description="Подписка на психобота 💎",
        payload=f"premium_{plan}_{user_db_id}",  # payload содержит внутренний ID
        provider_token=settings.provider_token,  
        currency="RUB",
        prices=[types.LabeledPrice(label=info["title"], amount=info["price"])],
        start_parameter="premium-subscription"
    )

# ===============================
# Подтверждение оплаты (pre_checkout)
# ===============================
@router.pre_checkout_query(lambda q: True)
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    # обязательно отвечаем Telegram
    await pre_checkout_query.answer(ok=True)

# ===============================
# Обработка успешной оплаты
# ===============================
@router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload  # например "premium_1m_42"
    
    try:
        _, plan, user_db_id_str = payload.split("_")
        user_db_id = int(user_db_id_str)
    except Exception:
        await message.answer("⚠️ Ошибка обработки платежа: неверный payload.")
        return

    duration_map = {"1m": 31, "3m": 92, "12m": 365}
    days = duration_map.get(plan, 30)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_db_id)).first()
        if not user:
            await message.answer("⚠️ Пользователь не найден в базе.")
            return

        # Активируем премиум
        user.is_premium = True
        user.premium_until = datetime.utcnow() + timedelta(days=days)
        session.add(user)

        # Сохраняем платеж
        payment_record = PaymentHistory(
            user_id=user.id,
            amount=payment.total_amount / 100,  # в рублях
            currency=payment.currency,
            duration_days=days,
            created_at=datetime.utcnow()
        )
        session.add(payment_record)
        session.commit()

        until_str = user.premium_until.strftime("%d.%m.%Y")
        await message.answer(
            f"✅ Спасибо за оплату! 💎\n"
            f"Твоя премиум-подписка активна до *{until_str}*. Наслаждайся расширенными возможностями!",
            parse_mode="Markdown"
        )
