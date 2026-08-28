"""面试 API：启动（topic / 题单双模式）/ 作答 / 挑题 / 跳过 / 历史复盘

op 协议：resume 负载统一为 {"op": "answer"|"pick"|"skip", ...}，由 route_op 节点分发。
全部端点为同步 def（图 invoke/DB 均为阻塞调用，交 FastAPI 线程池，不堵事件循环）。
"""

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.agent.interview_agent import (
    extract_interrupt,
    graph_config,
    interview_graph,
)
from app.agent.report import generate_review_report
from app.database import get_db
from app.models import QuestionList
from app.schemas import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewPickRequest,
    InterviewSkipRequest,
    InterviewStartRequest,
    InterviewStartResponse,
)
from app.services.memory import (
    append_interview_event,
    get_interview_events,
)
from app.services.records import (
    list_interviews,
    list_interviews_by_topic,
    save_answer_record,
    save_interview_record,
)

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])

_HINT = "请用 2-3 分钟回答，尽量结构化：先结论、再展开、最后量化。"


def _finish_interview(session_id: str, result: dict) -> tuple[str, float]:
    """面试结束统一收尾：复盘报告（带上场对比）+ 落库（含 q_scores detail）。
    返回 (summary, avg)。
    avg 口径 = 每题 final（首答50%+追问均分50%）的均分，skipped 不计——
    与 /compare 的 per_question_final_avg 同口径（2026-08-29 审查统一起见，
    不再按作答事件计分：追问是同题能力暴露的深化，不该与首答平权稀释）。"""
    events = get_interview_events(session_id)
    topic = result.get("topic", "mixed")
    db: Session = next(get_db())
    try:
        prev = [r for r in list_interviews_by_topic(db, topic)
                if r.session_id != session_id]
        prev_avg = prev[-1].avg_score if prev else None
        summary = generate_review_report(topic, events, prev_avg) if events else "（无记录）"
        finals = [q["final"] for q in (result.get("q_scores") or [])
                  if isinstance(q, dict) and not q.get("skipped") and q.get("final") is not None]
        avg = sum(finals) / len(finals) if finals else 0.0
        save_interview_record(
            db, session_id, topic, len(events), avg, summary,
            detail=list(result.get("q_scores") or []),
        )
    finally:
        db.close()
    return summary, avg


def _ensure_running(session_id: str) -> None:
    """已完结场次的防护：图快照存在且无后继节点 = 面试结束，拒绝 resume。
    防止前端重复点击/重试导致图重放、Redis 事件与 MySQL 场次重复写入。"""
    state = interview_graph.get_state(graph_config(session_id))
    if state.created_at and not state.next:
        raise HTTPException(status_code=409, detail="该场次面试已结束，请开启新场次")


def _pending_meta(session_id: str) -> tuple[int, str]:
    """恢复前挂起题的 (round, question)：恢复后 state 已推进到下一题，
    作答记录/事件必须按恢复前的题目归属，否则张冠李戴。"""
    try:
        values = interview_graph.get_state(graph_config(session_id)).values
        return int(values.get("round", 0)), str(values.get("current_question", ""))
    except Exception:
        return -1, ""


def _last_finalized(result: dict, pending_round: int) -> dict | None:
    """本次 invoke 新结算的题（q_scores 末尾且非 skipped 且 round 匹配挂起题）"""
    q_scores = result.get("q_scores") or []
    if q_scores and not q_scores[-1].get("skipped") and q_scores[-1].get("round") == pending_round:
        return q_scores[-1]
    return None


@router.post("/start", response_model=InterviewStartResponse)
def start(req: InterviewStartRequest):
    """启动一场模拟面试：图运行到 ask 节点出题、wait interrupt，返回第一题"""
    questions: list[dict] = []
    qlist_id = 0
    if req.qlist_id is not None:
        db: Session = next(get_db())
        try:
            qlist = db.get(QuestionList, req.qlist_id)
        finally:
            db.close()
        if qlist is None or not (qlist.questions or []):
            raise HTTPException(status_code=404, detail=f"题单不存在或为空: id={req.qlist_id}")
        questions = list(qlist.questions)  # 快照拷入 state，防面试中途题单被改
        qlist_id = qlist.id

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
            "op": "answer",
            "pick_index": 0,
            "qlist_id": qlist_id,
            "questions": questions,
            "q_idx": 0,
            "base_question": "",
            "current_reference": "",
            "cur_first_score": -1.0,
            "cur_followup_scores": [],
            "q_scores": [],
            "judge_degraded": False,
        },
        config=graph_config(req.session_id),
    )
    payload = extract_interrupt(result) or {}
    return InterviewStartResponse(
        session_id=req.session_id,
        topic=req.topic,
        round=payload.get("round", 1),
        question=payload.get("question", ""),
        hint=_HINT,
        progress=payload.get("progress"),
    )


