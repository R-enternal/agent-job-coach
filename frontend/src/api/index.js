import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 180000,
});

/** POST SSE 流式对话：回调事件 */
export async function chatStream(question, sessionId, onEvent) {
  const resp = await fetch("/api/agent/chat_stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!resp.ok || !resp.body) throw new Error("SSE 连接失败");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // 按空行切分 SSE 事件
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) {
        try {
          onEvent(event, JSON.parse(data));
        } catch {
          onEvent(event, { type: "content", data });
        }
      }
    }
  }
}

export default api;
