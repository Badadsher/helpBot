from sqlmodel import select, Session, func
from collections import deque
from bot.db import engine
from bot.models.user import User
from bot.services.gpt_client import ask_gpt
from bot.models.message import UserSummary, MessageHistory
from datetime import datetime

user_recent_messages = {}
user_message_counter = {}

SUMMARY_BATCH = 3
MAX_MESSAGES = 25
TRIM_MESSAGES = 10

def add_recent_message(user_id: int, message: str):
    if user_id not in user_recent_messages:
        user_recent_messages[user_id] = deque(maxlen=50)
        user_message_counter[user_id] = 0
    user_recent_messages[user_id].append(message)
    user_message_counter[user_id] += 1

def get_summary(user_id: int) -> str:
    with Session(engine) as session:
        summaries = session.exec(
            select(UserSummary).where(UserSummary.user_id == user_id).order_by(UserSummary.updated_at)
        ).all()
        return "\n".join([s.summary_text for s in summaries])

def get_recent_messages(user_id: int):
    return list(user_recent_messages.get(user_id, []))

async def compress_summary(old_summary: str, messages: str, user_data: dict = None) -> str:
    user_info = ""
    if user_data:
        user_info = f"Имя: {user_data.get('name')}, Пол: {user_data.get('gender')}, Возраст: {user_data.get('age')}\n"
    prompt = (
        f"Ты психолог. Обнови краткий профиль пользователя на основе следующих сообщений:\n"
        f"{messages}\n"
        f"{user_info}"
        f"Старый профиль: {old_summary}\n"
        "Сохрани только важное, убери лишние детали, сохрани тон общения и основные проблемы."
    )
    system_msg = {"role": "system", "content": "Ты эксперт по психологии и работе с пользователями."}
    user_msg = {"role": "user", "content": prompt}
    return await ask_gpt([system_msg, user_msg])

async def update_summary_if_needed(user_id: int):
    from bot.models.message import UserSummary, MessageHistory
    from sqlmodel import select
    from datetime import datetime

    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return

        user_data = {"name": user.name, "gender": user.gender, "age": user.age}

        # === 1️⃣ Проверяем, сколько всего сообщений ===
        total_messages = session.exec(
            select(func.count(MessageHistory.id)).where(MessageHistory.user_id == user_id)
        ).first()

        # === 2️⃣ Проверяем, сколько summary уже есть ===
        existing_summaries = session.exec(
            select(UserSummary).where(UserSummary.user_id == user_id).order_by(UserSummary.updated_at)
        ).all()
        has_summary = len(existing_summaries) > 0

        # === 3️⃣ Если сообщений стало слишком много — чистим ===
        if total_messages > MAX_MESSAGES:
            old_messages = session.exec(
                select(MessageHistory)
                .where(MessageHistory.user_id == user_id)
                .order_by(MessageHistory.created_at)
                .limit(total_messages - TRIM_MESSAGES)
            ).all()
            for m in old_messages:
                session.delete(m)
            session.commit()

        # === 4️⃣ Если пользователь написал >=3 новых сообщений ===
        if user_message_counter.get(user_id, 0) >= SUMMARY_BATCH:
            recent_messages = get_recent_messages(user_id)
            last_messages_text = "\n".join(recent_messages[-SUMMARY_BATCH:])

            # --- если это первое summary ---
            if not has_summary:
                new_summary_text = await compress_summary(
                    "",  # без старого контекста
                    last_messages_text,
                    user_data
                )

            # --- если summary уже есть ---
            else:
                last_summary_text = existing_summaries[-1].summary_text  # берем последнее
                new_summary_text = await compress_summary(
                    last_summary_text,
                    last_messages_text,
                    user_data
                )

            # --- сохраняем новое summary ---
            new_summary = UserSummary(
                user_id=user_id,
                summary_text=new_summary_text,
                updated_at=datetime.utcnow()
            )
            session.add(new_summary)

            # сбрасываем счётчик сообщений
            user_message_counter[user_id] = 0

            session.commit()

