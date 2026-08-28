"""面试官 Agent：题单化状态机 + human-in-the-loop（interrupt）

图结构（M2）：
START → ask（取题单题/现场生成/生成追问，不 interrupt）→ wait（独占 interrupt，等用户输入）
      → route_op（op=answer→judge / op=pick、skip→ask）
      → judge（Pydantic 校验评分 + 本题结算）→ 条件边 → ask（追问/下一题）或 END。

关键不变量：
1. interrupt 独占 wait 节点，恢复时只重放 wait（幂等），题目不因重放重复生成；
2. LLM/DB 副作用全在 wait 之前的节点（ask 出题、judge 评分），route_op 纯计算；
3. 深挖上限代码强制（≤2 轮），不信 LLM finished 标志；
4. 题单模式：题尽由 ask 判定 done；非题单模式：round>=max_rounds 兜底。

状态由 SqliteSaver 按 thread_id=session_id 持久化到 SQLite 文件（重启后端可断点续答）；
API 层流程：
  start  → invoke({topic/qlist_id,...})           → 拿到 __interrupt__（第一题）
  answer → invoke(Command(resume={"op":"answer","answer":...}))
  pick   → invoke(Command(resume={"op":"pick","index":n}))
  skip   → invoke(Command(resume={"op":"skip"}))
"""

import re
import sqlite3
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, field_validator

from sqlalchemy import select

from app.agent.llm import call_llm_json, get_chat_model
from app.agent.state import InterviewState
from app.config import config
from app.constants import TOPIC_NAMES
from app.rag.search import search_as_context

_ASK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是资深技术面试官。根据主题和参考题目，出一道新的面试题。"
               "要求：贴合主题、由浅入深、不要重复已出题目（见已出列表）。"
               "只输出题目本身，不要输出答案或其他说明。"),
    ("human", "主题：{topic}\n已出题目：{asked}\n参考题库：\n{reference}"),
])

_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是面试评分专家。评判候选人回答，输出 JSON（不要多余文字）：\n"
               "{{\"score\": 0-10 的浮点数（总分）, \"feedback\": \"具体反馈：优点、不足、参考答案要点\", "
               "\"finished\": true/false（回答质量已充分暴露或轮数足够则 true）, "
               "\"deep_dive\": true/false（回答还有明显深挖空间，值得追问则 true）, "
               "\"dims\": {{\"correctness\": 0-10, \"depth\": 0-10, \"structure\": 0-10, "
               "\"expression\": 0-10, \"risk_awareness\": 0-10}}}}\n"
               "五维指引：correctness 知识点正确性；depth 原理展开深度；structure 表达结构（先结论后展开）；\n"
               "expression 语言准确性与术语运用；risk_awareness 对边界/坑/适用条件的意识。\n"
               "注意：总分 score 必须严格对照下方锚点独立定档，严禁取五维平均；\n"
               "五维只是诊断分解，各维打分尺度与总分锚点一致（如 answer 属 5-6 档，各维也应落在相近区间）。\n"
               "评分锚点（针对总分 score，严格对照，不得整体抬分）：\n"
               "0-2 分：空答/跑题/空话堆砌/答非所问；\n"
               "3-4 分：沾边但回避了题目的核心设问，或仅有名词没有解释；\n"
               "5-6 分：要点齐全但浅尝辄止，缺原理展开或量化细节；\n"
               "7-8 分：原理正确 + 有真实实践细节，能正面回应核心设问；\n"
               "9-10 分：原理+实践+量化结果+边界意识（知道方案的适用边界与坑）。"),
    ("human", "面试题：{question}\n候选人回答：{answer}\n参考要点：\n{reference}"),
])

_DIM_KEYS = ("correctness", "depth", "structure", "expression", "risk_awareness")

_FOLLOWUP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是资深技术面试官。基于面试题和候选人回答，生成一个更深一层的追问。"
               "要求：针对回答中的薄弱点/模糊处/可量化细节追问，不要重复原题，"
               "只输出追问本身。"),
    ("human", "原题：{question}\n候选人回答：{answer}"),
])

_MAX_DEEP_DIVE = 2  # 深挖轮次代码强制上限（不信 LLM finished 标志）


