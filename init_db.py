from sqlmodel import SQLModel
from bot.db import engine
from bot.models.user import User

def init_db():
    SQLModel.metadata.create_all(engine)
    print("✅ База и таблицы созданы")

if __name__ == "__main__":
    init_db()
