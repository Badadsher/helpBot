from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlmodel import select, Session
from bot.models.user import User
from bot.db import engine
from datetime import datetime
import asyncio
from sqlalchemy import func
from bot.models.usermood import UserMood
from bot.models.usermood import UserMood, get_weekly_average
from bot.models.message import MessageHistory
router = Router()
class UserForm(StatesGroup):
    accept_intro = State()  # нажал "Привет👋🏻"
    accept_terms = State()  # нажал "Да✅"
    name = State()
    gender = State()
    age = State()

# Главное меню после регистрации
def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🗣 Начать диалог")],
            [types.KeyboardButton(text="📊 Метрики"), types.KeyboardButton(text="📜 Условия")],
            [types.KeyboardButton(text="❓ Вопрос-ответ"), types.KeyboardButton(text="💎 Премиум подписка")]
        ],
        resize_keyboard=True
    )

# Клавиатура во время активного диалога
def dialog_keyboard() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚪 Завершить диалог")]
        ],
        resize_keyboard=True
    )

# ===========================
# /start
# ===========================
@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            await message.bot.send_chat_action(message.chat.id, "typing")
            await asyncio.sleep(1)
            await message.answer(
                f"С возвращением, {user.name or 'друг'} 👋\n\nВыбери действие ниже:",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

    # Новый пользователь — показываем приветственный текст с кнопкой "Привет👋🏻"
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="Привет👋🏻", callback_data="intro_hello")]]
    )
    await message.answer(
        "Привет! ✨ Я Алиса — ваш личный бот эмоциональной поддержки. Я на связи в любое время и всегда готова помочь! 🤝\n\n"
        "Обо мне:\n"
        "• Конфиденциально и безопасно 🛡️\n"
        "• Мгновенный ответ ⚡\n"
        "• Личный виртуальный собеседник 💬\n"
        "• На связи 24/7 ⏰",
        reply_markup=keyboard
    )
    await state.set_state(UserForm.accept_intro)

# ===========================
# Обработка кнопки "Привет👋🏻"
# ===========================
@router.callback_query(lambda c: c.data == "intro_hello")
async def intro_hello(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="Да✅", callback_data="accept_terms")]]
    )
    await callback.message.edit_text(
        "Я здесь, чтобы обеспечить вам общение, пространство для выражения чувств, поддержку и помочь в поиске новых подходов к личным проблемам 🧠.\n\n"
        "Важное ограничение: Я не заменяю профессиональную помощь. Если ситуация серьезная, пожалуйста, обратитесь к специалисту 🩺.\n\n"
        "Принимаете условия? Нажми 'Да' ✅.",
        reply_markup=keyboard
    )
    await state.set_state(UserForm.accept_terms)

# ===========================
# Обработка кнопки "Да✅"
# ===========================
@router.callback_query(lambda c: c.data.startswith("mood_"))
async def mood_callback(callback: types.CallbackQuery):
    await callback.answer("Сохраняем настроение...")
    user_id = callback.from_user.id
    mood_value = int(callback.data.split("_")[1])

    # Проверка премиума
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == user_id)).first()
        if not user or not user.is_premium:
            await callback.message.answer("Эта функция доступна только для премиум пользователей 🌟")
            return

        # Сохраняем настроение
        user_mood = UserMood(user_id=user_id, mood=mood_value)
        session.add(user_mood)
        session.commit()

    await callback.message.answer(f"Спасибо! Твое настроение {mood_value} сохранено ✅")

# ===========================
# Обработка настроения"
# ===========================
@router.callback_query(lambda c: c.data == "accept_terms")
async def accept_terms(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    sent_message = await callback.message.bot.send_message(
        callback.from_user.id,
        "Отлично! Давай познакомимся. Как тебя зовут? Пришли имя без прочего текста и слов ✏️"
    )
    await state.update_data(name_message_id=sent_message.message_id)
    await state.set_state(UserForm.name)

# ===========================
# Регистрация: имя, пол, возраст
# ===========================
@router.message(UserForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="👨 Мужской", callback_data="gender_m"),
                          types.InlineKeyboardButton(text="👩 Женский", callback_data="gender_f")]]
    )
    sent_message = await message.answer("Выбери свой пол:", reply_markup=keyboard)
    await state.update_data(buttons_message_id=sent_message.message_id)
    await state.set_state(UserForm.gender)

@router.callback_query(lambda c: c.data in ["gender_m", "gender_f"])
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "м" if callback.data == "gender_m" else "ж"
    await state.update_data(gender=gender)

    data = await state.get_data()
    if "buttons_message_id" in data:
        try: await callback.message.delete()
        except: pass

    sent_message = await callback.message.answer("Сколько тебе лет? 📅")
    await state.update_data(age_message_id=sent_message.message_id)
    await state.set_state(UserForm.age)
    await callback.answer()

