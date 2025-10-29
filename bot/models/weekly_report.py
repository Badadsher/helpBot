# bot/models/weekly_report.py
from sqlmodel import SQLModel, Field
from datetime import datetime

class WeeklyReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    report_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
