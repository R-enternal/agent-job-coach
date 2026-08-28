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
    detail: list | None = None,
) -> InterviewRecord:
    # 幂等：同 session_id 已落库则更新（覆盖写），防结束流程重入造成唯一键冲突
    rec = db.scalar(
        select(InterviewRecord).where(InterviewRecord.session_id == session_id)
    )
    if rec is not None:
        rec.topic = topic
        rec.rounds = rounds
        rec.avg_score = round(avg_score, 2)
        rec.summary = summary
        rec.detail = detail or []
        db.commit()
        db.refresh(rec)
        return rec
    rec = InterviewRecord(
        session_id=session_id,
        topic=topic,
        rounds=rounds,
        avg_score=round(avg_score, 2),
        summary=summary,
        detail=detail or [],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_interviews_by_topic(db: Session, topic: str) -> list[InterviewRecord]:
    """同主题历史场次（按时间正序，复盘对比用）"""
    return list(
        db.scalars(
            select(InterviewRecord)
            .where(InterviewRecord.topic == topic)
            .order_by(InterviewRecord.created_at.asc())
        ).all()
    )


def save_answer_record(
    db: Session,
    session_id: str,
    round_no: int,
    question: str,
    answer: str,
    feedback: str,
    score: float,
    skipped: bool = False,
) -> None:
    db.add(
        AnswerRecord(
            session_id=session_id,
            round=round_no,
            question=question,
            answer=answer,
            feedback=feedback,
            score=score,
            skipped=skipped,
        )
    )
    db.commit()


def list_interviews(db: Session, limit: int = 20) -> list[InterviewRecord]:
    return list(
        db.scalars(
            select(InterviewRecord).order_by(InterviewRecord.created_at.desc()).limit(limit)
        ).all()
    )