@router.message(UserForm.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
    except ValueError:
        await message.answer("Возраст должен быть числом. Попробуй снова:")
        return

    data = await state.get_data()
    user = User(
        telegram_id=message.from_user.id,
        name=data["name"],
        gender=data["gender"],
        age=age,
        is_active_dialog=False
    )
    with Session(engine) as session:
        session.add(user)
        session.commit()

    # Удаляем все регистрационные сообщения
    for msg_id in [data.get("name_message_id"), data.get("buttons_message_id"), data.get("age_message_id")]:
        if msg_id:
            try: await message.bot.delete_message(message.chat.id, msg_id)
            except: pass

    await message.bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1)
    await message.answer(
        f"Рад познакомиться, {data['name']}! 👋\n\nТеперь выбери действие ниже:",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ===========================
# Обработка кнопок меню
# ===========================
@router.message(lambda m: m.text == "🗣 Начать диалог")
async def start_dialog(message: types.Message):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            user.is_active_dialog = True
            session.add(user)
            session.commit()

    await message.answer("Диалог начат. Можешь писать всё, что хочешь обсудить 💬", reply_markup=dialog_keyboard())

@router.message(lambda m: m.text == "🚪 Завершить диалог")
async def end_dialog(message: types.Message):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            user.is_active_dialog = False
            session.add(user)
            session.commit()

    await message.answer("Диалог завершён. Что хочешь сделать дальше?", reply_markup=main_menu_keyboard())

@router.message(lambda m: m.text == "📊 Метрики")
async def show_metrics(message: types.Message):
    user_id = message.from_user.id
    with Session(engine) as session:
        user = session.exec(select(User).where(User.telegram_id == user_id)).first()
        if not user or not user.is_premium:
            await message.answer("Раздел Метрики доступен только для премиум пользователей 🌟")
            return

    # Среднее настроение
    avg_mood = get_weekly_average(user_id)
    avg_mood_text = f"{avg_mood:.2f}" if avg_mood else "Информация еще собирается"

    # Количество сообщений
    messages_count = session.exec(
        select(func.count(MessageHistory.id)).where(MessageHistory.user_id == user_id)
    ).one()


    await message.answer(
        f"📊 Твои метрики за неделю:\n"
        f"• Среднее настроение: {avg_mood_text}\n"
        f"• Количество сообщений: {messages_count}\n"
    )

@router.message(lambda m: m.text == "📜 Условия")
async def conditions(message: types.Message):
    await message.answer("📜 Условия использования:\n1. Уважай других.\n2. Не отправляй спам.\n3. Соблюдай этику общения.")

@router.message(lambda m: m.text == "❓ Вопрос-ответ")
async def faq(message: types.Message):
    text = (
        "✨ *Как это устроено?*\n\n"
        "Меня зовут *Алиса*, и я — продукт многолетних разработок в сфере _искусственного интеллекта_.\n"
        "В основе моих алгоритмов лежат обширные знания, полученные в результате изучения человеческих эмоций и коммуникации.\n\n"
        "Это позволяет мне помогать тебе в сложных ситуациях: анализировать проблемы, предлагать решения и давать *персонализированные советы*.\n"
        "Все ответы, которые ты получаешь, генерируются специально для тебя нейросетью — они *уникальны и адаптированы под твой запрос*.\n\n"
        "В диалоге я стараюсь глубже разобраться в твоём вопросе, выдвигаю предположения о возможных причинах трудностей и способах их преодоления. 🍃\n"
        "Я также могу помочь справиться с напряжением, улучшить эмоциональное состояние и найти внутреннюю гармонию.\n\n"
        "Просто расскажи мне о том, что тебя волнует.\n"
        "Моя поддержка будет полезна, если ты:\n"
        "• ищешь совет или помощь в принятии решений,\n"
        "• хочешь, чтобы тебя выслушали,\n"
        "• переживаешь стресс, тревогу или снижение настроения,\n"
        "• нуждаешься в том, чтобы выговориться.\n\n"
        "Я здесь, чтобы помочь осознать корень проблем и подсказать пути их решения.\n\n"
        "— — —\n\n"
        "🔒 *Конфиденциальны ли наши сообщения?*\n\n"
        "Да, абсолютно. Конфиденциальность — это главный принцип моей работы.\n"
        "Вся переписка хранится только *в твоём аккаунте Telegram*, и никто, кроме тебя, не имеет к ней доступа.\n\n"
        "— — —\n\n"
        "🧠 *Могу ли я заменить психолога?*\n\n"
        "Я могу стать *инструментом первой помощи*: дать возможность высказаться, получить поддержку и направление для дальнейших действий.\n"
        "Однако при серьёзных психологических проблемах я *настоятельно рекомендую* обратиться к профессиональному психологу или психотерапевту.\n\n"
        "— — —\n\n"
        "💎 *Что даёт Premium-подписка?*\n\n"
        "Премиум-доступ открывает:\n"
        "• неограниченное общение со мной,\n"
        "• ежедневные мотивирующие сообщения,\n"
        "• умную метрику для отслеживания эмоционального состояния.\n\n"
        "Оформив подписку, ты получаешь поддержку и приятную беседу в любое время суток,\n"
        "а также помогаешь моему развитию и улучшению.\n\n"
        "— — —\n\n"
        "🛠️ *Куда обратиться по вопросам работы бота?*\n\n"
        "Если у тебя есть вопросы, предложения или ты столкнулся с ошибкой — напиши сюда:\n"
        "👉 [@alicepszkhelp](https://t.me/alicepszkhelp)\n\n"
        "— — —\n\n"
        "📌 *Как отменить подписку?*\n\n"
        "Ты можешь отменить подписку *в любой момент*, нажав на кнопку «Отменить подписку» в разделе _Премиум_.\n"
        "Это быстро и просто 💫"
    )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(lambda m: m.text == "💎 Премиум подписка")
async def premium(message: types.Message):
    await message.answer("💎 Премиум подписка откроет доступ к дополнительным возможностям (скоро).")