class _JudgeResult(BaseModel):
    """judge 输出的 Pydantic 校验：score 强制 clamp 到 0-10，修 v1 float() 裸转换；
    M5.1 起带五维 dims（逐维 clamp，缺失/非法维度剔除，整体缺失则空 dict）"""

    score: float = 5.0
    feedback: str = ""
    finished: bool = False
    deep_dive: bool = False
    dims: dict[str, float] = {}

    @field_validator("score", mode="before")
    @classmethod
    def _clamp_score(cls, v: Any) -> float:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 5.0
        return max(0.0, min(10.0, f))

    @field_validator("feedback", mode="before")
    @classmethod
    def _str_feedback(cls, v: Any) -> str:
        return str(v or "")

    @field_validator("dims", mode="before")
    @classmethod
    def _clamp_dims(cls, v: Any) -> dict[str, float]:
        if not isinstance(v, dict):
            return {}
        out: dict[str, float] = {}
        for key in _DIM_KEYS:
            try:
                f = float(v.get(key))
            except (TypeError, ValueError):
                continue
            out[key] = max(0.0, min(10.0, f))
        return out


def _stories_context(topic: str) -> str:
    """hr 题型：注入候选人 STAR 故事库摘要，让行为题围绕真实经历出（M5.2）。
    无故事或任何异常 → 空串，静默退回原检索逻辑。"""
    if topic != "hr":
        return ""
    try:
        from app.database import SessionLocal
        from app.models import ExperienceStory
        from app.services.stories import BEHAVIORAL_QUESTIONS

        db = SessionLocal()
        try:
            stories = list(db.scalars(select(ExperienceStory)).all())
        finally:
            db.close()
    except Exception:
        return ""
    if not stories:
        return ""
    qmap = {q["id"]: q["zh"] for q in BEHAVIORAL_QUESTIONS}
    lines = ["【候选人故事库】（优先围绕这些真实经历出题或追问）"]
    for s in stories:
        can = "、".join(qmap.get(i, str(i)) for i in (s.can_answer or []))
        lines.append(
            f"- 《{s.title}》标签：{'、'.join(s.tags or [])}；可答：{can}；"
            f"素材要点：{(s.raw_answer or '')[:120]}"
        )
    return "\n".join(lines)


def _generate_question(topic: str, asked: list[str], round_no: int) -> str:
    topic_name = TOPIC_NAMES.get(topic, topic)
    reference = search_as_context(topic_name, k=4, category="interview")
    if not reference.strip() or reference.strip() == "没有找到相关资料。":
        reference = search_as_context(topic_name, k=4)
    stories_ctx = _stories_context(topic)
    if stories_ctx:
        reference = stories_ctx + "\n\n" + reference
    chain = _ASK_PROMPT | get_chat_model() | StrOutputParser()
    question = chain.invoke({
        "topic": topic_name,
        "asked": "\n".join(asked) if asked else "（无）",
        "reference": reference,
    }).strip()
    # 兜底：LLM 偶尔输出序号或换行
    return re.sub(r"^\d+[.、]\s*", "", question).strip() or f"请介绍与{topic_name}相关的一个知识点"


def _generate_followup(question: str, answer: str) -> str:
    """基于当前题 + 用户回答生成深挖追问"""
    chain = _FOLLOWUP_PROMPT | get_chat_model() | StrOutputParser()
    followup = chain.invoke({"question": question, "answer": answer}).strip()
    return re.sub(r"^\d+[.、]\s*", "", followup).strip() or "可以再具体讲讲吗？"


def _judge_answer(state: InterviewState) -> tuple[_JudgeResult, bool]:
    """评分双保险：call_llm_json（response_format + 正则兜底 + 重试）→ Pydantic clamp；
    重试耗尽 → 兜底 5 分 + degraded=True 显性标记，绝不让面试流程崩在评分上。"""
    # 题单题自带参考要点，优先用，免二次检索
    reference = state.get("current_reference") or search_as_context(
        state["current_question"], k=3, category="interview"
    )
    messages = _JUDGE_PROMPT.format_messages(
        question=state["current_question"],
        answer=state["answer"],
        reference=reference,
    )
    try:
        raw = call_llm_json(messages)
        return _JudgeResult.model_validate(raw), False
    except Exception:
        return _JudgeResult(
            score=5.0,
            feedback="评分服务暂时异常，本题按 5 分兜底记录，建议结合回答内容人工复核。",
        ), True


