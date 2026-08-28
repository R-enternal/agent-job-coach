"""面试 API：启动 / 作答 / 历史复盘"""

from fastapi import APIRouter, Depends
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.agent.interview_agent import (
    extract_interrupt,
    graph_config,
    interview_graph,
)
from app.agent.report import generate_review_report
from app.database import get_db
from app.schemas import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewStartRequest,
    InterviewStartResponse,
)
from app.services.memory import (
    append_interview_event,
    get_interview_events,
)
from app.services.records import (
    list_interviews,
    save_answer_record,
    save_interview_record,
)

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])


@router.post("/start", response_model=InterviewStartResponse)
async def start(req: InterviewStartRequest):
    """启动一场模拟面试：图运行到 ask 节点 interrupt，返回第一题"""
    result = interview_graph.invoke(
        {
            "topic": req.topic,
            "round": 0,
            "asked": [],
            "scores": [],
            "current_question": "",
            "answer": "",
            "last_feedback": "",
            "waiting_for": "",
            "need_deep_dive": False,
            "deep_dive_round": 0,
            "done": False,
        },
        config=graph_config(req.session_id),
    )
    payload = extract_interrupt(result) or {}
    return InterviewStartResponse(
        session_id=req.session_id,
        topic=req.topic,
        round=payload.get("round", 1),
        question=payload.get("question", ""),
        hint="请用 2-3 分钟回答，尽量结构化：先结论、再展开、最后量化。",
    )


@router.post("/answer", response_model=InterviewAnswerResponse)
async def answer(req: InterviewAnswerRequest):
    """提交回答：图从 interrupt 恢复 → judge 评分 → 出下一题或结束"""
    # 必须用 Command(resume=...) 恢复 interrupt 暂停的图执行
    result = interview_graph.invoke(
        Command(resume=req.answer),
        config=graph_config(req.session_id),
    )
    rounds = result.get("asked", [])
    round_no = result.get("round", 1)
    question = result.get("current_question", "")
    score = float(result["scores"][-1]) if result.get("scores") else 0.0
    feedback = result.get("last_feedback", "")

    append_interview_event(req.session_id, {
        "round": round_no,
        "question": question,
        "answer": req.answer,
        "score": score,
        "feedback": feedback,
    })

    db: Session = next(get_db())
    try:
        save_answer_record(db, req.session_id, round_no, question, req.answer, feedback, score)
    finally:
        db.close()

    payload = extract_interrupt(result)
    if payload is not None:
        # 还有下一题或深挖追问
        return InterviewAnswerResponse(
            session_id=req.session_id,
            round=payload.get("round", round_no + 1),
            question=payload.get("question", ""),
            score=score,
            feedback=feedback,
            next_question=payload.get("question"),
            next_type=payload.get("type", "question"),
            finished=False,
        )

    # 面试结束：生成复盘报告并落库
    events = get_interview_events(req.session_id)
    topic = result.get("topic", "mixed")
    summary = generate_review_report(topic, events) if events else "（无记录）"
    avg = sum(events[i]["score"] for i in range(len(events))) / len(events) if events else 0.0
    db = next(get_db())
    try:
        save_interview_record(
            db, req.session_id, topic, len(events), avg, summary
        )
    finally:
        db.close()
    return InterviewAnswerResponse(
        session_id=req.session_id,
        round=round_no,
        question=question,
        score=score,
        feedback=feedback,
        finished=True,
        summary=summary,
    )


@router.get("/history")
async def history(session_id: str):
    """查看某场面试的事件记录"""
    events = get_interview_events(session_id)
    return {"session_id": session_id, "rounds": events}


@router.get("/records")
async def records(db: Session = Depends(get_db)):
    """历史面试汇总"""
    items = list_interviews(db)
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "topic": r.topic,
            "rounds": r.rounds,
            "avg_score": r.avg_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in items
    ]
