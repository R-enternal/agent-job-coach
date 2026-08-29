import { useEffect, useRef, useState } from "react";
import { Plus, Trash2, Send } from "lucide-react";
import { chatStream, deleteChatSession, getChatHistory, listSessions } from "../api";
import { ChatMessage, Session } from "../lib/types";
import { Button, Empty, Tag } from "../components/ui";
import VoiceInput from "../components/VoiceInput";

const SESSION_KEY = "ajc_active_chat_session";

export default function Chat() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY) || `chat-${Date.now()}`);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const scrollBottom = () => {
    requestAnimationFrame(() => {
      if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
    });
  };

  const reloadSessions = () => listSessions().then((r) => setSessions(r.data.items || [])).catch(() => {});

  const loadHistory = async (sid: string) => {
    try {
      const r = await getChatHistory(sid);
      setMessages(
        (r.data.messages || []).map((m: any) => ({
          role: m.role === "assistant" ? "ai" : "user",
          content: m.content || "",
          tools: m.tools || [],
        }))
      );
    } catch {
      setMessages([]);
    }
    scrollBottom();
  };

  const switchSession = (sid: string) => {
    setSessionId(sid);
    localStorage.setItem(SESSION_KEY, sid);
    loadHistory(sid);
  };

  const newSession = () => {
    const sid = `chat-${Date.now()}`;
    setSessionId(sid);
    localStorage.setItem(SESSION_KEY, sid);
    setMessages([]);
  };

  const removeSession = async () => {
    if (!confirm("删除当前会话？历史记录不可恢复。")) return;
    await deleteChatSession(sessionId);
    setSessions((s) => s.filter((x) => x.session_id !== sessionId));
    newSession();
    reloadSessions();
  };

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    const ai: ChatMessage = { role: "ai", content: "", tools: [] };
    setMessages((m) => [...m, { role: "user", content: q }, ai]);
    setLoading(true);
    scrollBottom();
    try {
      await chatStream(q, sessionId, (event, data) => {
        if (event === "tool_call") {
          ai.tools = ai.tools || [];
          if (!ai.tools.includes(data.data)) ai.tools.push(data.data);
        } else if (event === "content") {
          ai.content += data.data;
        } else if (event === "error") {
          ai.content = "出错了：" + data.data;
        }
        setMessages((m) => [...m]);
        scrollBottom();
      });
    } catch (e: any) {
      ai.content = "请求失败：" + e.message;
      setMessages((m) => [...m]);
    }
    setLoading(false);
    reloadSessions();
  };

  useEffect(() => {
    reloadSessions().then(() => {
      if (sessions.some((s) => s.session_id === sessionId)) loadHistory(sessionId);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full gap-5 p-6">
      <aside className="flex w-64 shrink-0 flex-col rounded-2xl border border-slate-200/70 bg-white p-3 shadow-[0_1px_3px_rgba(15,23,42,0.05)]">
        <div className="mb-2 flex items-center justify-between px-1.5 pt-1">
          <span className="text-[13px] font-semibold text-slate-700">会话</span>
          <button onClick={newSession} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600" title="新建会话">
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => switchSession(s.session_id)}
              className={`w-full rounded-xl px-3 py-2.5 text-left transition ${
                s.session_id === sessionId ? "bg-brand-50" : "hover:bg-slate-50"
              }`}
            >
              <p className="truncate text-[13px] text-slate-700">{s.preview || "新会话"}</p>
              <p className="mt-0.5 text-xs text-slate-400">{s.message_count} 条</p>
            </button>
          ))}
          {sessions.length === 0 && <Empty text="暂无会话" />}
        </div>
        <Button variant="danger" size="sm" onClick={removeSession} className="mt-2 w-full">
          <Trash2 className="h-3.5 w-3.5" /> 删除当前会话
        </Button>
      </aside>

      <div className="flex flex-1 flex-col rounded-2xl border border-slate-200/70 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.05)]">
        <div ref={boxRef} className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-slate-400">
              <p className="text-sm">问我求职相关问题，试试下方示例</p>
              <div className="flex flex-wrap justify-center gap-2">
                {["什么是 LangGraph 状态图？", "RAG 为什么用 RRF 融合？", "仓维云项目有什么亮点？"].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="rounded-full border border-slate-200 px-3.5 py-1.5 text-xs text-slate-500 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-600"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
              }`}>
                {m.tools && m.tools.length > 0 && (
                  <div className="mb-1.5 flex flex-wrap gap-1">
                    {m.tools.map((t) => <Tag key={t} color="blue">🔧 {t}</Tag>)}
                  </div>
                )}
                <p className="whitespace-pre-wrap">{m.content || (loading && m.role === "ai" ? "思考中…" : "")}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 border-t border-slate-100 p-3.5">
          <VoiceInput onText={(t) => setInput((v) => (v ? v.replace(/\s+$/, "") + " " + t : t))} />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
            placeholder="输入你的求职问题，Enter 发送…"
            className="h-10 flex-1 rounded-xl border border-slate-200 px-3.5 text-sm outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50"
          />
          <Button onClick={send} disabled={loading || !input.trim()} className="w-10 px-0">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
