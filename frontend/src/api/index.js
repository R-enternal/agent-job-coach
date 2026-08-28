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

// ---------- 素材库 ----------
export const upsertResume = (rawText, version = "default") =>
  api.post("/assets/resume", { raw_text: rawText, version });
export const getResume = (version = "default") =>
  api.get("/assets/resume", { params: { version } });
export const listProjects = () => api.get("/assets/projects");
export const createProject = (data) => api.post("/assets/projects", data);
export const updateProject = (id, data) => api.put(`/assets/projects/${id}`, data);
export const deleteProject = (id) => api.delete(`/assets/projects/${id}`);
export const extractProjectDraft = () => api.post("/assets/projects/extract");

// ---------- JD 定制 ----------
export const parseJdText = (rawText) => api.post("/jd/parse", { raw_text: rawText });
export const parseJdImage = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/jd/parse_image", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const listJds = (status = "") => api.get("/jd", { params: { status } });
export const updateJd = (id, data) => api.put(`/jd/${id}`, data);

// ---------- 题单 ----------
export const generateQlist = (jdId = null) =>
  api.post("/qlist/generate", { jd_id: jdId });
export const listQlists = () => api.get("/qlist");
export const getQlist = (id) => api.get(`/qlist/${id}`);

// ---------- 面试 ----------
export const startInterview = (payload) => api.post("/interview/start", payload);
export const answerInterview = (sessionId, answer) =>
  api.post("/interview/answer", { session_id: sessionId, answer });
export const pickQuestion = (sessionId, index) =>
  api.post("/interview/pick", { session_id: sessionId, index });
export const skipQuestion = (sessionId) =>
  api.post("/interview/skip", { session_id: sessionId });
export const endInterview = (sessionId) =>
  api.post("/interview/end", { session_id: sessionId });
export const getRecords = () => api.get("/interview/records");
export const getCompare = (topic) =>
  api.get("/interview/compare", { params: { topic } });

// ---------- STAR 经历故事 ----------
export const listStories = () => api.get("/stories");
export const generateStory = (question, rawAnswer) =>
  api.post("/stories", { question, raw_answer: rawAnswer });
export const deleteStory = (id) => api.delete(`/stories/${id}`);
export const getStoryQuestions = () => api.get("/stories/questions");

// ---------- 答案打磨 ----------
export const polishAnswer = (question, answer, storyId = null) =>
  api.post("/answers/polish", { question, answer, story_id: storyId });

export default api;
