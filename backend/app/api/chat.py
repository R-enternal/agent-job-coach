"""对话 API：SSE 流式（对标仓维云 /api/agent/chat_stream 事件流）"""

import json
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.agent.qa_agent import _init_state, qa_graph, sanitize_messages
from app.schemas import ChatRequest
from app.services.memory import save_history

router = APIRouter(prefix="/api/agent", tags=["对话"])


def _collect_messages(session_id: str) -> list[dict]:
    """从 checkpointer 收集当前会话消息（不含系统消息、空内容）"""
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}
    try:
        checkpoint_tuple = qa_graph.checkpointer.get_tuple(config)
        if checkpoint_tuple is None:
            return []
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", []) or []
        history: list[dict] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                continue
            if isinstance(msg, (HumanMessage, AIMessage)):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if not content.strip():
                    continue
                item: dict = {
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                    "content": content,
                }
                tool_calls = getattr(msg, "tool_calls", None) or []
                if tool_calls:
                    item["tools"] = [tc.get("name", "") for tc in tool_calls]
                history.append(item)
        return history
    except Exception:
        return []


async def _emit_updates(payload: dict) -> AsyncGenerator[dict, None]:
    """updates 模式：节点级事件（工具调用、工具结果）"""
    for _node_name, output in payload.items():
        output = output or {}
        for message in output.get("messages", []) or []:
            if isinstance(message, AIMessage):
                for call in getattr(message, "tool_calls", []) or []:
                    yield {"type": "tool_call", "data": call.get("name", "")}
            elif isinstance(message, BaseMessage) and getattr(message, "type", "") == "tool":
                yield {
                    "type": "tool_result",
                    "data": str(message.content)[:500],
                    "tool": message.name or "",
                }


async def _chat_events(question: str, session_id: str) -> AsyncGenerator[dict, None]:
    """遍历 LangGraph 事件：messages 出 token、updates 出工具事件"""
    graph_config: RunnableConfig = {"configurable": {"thread_id": session_id}}
    try:
        async for event in qa_graph.astream(
            _init_state(question),
            config=graph_config,
            stream_mode=["updates", "messages"],
        ):
            if not isinstance(event, tuple) or len(event) != 2:
                continue
            mode, payload = event
            if mode == "messages" and isinstance(payload, tuple) and len(payload) == 2:
                chunk, _metadata = payload
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield {"type": "content", "data": str(chunk.content)}
            elif mode == "updates" and isinstance(payload, dict):
                async for ev in _emit_updates(payload):
                    yield ev
        save_history(session_id, _collect_messages(session_id))
        yield {"type": "complete"}
    except Exception as exc:
        yield {"type": "error", "data": str(exc)}


@router.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    async def gen():
        async for ev in _chat_events(req.question, req.session_id):
            # sse-starlette 要求 event / data 两个字段
            yield {
                "event": ev.get("type", "message"),
                "data": json.dumps(ev, ensure_ascii=False),
            }

    return EventSourceResponse(gen())


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    """非流式对话：拼装最终回答"""
    answer_parts: list[str] = []
    async for ev in _chat_events(req.question, req.session_id):
        if ev["type"] == "content":
            answer_parts.append(str(ev["data"]))
        elif ev["type"] == "error":
            return {"answer": f"出错了：{ev['data']}"}
    return {"answer": "".join(answer_parts) if answer_parts else "（暂无回答，请换个问法）"}
