from sqlmodel import select, Session
from collections import deque
from bot.db import engine
from bot.models.user import User
from bot.services.gpt_client import ask_gpt

# Хранение последних сообщений в памяти
user_recent_messages = {}
user_message_counter = {}  # Счетчик сообщений до обновления summary

def add_recent_message(user_id: int, message: str):
    if user_id not in user_recent_messages:
        user_recent_messages[user_id] = deque(maxlen=50)
        user_message_counter[user_id] = 0
    user_recent_messages[user_id].append(message)
    user_message_counter[user_id] += 1

def get_recent_messages(user_id: int):
    return list(user_recent_messages.get(user_id, []))

def get_summary(user_id: int) -> str:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == user_id)).first()
        return user.summary if user and user.summary else ""

def save_summary(user_id: int, new_summary: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == user_id)).first()
        if user:
            user.summary = new_summary
            session.add(user)
            session.commit()

async def compress_summary(old_summary: str, messages: list) -> str:
    """Асинхронно обновляет summary через GPT на основе новых сообщений."""
    prompt = (
        f"Ты психолог. Обнови краткий профиль пользователя на основе следующих сообщений:\n"
        f"{messages}\n"
        f"Старый профиль: {old_summary}\n"
        f"Сохрани только важное, убери лишние детали, сохрани тон общения и основные проблемы."
    )
    system_msg = {"role": "system", "content": "Ты эксперт по психологии и работе с пользователями."}
    user_msg = {"role": "user", "content": prompt}
    return await ask_gpt([system_msg, user_msg])

async def update_summary_if_needed(user_id: int):
    """Обновляет summary, если прошло >= 3 сообщений с момента последнего обновления."""
    if user_message_counter.get(user_id, 0) >= 3:
        old_summary = get_summary(user_id)
        recent_messages = get_recent_messages(user_id)
        new_summary = await compress_summary(old_summary, recent_messages)
        save_summary(user_id, new_summary)
        user_message_counter[user_id] = 0
