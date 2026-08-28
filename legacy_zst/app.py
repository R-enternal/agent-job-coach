import time
import json

from Agent.ReAct import ReActAgent
from Models.Factory import ChatModelFactory
from Tools.Tools import *
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from flask import Flask, request, jsonify, Response
import re

app = Flask(__name__)

# 按 uuid 缓存会话历史（对标仓维云 MemorySaver + thread_id；生产可换 Redis 持久化）
_histories: dict[int, ChatMessageHistory] = {}


def _get_history(uuid: int) -> ChatMessageHistory:
    """按用户 uuid 隔离会话记忆：同一用户连续提问可引用上文"""
    if uuid not in _histories:
        _histories[uuid] = ChatMessageHistory()
    return _histories[uuid]


def launch_agent(query, agent, uuid=1001):
    chat_history = _get_history(uuid)
    reply = agent.execute(query, uuid, chat_history=chat_history, verbose=True)
    return reply


@app.route("/predict", methods=["POST"])
def main():
    try:
        data = request.get_json()
        query = data.get("query", "")
        uuid = data.get('uuid', 1001)
        if not query:
            return jsonify({"error": "请输入文本"}), 400
        llm = ChatModelFactory().get_model()

        tools = [
            rag_qa_tool,
            report_generation_tool,
        ]

        agent = ReActAgent(
            llm=llm,
            tools=tools,
            main_prompt_file_path="prompts/main.txt"
        )

        response = launch_agent(query, agent, uuid)

        if '<think>' in response and "</think>" in response:
            answer = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        elif '<think>' in response and "</think>\n\n答：" in response:
            answer = re.sub(r"<think>.*?</think>\n\n答：", "", response, flags=re.DOTALL)
        else:
            answer = response
        print(f'answer:{answer}')
        print('-----------------------------------------------------------------------')
        return jsonify({"answer": answer}), 200
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@app.route("/predict_stream", methods=["POST"])
def predict_stream():
    """SSE 流式接口（对标仓维云 /api/agent/chat_stream 事件流）：
    tool_call → tool_result → content(最终答案) → complete
    """
    try:
        data = request.get_json()
        query = data.get("query", "")
        uuid = data.get('uuid', 1001)
        if not query:
            return jsonify({"error": "请输入文本"}), 400

        def generate():
            llm = ChatModelFactory().get_model()
            tools = [
                rag_qa_tool,
                report_generation_tool,
            ]
            agent = ReActAgent(
                llm=llm,
                tools=tools,
                main_prompt_file_path="prompts/main.txt",
            )
            history = _get_history(uuid)
            for event, payload in agent.execute_stream(query, uuid, history, verbose=False):
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