def _ask_node(state: InterviewState) -> dict[str, Any]:
    """只生成题目/追问写入 state，不 interrupt（重放安全）"""
    if state.get("need_deep_dive"):
        # 生成追问：题序号不变（归属母题），深挖轮次 +1
        followup = _generate_followup(state["current_question"], state["answer"])
        return {
            "deep_dive_round": state.get("deep_dive_round", 0) + 1,
            "current_question": followup,
            "current_reference": "",  # 追问无题单参考，judge 回退检索
            "asked": state["asked"] + [followup],
            "waiting_for": "followup",
            "need_deep_dive": False,
        }
    # 题单模式：从快照取题；题尽 → done（条件边去 END）
    questions = state.get("questions") or []
    if state.get("qlist_id"):
        if state["q_idx"] >= len(questions):
            return {"done": True}
        item = questions[state["q_idx"]]
        question = str(item.get("question", "")).strip() or "请做一个自我介绍。"
        return {
            "round": state["round"] + 1,
            "q_idx": state["q_idx"] + 1,
            "deep_dive_round": 0,
            "base_question": question,
            "current_question": question,
            "current_reference": str(item.get("reference", "") or ""),
            "asked": state["asked"] + [question],
            "waiting_for": "answer",
            "need_deep_dive": False,
            "cur_first_score": -1.0,
            "cur_followup_scores": [],
            "cur_first_dims": {},
            "done": False,
        }
    # 非题单模式：现场生成（v2 行为，round 上限在 judge 兜底）
    question = _generate_question(state["topic"], state["asked"], state["round"] + 1)
    return {
        "round": state["round"] + 1,
        "deep_dive_round": 0,
        "base_question": question,
        "current_question": question,
        "current_reference": "",
        "asked": state["asked"] + [question],
        "waiting_for": "answer",
        "need_deep_dive": False,
        "cur_first_score": -1.0,
        "cur_followup_scores": [],
        "cur_first_dims": {},
        "done": False,
    }


def _wait_node(state: InterviewState) -> dict[str, Any]:
    """独占 interrupt：唯一等待用户输入的点（恢复时只重放本节点，幂等）

    resume 负载统一为 op 协议：{"op":"answer","answer":...} / {"op":"pick","index":n}
    / {"op":"skip"}；兼容裸字符串（视为 answer）。
    """
    payload: dict[str, Any] = {
        "type": "followup" if state.get("waiting_for") == "followup" else "question",
        "round": state["round"],
        "deep_dive_round": state.get("deep_dive_round", 0),
        "question": state["current_question"],
    }
    if state.get("qlist_id"):
        # 题单进度供前端渲染题目选择器（自由挑题）
        payload["progress"] = {
            "consumed": state["q_idx"],
            "total": len(state.get("questions") or []),
        }
    resume = interrupt(payload)
    if isinstance(resume, dict):
        return {
            "op": str(resume.get("op", "answer")),
            "answer": str(resume.get("answer", "")),
            "pick_index": int(resume.get("index", 0) or 0),
        }
    return {"op": "answer", "answer": str(resume), "pick_index": 0}


def _route_op_node(state: InterviewState) -> dict[str, Any]:
    """op 分发（纯计算，无 LLM/DB 副作用）：answer→judge；pick→改游标去 ask；
    skip→记 skipped 去 ask；end→直达 END。
    end 结算语义（Codex 裁决 2026-08-29）：有首答按首答结算（final=首答），无首答作废。"""
    op = state.get("op", "answer")
    if op == "end":
        updates: dict[str, Any] = {"done": True, "need_deep_dive": False}
        if state.get("cur_first_score", -1.0) >= 0:
            updates["q_scores"] = state.get("q_scores", []) + [{
                "round": state["round"],
                "question": state.get("base_question") or state["current_question"],
                "first": state["cur_first_score"],
                "followups": list(state.get("cur_followup_scores") or []),
                "final": state["cur_first_score"],
                "dims": state.get("cur_first_dims") or {},
            }]
        return updates
    if op == "pick":
        questions = state.get("questions") or []
        if not questions:  # 非题单模式无题可挑，等同 skip 当前题
            return {
                "need_deep_dive": False,
                "q_scores": state.get("q_scores", []) + [{
                    "round": state["round"],
                    "question": state.get("base_question") or state["current_question"],
                    "skipped": True,
                }],
            }
        idx = max(0, min(int(state.get("pick_index", 0)), len(questions) - 1))
        return {"q_idx": idx, "need_deep_dive": False}
    if op == "skip":
        return {
            "need_deep_dive": False,
            "q_scores": state.get("q_scores", []) + [{
                "round": state["round"],
                "question": state.get("base_question") or state["current_question"],
                "skipped": True,
            }],
        }
    return {}


