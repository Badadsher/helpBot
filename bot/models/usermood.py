from sqlmodel import SQLModel, Field, select, Session
from datetime import datetime, timedelta
from bot.db import engine  # твой движок базы данных

class UserMood(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int  # telegram_id пользователя
    mood: int  # от 1 до 5
    created_at: datetime = Field(default_factory=datetime.utcnow)


def get_weekly_average(user_id: int) -> float:
    week_ago = datetime.utcnow() - timedelta(days=7)
    with Session(engine) as session:
        moods = session.exec(
            select(UserMood.mood)
            .where(UserMood.user_id == user_id)
            .where(UserMood.created_at >= week_ago)
        ).all()
    if moods:
        return sum(moods) / len(moods)
    return 0.0
