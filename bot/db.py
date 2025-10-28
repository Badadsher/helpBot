from sqlmodel import SQLModel, create_engine, Session, select
import asyncio
from bot.models.user import User
from sqlmodel import SQLModel, create_engine, Session, select

# Временно SQLite (можно потом сменить на PostgreSQL)
DATABASE_URL = "sqlite:///helpbot.db"  # или PostgreSQL
engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Session:
    """Возвращает сессию SQLAlchemy, которую можно использовать с 'with'"""
    return Session(engine)

# ------------------------
# Функция для получения премиум-пользователей
def get_premium_users():
    """Возвращает список пользователей с is_premium=True"""
    from bot.models.user import User

    with Session(engine) as session:
        statement = select(User).where(User.is_premium == True)
        users = session.exec(statement).all()
        return users

# ------------------------
# Функция для инициализации базы
def init_db():
    """Создание всех таблиц"""
    from bot.models.user import User
    from bot.models.message import MessageHistory, UserSummary
    from bot.models.payment import PaymentHistory
    SQLModel.metadata.create_all(engine)
