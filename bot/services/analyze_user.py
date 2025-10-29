from datetime import datetime, timedelta
from sqlmodel import Session, select
from bot.db import engine
from bot.models.message import UserSummary
from bot.models.psychotype import UserPsychotype
from bot.models.weekly_report import WeeklyReport
from bot.services.gpt_client import ask_gpt  # асинхронная функция

async def analyze_user_profile(user_id: int):
    """Асинхронный анализ: психотип и психологический отчёт пользователя"""
    
    # --- Работа с БД синхронно ---
    with Session(engine) as session:
        # Берём все summary пользователя
        summaries = session.exec(
            select(UserSummary).where(UserSummary.user_id == user_id)
        ).all()

        # Берём существующий психотип
        psychotype = session.exec(
            select(UserPsychotype).where(UserPsychotype.user_id == user_id)
        ).first()

    # --- Психотип ---
    if len(summaries) >= 20 and not psychotype:
        full_text = "\n".join([s.summary_text for s in summaries])
        prompt = (
            "На основе психологических сводок ниже определи психотип человека. "
            "Ответь только одним словом с маленькой буквы.\n\n"
            f"{full_text}"
        )

        psychotype_text = await ask_gpt([
            {"role": "system", "content": "Ты психологический аналитик, отвечай лаконично и по сути."},
            {"role": "user", "content": prompt}
        ])
        psychotype_text = psychotype_text.strip().split()[0]

        # Сохраняем психотип
        with Session(engine) as session:
            new_type = UserPsychotype(user_id=user_id, psychotype=psychotype_text)
            session.add(new_type)
            session.commit()
            psychotype = new_type

    # --- Психологический отчёт ---
    week_ago = datetime.utcnow() - timedelta(days=7)

    with Session(engine) as session:
        # Берём последний отчёт
        last_report = session.exec(
            select(WeeklyReport)
            .where(WeeklyReport.user_id == user_id)
            .order_by(WeeklyReport.created_at.desc())
        ).first()

        # Берём summary за последнюю неделю
        week_summaries = session.exec(
            select(UserSummary)
            .where(UserSummary.user_id == user_id)
            .where(UserSummary.updated_at >= week_ago)
            .order_by(UserSummary.updated_at)
        ).all()

    # Генерация нового отчёта только если summary >=5 и нет отчёта за эту неделю
    if len(week_summaries) >= 5 and (not last_report or last_report.created_at < week_ago):
        text = "\n".join([s.summary_text for s in week_summaries])
        prompt = (
            "На основе сводок за неделю сделай краткий психологический отчёт — одно предложение: "
            "что изменилось в эмоциональном состоянии человека. Без вступлений и выводов. С маленькой буквы\n\n"
            f"{text}"
        )

        report_text = await ask_gpt([
            {"role": "system", "content": "Ты психологический аналитик, отвечай лаконично и по сути."},
            {"role": "user", "content": prompt}
        ])

        with Session(engine) as session:
            new_report = WeeklyReport(user_id=user_id, report_text=report_text.strip())
            session.add(new_report)
            session.commit()
            last_report_text = new_report.report_text
    else:
        last_report_text = last_report.report_text if last_report else "Отчёт за неделю появится позже."

    return {
        "psychotype": psychotype.psychotype if psychotype else "Анализ в процессе...",
        "weekly_report": last_report_text
    }
