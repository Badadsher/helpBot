from sqlmodel import SQLModel, Field, ForeignKey
from datetime import datetime

class PaymentHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: float
    currency: str
    duration_days: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan: str | None = Field(default=None)