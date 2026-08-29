import axios from "axios";

export const api = axios.create({ baseURL: "/api", timeout: 180000 });

// ---------- SSE 流式对话 ----------
export async function chatStream(
  question: string,
  sessionId: string,
  onEvent: (event: string, data: any) => void
) {
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

// ---------- 会话 ----------
export const listSessions = () => api.get("/agent/sessions");
export const getChatHistory = (sessionId: string) =>
  api.get("/agent/history", { params: { session_id: sessionId } });
export const deleteChatSession = (sessionId: string) =>
  api.delete(`/agent/sessions/${encodeURIComponent(sessionId)}`);

// ---------- 简历底稿（题单生成的素材来源） ----------
export const upsertResume = (raw_text: string) => api.post("/assets/resume", { raw_text });
export const getResume = () => api.get("/assets/resume");

// ---------- 知识库（资料库） ----------
export const kbUpload = (file: File, category: string) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/kb/upload", fd, {
    params: { category },
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const kbDocuments = () => api.get("/kb/documents");
export const kbDeleteDocument = (source: string) =>
  api.delete("/kb/documents", { params: { source } });
export const kbSearch = (q: string, category = "") =>
  api.get("/kb/search", { params: { q, category } });
export const kbCategories = () => api.get("/kb/categories");

// ---------- JD / 题单 ----------
export const parseJdText = (raw_text: string) => api.post("/jd/parse", { raw_text });
export const parseJdImage = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/jd/parse_image", fd, { headers: { "Content-Type": "multipart/form-data" } });
};
export const listJds = () => api.get("/jd");
export const updateJd = (id: number, data: any) => api.put(`/jd/${id}`, data);
export const generateQlist = (jd_id: number | null, quota?: Record<string, number>) =>
  api.post("/qlist/generate", { jd_id, quota });
export const listQlists = () => api.get("/qlist");
export const getQlist = (id: number) => api.get(`/qlist/${id}`);

// ---------- 面试 ----------
export const startInterview = (payload: any) => api.post("/interview/start", payload);
export const answerInterview = (session_id: string, answer: string) =>
  api.post("/interview/answer", { session_id, answer });
export const pickQuestion = (session_id: string, index: number) =>
  api.post("/interview/pick", { session_id, index });
export const skipQuestion = (session_id: string) => api.post("/interview/skip", { session_id });
export const endInterview = (session_id: string) => api.post("/interview/end", { session_id });
export const getInterviewState = (session_id: string) =>
  api.get("/interview/state", { params: { session_id } });
export const getInterviewRecords = () => api.get("/interview/records");
export const getCompare = (topic: string) => api.get("/interview/compare", { params: { topic } });
export const polishAnswer = (question: string, answer: string) =>
  api.post("/answers/polish", { question, answer });

export default api;