def _route_op_edge(state: InterviewState) -> str:
    op = state.get("op", "answer")
    if op == "end":
        return END
    return "judge" if op == "answer" else "ask"


def _judge_node(state: InterviewState) -> dict[str, Any]:
    result, degraded = _judge_answer(state)
    is_first = state.get("waiting_for") != "followup"
    first = result.score if is_first else state.get("cur_first_score", -1.0)
    first_dims = result.dims if is_first else state.get("cur_first_dims", {})
    followups = list(state.get("cur_followup_scores") or [])
    if not is_first:
        followups.append(result.score)

    updates: dict[str, Any] = {
        "scores": state["scores"] + [result.score],
        "last_feedback": result.feedback,
        "judge_degraded": degraded,
        "cur_first_score": first,
        "cur_followup_scores": followups,
        "last_dims": result.dims,
        "cur_first_dims": first_dims,
    }

    # 深挖：LLM 建议 + 未达代码上限 + 未自报完成
    if result.deep_dive and state.get("deep_dive_round", 0) < _MAX_DEEP_DIVE and not result.finished:
        updates["need_deep_dive"] = True
        updates["done"] = False
        return updates

    # 本题结算：final = 首答 50% + 追问均分 50%（无追问则 final=首答）
    # dims 取首答五维入账（追问五维已随各轮事件入 Redis，不进结算条目）
    base = first if first >= 0 else result.score
    final = round(base * 0.5 + (sum(followups) / len(followups)) * 0.5, 2) if followups else base
    updates["q_scores"] = state.get("q_scores", []) + [{
        "round": state["round"],
        "question": state.get("base_question") or state["current_question"],
        "first": base,
        "followups": followups,
        "final": final,
        "dims": first_dims,
    }]
    updates["need_deep_dive"] = False
    if state.get("qlist_id"):
        updates["done"] = False  # 题单模式：题尽由 ask 判定
    else:
        updates["done"] = bool(result.finished) or state["round"] >= config.interview_max_rounds
    return updates


def _after_ask(state: InterviewState) -> str:
    """ask 判定题单用尽（done=True）→ END，否则去 wait 等用户"""
    return END if state.get("done") else "wait"


def _route(state: InterviewState) -> str:
    return END if state["done"] else "ask"


_workflow = StateGraph(InterviewState)
_workflow.add_node("ask", _ask_node)
_workflow.add_node("wait", _wait_node)
_workflow.add_node("route_op", _route_op_node)
_workflow.add_node("judge", _judge_node)
_workflow.add_edge(START, "ask")
_workflow.add_conditional_edges("ask", _after_ask, {"wait": "wait", END: END})
_workflow.add_edge("wait", "route_op")
_workflow.add_conditional_edges("route_op", _route_op_edge, {"judge": "judge", "ask": "ask", END: END})
_workflow.add_conditional_edges("judge", _route, {"ask": "ask", END: END})


def _make_checkpointer() -> SqliteSaver:
    """同步 SqliteSaver：面试图状态落 SQLite 文件，进程重启后可按 session_id 恢复"""
    db_path = config.interview_checkpoint_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()  # 幂等建表（CREATE TABLE IF NOT EXISTS）
    return saver


interview_checkpointer = _make_checkpointer()
interview_graph = _workflow.compile(checkpointer=interview_checkpointer)


def extract_interrupt(result: dict) -> dict | None:
    """从图运行结果中提取 interrupt 负载（题目）"""
    interrupts = result.get("__interrupt__") or []
    if interrupts:
        return interrupts[0].value
    return None


def graph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}
