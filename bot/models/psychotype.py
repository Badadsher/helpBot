from sqlmodel import SQLModel, Field
from datetime import datetime

class UserPsychotype(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    psychotype: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
