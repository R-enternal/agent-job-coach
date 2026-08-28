"""面试官 Agent：LangGraph 状态机 + human-in-the-loop（interrupt）

图结构（v2，修复 v1 interrupt 重放 bug）：
START → ask（只生成题目/追问，不 interrupt）→ wait（独占 interrupt，等用户输入）
      → judge（评分/反馈/决定深挖或结束）→ 条件边 → ask（追问/下一题）或 END。

关键：interrupt 独占 wait 节点，LangGraph 恢复时只重放 wait（幂等），
题目不会因重放而重复生成。

状态由 checkpointer 按 thread_id=session_id 持久化；
API 层流程：
  start  → invoke({topic,...})  → 拿到 __interrupt__（第一题）
  answer → invoke(Command(resume=回答)) → 拿到评分/反馈 + 下一题（或最终结果）
"""

import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agent.llm import call_llm_json, get_chat_model
from app.agent.state import InterviewState
from app.config import config
from app.rag.search import search_as_context

_TOPIC_NAMES = {
    "agent": "Agent 原理与工程化",
    "rag": "RAG 专项",
    "project": "项目深挖",
    "eight-part": "八股基础",
    "hr": "主管/HR 面",
    "mixed": "综合混面",
}

_ASK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是资深技术面试官。根据主题和参考题目，出一道新的面试题。"
               "要求：贴合主题、由浅入深、不要重复已出题目（见已出列表）。"
               "只输出题目本身，不要输出答案或其他说明。"),
    ("human", "主题：{topic}\n已出题目：{asked}\n参考题库：\n{reference}"),
])

_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是面试评分专家。评判候选人回答，输出 JSON（不要多余文字）：\n"
               "{{\"score\": 0-10 的浮点数, \"feedback\": \"具体反馈：优点、不足、参考答案要点\", "
               "\"finished\": true/false（回答质量已充分暴露或轮数足够则 true）, "
               "\"deep_dive\": true/false（回答还有明显深挖空间，值得追问则 true）}}"),
    ("human", "面试题：{question}\n候选人回答：{answer}\n参考要点：\n{reference}"),
])

_FOLLOWUP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是资深技术面试官。基于面试题和候选人回答，生成一个更深一层的追问。"
               "要求：针对回答中的薄弱点/模糊处/可量化细节追问，不要重复原题，"
               "只输出追问本身。"),
    ("human", "原题：{question}\n候选人回答：{answer}"),
])


def _generate_question(topic: str, asked: list[str], round_no: int) -> str:
    topic_name = _TOPIC_NAMES.get(topic, topic)
    reference = search_as_context(topic_name, k=4, category="interview")
    if not reference.strip() or reference.strip() == "没有找到相关资料。":
        reference = search_as_context(topic_name, k=4)
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


def _judge_answer(state: InterviewState) -> dict[str, Any]:
    reference = search_as_context(state["current_question"], k=3, category="interview")
    messages = _JUDGE_PROMPT.format_messages(
        question=state["current_question"],
        answer=state["answer"],
        reference=reference,
    )
    result = call_llm_json(messages)
    return {
        "score": float(result.get("score", 5.0)),
        "feedback": str(result.get("feedback", "")),
        "finished": bool(result.get("finished", False)),
        "deep_dive": bool(result.get("deep_dive", False)),
    }


def _ask_node(state: InterviewState) -> dict[str, Any]:
    """只生成题目/追问写入 state，不 interrupt（重放安全）"""
    if state.get("need_deep_dive"):
        # 生成追问：题序号不变，深挖轮次 +1
        followup = _generate_followup(state["current_question"], state["answer"])
        return {
            "round": state["round"],
            "deep_dive_round": state.get("deep_dive_round", 0) + 1,
            "current_question": followup,
            "asked": state["asked"] + [followup],
            "waiting_for": "followup",
            "need_deep_dive": False,
        }
    # 生成新题：题序号 +1，深挖轮次归零
    round_no = state["round"] + 1
    question = _generate_question(state["topic"], state["asked"], round_no)
    return {
        "round": round_no,
        "deep_dive_round": 0,
        "current_question": question,
        "asked": state["asked"] + [question],
        "waiting_for": "answer",
        "need_deep_dive": False,
    }


def _wait_node(state: InterviewState) -> dict[str, Any]:
    """独占 interrupt：唯一等待用户输入的点（恢复时只重放本节点，幂等）"""
    if state.get("waiting_for") == "followup":
        answer = interrupt({
            "type": "followup",
            "round": state["round"],
            "deep_dive_round": state.get("deep_dive_round", 0),
            "question": state["current_question"],
        })
    else:
        answer = interrupt({
            "type": "question",
            "round": state["round"],
            "question": state["current_question"],
        })
    return {"answer": str(answer)}


def _judge_node(state: InterviewState) -> dict[str, Any]:
    result = _judge_answer(state)
    deep_dive_round = state.get("deep_dive_round", 0)
    if (
        result.get("deep_dive")
        and deep_dive_round < 2
        and not result.get("finished")
    ):
        # 值得深挖且未达上限：去 ask 生成追问
        need_deep_dive = True
        done = False
    elif result.get("finished") or state["round"] >= config.interview_max_rounds:
        need_deep_dive = False
        done = True
    else:
        # 本题结束，出下一题
        need_deep_dive = False
        done = False
    return {
        "scores": state["scores"] + [result["score"]],
        "last_feedback": result["feedback"],
        "need_deep_dive": need_deep_dive,
        "done": done,
    }


def _route(state: InterviewState) -> str:
    return END if state["done"] else "ask"


_workflow = StateGraph(InterviewState)
_workflow.add_node("ask", _ask_node)
_workflow.add_node("wait", _wait_node)
_workflow.add_node("judge", _judge_node)
_workflow.add_edge(START, "ask")
_workflow.add_edge("ask", "wait")
_workflow.add_edge("wait", "judge")
_workflow.add_conditional_edges("judge", _route, {"ask": "ask", END: END})

interview_graph = _workflow.compile(checkpointer=MemorySaver())


def extract_interrupt(result: dict) -> dict | None:
    """从图运行结果中提取 interrupt 负载（题目）"""
    interrupts = result.get("__interrupt__") or []
    if interrupts:
        return interrupts[0].value
    return None


def graph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}
