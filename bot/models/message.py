from sqlmodel import SQLModel, Field, ForeignKey
from datetime import datetime

class MessageHistory(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    role: str  # "user" или "bot"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSummary(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    summary_text: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MessageCounter(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    total_messages: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)