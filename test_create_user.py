from sqlmodel import select
from bot.db import get_session
from bot.models.user import User
from datetime import datetime

def create_test_premium_user():
    # используем Session напрямую
    from bot.db import engine
    from sqlmodel import Session

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.telegram_id == 597797468)
        ).first()
        if not user:
            user = User(
                telegram_id=597797468, 
                name="Тест", 
                gender="м", 
                age=25,
                is_premium=True,
                created_at=datetime.now(),
                summary="Пользователь интересуется мотивацией и самопознанием"
            )
            session.add(user)
            session.commit()
    print("✅ Тестовый премиум пользователь создан")

if __name__ == "__main__":
    create_test_premium_user()
