from sqlmodel import select, Session
from collections import deque
from bot.db import engine
from bot.models.user import User
from bot.services.gpt_client import ask_gpt
from bot.models.message import UserSummary
from datetime import datetime
from bot.models.message import MessageHistory
# Хранение последних сообщений в памяти
user_recent_messages = {}
user_message_counter = {}  # Счетчик сообщений до обновления summary

SUMMARY_BATCH = 3        # Добавлять summary каждые 3 сообщения
MAX_MESSAGES = 15        # Максимум сообщений в MessageHistory
TRIM_MESSAGES = 10       # Удалять старые сообщения при объединении summary

def add_recent_message(user_id: int, message: str):
    """Добавляет сообщение в буфер последних сообщений и увеличивает счётчик."""
    if user_id not in user_recent_messages:
        user_recent_messages[user_id] = deque(maxlen=50)
        user_message_counter[user_id] = 0
    user_recent_messages[user_id].append(message)
    user_message_counter[user_id] += 1

def get_summary(user_id: int) -> str:
    """Возвращает объединённый текст всех summary пользователя."""
    with Session(engine) as session:
        summaries = session.exec(
            select(UserSummary)
            .where(UserSummary.user_id == user_id)
            .order_by(UserSummary.updated_at)
        ).all()
        return "\n".join([s.summary_text for s in summaries])

def get_recent_messages(user_id: int):
    """Возвращает последние сообщения пользователя."""
    return list(user_recent_messages.get(user_id, []))

async def compress_summary(old_summary: str, messages: list, user_data: dict = None) -> str:
    """Асинхронно обновляет summary через GPT на основе новых сообщений и данных пользователя."""
    user_info = ""
    if user_data:
        user_info = f"Имя: {user_data.get('name')}, Пол: {user_data.get('gender')}, Возраст: {user_data.get('age')}\n"
    prompt = (
        f"Ты психолог. Обнови краткий профиль пользователя на основе следующих сообщений:\n"
        f"{messages}\n"
        f"{user_info}"
        f"Старый профиль: {old_summary}\n"
        f"Сохрани только важное, убери лишние детали, сохрани тон общения и основные проблемы. Но не потеряй ничего важного, имена и ситуации, чтоб можно было продолжать диалоги с пользователем"
    )
    system_msg = {"role": "system", "content": "Ты эксперт по психологии и работе с пользователями."}
    user_msg = {"role": "user", "content": prompt}
    return await ask_gpt([system_msg, user_msg])

async def update_summary_if_needed(user_id: int):
    """
    Обновляет UserSummary, если прошло >= SUMMARY_BATCH сообщений.
    Также объединяет старые summary и удаляет старые сообщения, если их слишком много.
    """
    if user_message_counter.get(user_id, 0) >= SUMMARY_BATCH:
        recent_messages = get_recent_messages(user_id)
        last_messages_text = "\n".join(recent_messages[-SUMMARY_BATCH:])

        with Session(engine) as session:
            # Получаем данные пользователя
            user = session.exec(select(User).where(User.telegram_id == user_id)).first()
            user_data = {"name": user.name, "gender": user.gender, "age": user.age} if user else {}

            # Создаем новый summary на основе последних сообщений
            new_summary_text = await compress_summary("", last_messages_text, user_data)
            new_summary = UserSummary(
                user_id=user_id,
                summary_text=new_summary_text,
                updated_at=datetime.utcnow()
            )
            session.add(new_summary)
            session.commit()

            # Проверяем переполнение MessageHistory
            messages = session.exec(
                select(MessageHistory)
                .where(MessageHistory.user_id == user_id)
                .order_by(MessageHistory.created_at)
            ).all()
            if len(messages) > MAX_MESSAGES:
                # Получаем все summary для пользователя
                summaries = session.exec(
                    select(UserSummary)
                    .where(UserSummary.user_id == user_id)
                    .order_by(UserSummary.updated_at)
                ).all()
                last_5_messages = "\n".join([m.content for m in messages[-5:]])
                combined_text = "\n".join([s.summary_text for s in summaries] + [last_5_messages])
                combined_summary_text = await compress_summary("", combined_text, user_data)

                # Создаем объединённый summary
                combined_summary = UserSummary(
                    user_id=user_id,
                    summary_text=combined_summary_text,
                    updated_at=datetime.utcnow()
                )
                session.add(combined_summary)

                # Удаляем старые summary и старые сообщения
                for s in summaries:
                    session.delete(s)
                for m in messages[:TRIM_MESSAGES]:
                    session.delete(m)
                session.commit()

        # Сбрасываем счётчик сообщений
        user_message_counter[user_id] = 0