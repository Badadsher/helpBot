from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    is_premium: bool = False
    premium_until: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active_dialog: bool = Field(default=False)