@router.post("/answer", response_model=InterviewAnswerResponse)
def answer(req: InterviewAnswerRequest):
    """提交回答：图从 interrupt 恢复 → route_op → judge 评分 → 出下一题或结束"""
    _ensure_running(req.session_id)
    pending_round, pending_question = _pending_meta(req.session_id)
    result = interview_graph.invoke(
        Command(resume={"op": "answer", "answer": req.answer}),
        config=graph_config(req.session_id),
    )
    round_no = result.get("round", 1)
    question = result.get("current_question", "")
    score = float(result["scores"][-1]) if result.get("scores") else 0.0
    feedback = result.get("last_feedback", "")
    finalized = _last_finalized(result, pending_round)
    # 作答归属恢复前的挂起题（恢复后 current_question 已是下一题/追问）
    answered_round = pending_round if pending_round > 0 else round_no
    answered_question = pending_question or question

    append_interview_event(req.session_id, {
        "round": answered_round,
        "question": answered_question,
        "answer": req.answer,
        "score": score,
        "feedback": feedback,
        "question_score": finalized["final"] if finalized else None,
        "skipped": False,
    })

    db: Session = next(get_db())
    try:
        save_answer_record(db, req.session_id, answered_round,
                           answered_question, req.answer, feedback, score)
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
            question_score=finalized["final"] if finalized else None,
            judge_degraded=bool(result.get("judge_degraded")),
            progress=payload.get("progress"),
        )

    # 面试结束：复盘报告（带上场对比）+ 落库（含 q_scores detail）
    summary, _ = _finish_interview(req.session_id, result)
    return InterviewAnswerResponse(
        session_id=req.session_id,
        round=round_no,
        question=question,
        score=score,
        feedback=feedback,
        finished=True,
        summary=summary,
        question_score=finalized["final"] if finalized else None,
        judge_degraded=bool(result.get("judge_degraded")),
    )


@router.post("/pick", response_model=InterviewAnswerResponse)
def pick(req: InterviewPickRequest):
    """自由挑题：跳到题单第 index 题（当前题作废不记录）"""
    _ensure_running(req.session_id)
    result = interview_graph.invoke(
        Command(resume={"op": "pick", "index": req.index}),
        config=graph_config(req.session_id),
    )
    # pick 后图停在 wait，interrupt 负载即被挑中的题
    payload = extract_interrupt(result) or {}
    return InterviewAnswerResponse(
        session_id=req.session_id,
        round=int(payload.get("round", 0)),
        question=str(payload.get("question", "")),
        score=0.0,
        feedback=f"已切换到第 {req.index + 1} 题",
        next_question=payload.get("question"),
        next_type=payload.get("type", "question"),
        finished=False,
        progress=payload.get("progress"),
    )


@router.post("/skip", response_model=InterviewAnswerResponse)
def skip(req: InterviewSkipRequest):
    """跳过当前题：不计分、不计均分，skipped 标记进 answer_records 与复盘报告"""
    _ensure_running(req.session_id)
    pending_round, pending_question = _pending_meta(req.session_id)
    result = interview_graph.invoke(
        Command(resume={"op": "skip"}),
        config=graph_config(req.session_id),
    )
    # route_op 已把 skipped 条目写入 q_scores，取回写 MySQL + Redis 事件（不静默消失）
    q_scores = result.get("q_scores") or []
    skipped_entry = q_scores[-1] if q_scores and q_scores[-1].get("skipped") else None
    skipped_question = str((skipped_entry or {}).get("question", "")) or pending_question
    skipped_round = int((skipped_entry or {}).get("round", pending_round if pending_round > 0 else 0))

    append_interview_event(req.session_id, {
        "round": skipped_round,
        "question": skipped_question,
        "answer": "",
        "score": 0.0,
        "feedback": "已跳过",
        "question_score": None,
        "skipped": True,
    })
    db: Session = next(get_db())
    try:
        save_answer_record(db, req.session_id, skipped_round, skipped_question,
                           "", "已跳过", 0.0, skipped=True)
    finally:
        db.close()

    payload = extract_interrupt(result)
    if payload is None:
        # 跳过的是最后一题 → 面试结束，走与 answer 相同的收尾
        summary, _ = _finish_interview(req.session_id, result)
        return InterviewAnswerResponse(
            session_id=req.session_id,
            round=skipped_round,
            question=skipped_question,
            score=0.0,
            feedback="已跳过",
            finished=True,
            summary=summary,
            skipped=True,
        )
    return InterviewAnswerResponse(
        session_id=req.session_id,
        round=int(payload.get("round", skipped_round)),
        question=str(payload.get("question", "")),
        score=0.0,
        feedback="已跳过",
        next_question=payload.get("question"),
        next_type=payload.get("type", "question"),
        finished=False,
        skipped=True,
        progress=payload.get("progress"),
    )


@router.get("/history")
def history(session_id: str):
    """查看某场面试的事件记录（含 skipped 标记）"""
    events = get_interview_events(session_id)
    return {"session_id": session_id, "rounds": events}


@router.get("/compare")
def compare(topic: str, db: Session = Depends(get_db)):
    """同主题场次纵向对比：首场 vs 最近场的每题 final 均分（复测提升口径来源）"""
    sessions = list_interviews_by_topic(db, topic)
    if not sessions:
        return {"topic": topic, "n_sessions": 0, "items": [], "first_vs_latest": None}

    def per_q_final_avg(rec) -> float | None:
        finals = [q["final"] for q in (rec.detail or [])
                  if isinstance(q, dict) and not q.get("skipped") and q.get("final") is not None]
        return round(sum(finals) / len(finals), 2) if finals else None

    items = [{
        "session_id": r.session_id,
        "avg_score": r.avg_score,
        "per_question_final_avg": per_q_final_avg(r),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in sessions]

    first_vs_latest = None
    if len(sessions) >= 2:
        f, l = per_q_final_avg(sessions[0]), per_q_final_avg(sessions[-1])
        if f is not None and l is not None:
            first_vs_latest = {
                "first_session": sessions[0].session_id,
                "latest_session": sessions[-1].session_id,
                "first_final_avg": f,
                "latest_final_avg": l,
                "delta": round(l - f, 2),
            }
    return {"topic": topic, "n_sessions": len(sessions), "items": items,
            "first_vs_latest": first_vs_latest}


@router.get("/records")
def records(db: Session = Depends(get_db)):
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
