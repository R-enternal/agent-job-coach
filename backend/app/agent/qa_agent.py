"""知识问答 Agent：LangGraph ReAct 图（agent → tools 条件循环，步数上限 6）

参考仓维云 chat_agent.py：
- 节点 agent：LLM 决定调用哪些工具
- 节点 tools：执行工具，结果回填
- 条件边：还有 tool_calls 且未达步数上限就继续，否则结束
- MemorySaver 按 session_id 保存多轮会话
- 孤儿 tool_calls 自愈清洗（_sanitize_messages）
"""

from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.llm import get_chat_model
from app.agent.state import QaState
from app.config import config
from app.tools import ALL_TOOLS

SYSTEM_PROMPT = """你是 Agent Job Coach（Agent 求职助手），帮助求职者准备面试、整理知识点、诊断 JD 匹配度。

工作原则：
1. 根据用户问题选择合适的工具：知识问答用 query_knowledge，JD 匹配用 match_job，
   知识点整理用 gen_study_notes，项目深挖用 dig_project，项目介绍话术用 project_intro
2. 工具返回结果后，用简洁清晰的中文总结，保留关键细节和引用来源
3. 用户问题与求职无关时，礼貌说明你能做什么
4. 不编造简历/项目里没有的内容"""


def _tool_call_ids(msg: BaseMessage) -> set[str]:
    return {str(call.get("id", "")) for call in getattr(msg, "tool_calls", []) or [] if call.get("id")}


def sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """孤儿 tool_calls 自愈：保证 tool_calls 与 ToolMessage 严格配对，避免 LLM API 400"""
    system: SystemMessage | None = None
    body: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            if system is None:
                system = msg
            continue
        body.append(msg)

    cleaned: list[BaseMessage] = []
    for idx, msg in enumerate(body):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            later_ids = {
                tm.tool_call_id
                for tm in body[idx + 1 :]
                if isinstance(tm, ToolMessage) and tm.tool_call_id
            }
            call_ids = _tool_call_ids(msg)
            missing = call_ids - later_ids
            if missing:
                content = msg.content if isinstance(msg.content, str) else ""
                cleaned.append(AIMessage(content=content))
            else:
                cleaned.append(msg)
        elif isinstance(msg, ToolMessage):
            matched = msg.tool_call_id and any(
                msg.tool_call_id in _tool_call_ids(pm)
                for pm in body[:idx]
                if isinstance(pm, AIMessage)
            )
            if matched:
                cleaned.append(msg)
        else:
            cleaned.append(msg)

    cleaned = [
        msg
        for msg in cleaned
        if not (
            isinstance(msg, AIMessage)
            and not getattr(msg, "tool_calls", None)
            and not str(msg.content or "").strip()
        )
    ]
    if system is not None:
        cleaned.insert(0, system)
    return cleaned


def _init_state(question: str) -> dict[str, Any]:
    return {
        "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)],
        "step_count": 0,
    }


async def _agent_node(state: QaState) -> dict[str, Any]:
    llm = get_chat_model().bind_tools(ALL_TOOLS)
    response = await llm.ainvoke(sanitize_messages(list(state["messages"])))
    return {"messages": [response], "step_count": state["step_count"] + 1}


def _should_continue(state: QaState) -> str:
    last = state["messages"][-1]
    if state["step_count"] >= config.agent_max_steps:
        return END
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


async def _tools_node(state: QaState) -> dict[str, Any]:
    last = state["messages"][-1]
    tool_map = {t.name: t for t in ALL_TOOLS}
    tool_messages: list[ToolMessage] = []
    for call in getattr(last, "tool_calls", []) or []:
        tool = tool_map.get(call.get("name", ""))
        if tool is None:
            content = f"未找到工具: {call.get('name')}"
        else:
            try:
                content = str(await tool.ainvoke(call.get("args", {})))
            except Exception as exc:
                content = f"工具调用失败: {exc}"
        tool_messages.append(
            ToolMessage(
                content=content,
                tool_call_id=call.get("id") or "",
                name=call.get("name", ""),
            )
        )
    return {"messages": tool_messages}


_workflow = StateGraph(QaState)
_workflow.add_node("agent", _agent_node)
_workflow.add_node("tools", _tools_node)
_workflow.add_edge(START, "agent")
_workflow.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
_workflow.add_edge("tools", "agent")

qa_graph = _workflow.compile(checkpointer=MemorySaver())
