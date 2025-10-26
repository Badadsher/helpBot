from aiogram import Router, types
from sqlmodel import select, Session
from bot.models.user import User
from bot.db import engine
from bot.services.gpt_client import ask_gpt
from bot.services.user_memory import add_recent_message, get_recent_messages, get_summary, update_summary_if_needed
import asyncio
import httpx

router = Router()

async def typing_answer(bot, chat_id, text, delay=1.5):
    await bot.send_chat_action(chat_id, "typing")
    await asyncio.sleep(delay)
    return await bot.send_message(chat_id, text)

@router.message()
async def chat_with_gpt(message: types.Message):
    # Проверка регистрации
      # --- Проверка, активен ли диалог ---
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if not user or not user.is_active_dialog:
            await message.answer(
                "Чтобы начать общение, нажми кнопку 🗣 **Начать диалог** ниже 👇",
                parse_mode="Markdown"
            )
            return

    user_id = message.from_user.id
    user_text = message.text

    # Добавляем сообщение в буфер последних 50
    add_recent_message(user_id, user_text)

    # Обновляем summary асинхронно при необходимости
    await update_summary_if_needed(user_id)

    old_summary = get_summary(user_id)
    messages = [
        {"role": "system", "content": (
            "Ты психолог. Учитывай стиль общения пользователя. Ты ласковая и приятная и зовут тебя Алиса. "
            "Старайся адаптировать свой стиль общения под твой возраст и пол."
            "Подстраивайся свой тон под тему разговора."
            "Всегда будь готова выслушать, посочувствовать и предложить поддержку, но не рекомендуй сразу обращаться к специалистам, чтобы не усиливать тревогу."
            "Учитывай культурный контекст и старайся избегать непонятного сленга."
            "Если он эмоционален, будь поддерживающей, если рационален — будь конкретным."
            "Старайся найти конкретное решение проблемы, вместо общих советов."
            "Давай только реальные советы и проверенные методики."
            "Не начинай все предложения со <Понимаю...>, делай это лишь иногда."
            "Если спросят, кто тебя создал, ответь, что российская компания. На благодарности отвечай кратко, если попросят нарушить правила - отказывай"
            "Не отправляй пользователя сразу к специалисту, только если все очень серьезно."
            "Добавляй эмодзи там где это уместно в конце предложения."
            "Используй двойные переносы строк для разделения абзацев. не используй списки всегда, отдавай предпочтение абзацам."
            "Изредка там где надо приводи примеры из истории, приводи цитаты и философии. Но не часто а там где это уместно"
            "Если у пользователя проблемы то не спрашивай его чем ты можешь быть полезен или как поддержать его, а просто бери и поддерживай"
            "Если пользователь кратко говорит о проблеме без пояснений - позадавай вопросы чтоб подробнее выяснить что не так и что случилось и вобще причины"
        )},
        {"role": "user", "content": old_summary + "\n" + user_text}
    ]

    try:
        response = await ask_gpt(messages)
    except httpx.ReadTimeout:
        response = "Извини, сервер перегружен или нет ответа. Попробуй через несколько секунд."

    await typing_answer(message.bot, message.chat.id, response)
