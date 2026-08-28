"""MySQL 记录：面试汇总 + 答题明细"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnswerRecord, InterviewRecord


def save_interview_record(
    db: Session,
    session_id: str,
    topic: str,
    rounds: int,
    avg_score: float,
    summary: str,
) -> InterviewRecord:
    rec = InterviewRecord(
        session_id=session_id,
        topic=topic,
        rounds=rounds,
        avg_score=round(avg_score, 2),
        summary=summary,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def save_answer_record(
    db: Session,
    session_id: str,
    round_no: int,
    question: str,
    answer: str,
    feedback: str,
    score: float,
) -> None:
    db.add(
        AnswerRecord(
            session_id=session_id,
            round=round_no,
            question=question,
            answer=answer,
            feedback=feedback,
            score=score,
        )
    )
    db.commit()


def list_interviews(db: Session, limit: int = 20) -> list[InterviewRecord]:
    return list(
        db.scalars(
            select(InterviewRecord).order_by(InterviewRecord.created_at.desc()).limit(limit)
        ).all()
    )
