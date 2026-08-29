import { useEffect, useRef, useState } from "react";
import {
  BriefcaseBusiness, Check, CheckCircle2, History, ImageUp, Mic2, Play,
  RotateCcw, Send, SkipForward, Sparkles, StopCircle, Wand2,
} from "lucide-react";
import {
  answerInterview, endInterview, generateQlist, getInterviewRecords, getInterviewState,
  getQlist, listJds, parseJdImage, parseJdText, pickQuestion, polishAnswer,
  skipQuestion, startInterview, updateJd,
} from "../api";
import { InterviewRecord, Jd, Qlist, QLIST_QUOTA, QTYPE_NAMES, TOPIC_NAMES } from "../lib/types";
import { Button, Input, Modal, Select, Tag, Textarea } from "../components/ui";
import ScoreDims from "../components/ScoreDims";
import VoiceInput from "../components/VoiceInput";

const SAVED_KEY = "ajc_active_interview";
const QTYPE_COLORS: Record<string, string> = { "eight-part": "blue", project: "green", business: "violet" };

/* 对话流消息：问题 / 回答 / 评分卡 / 系统提示 / 复盘报告 */
type Msg =
  | { kind: "q"; round: number; text: string; qtype?: string; followup?: boolean }
  | { kind: "a"; text: string }
  | { kind: "s"; score?: number; dims?: Record<string, number> | null; qScore?: number | null; feedback: string; degraded?: boolean; question: string; answer: string }
  | { kind: "sys"; text: string }
  | { kind: "report"; text: string };

interface SessionMeta { id: string; topicName: string; qlistId: number }

export default function Interview() {
  /* ---------- 左栏：设置 ---------- */
  const [jds, setJds] = useState<Jd[]>([]);
  const [jdText, setJdText] = useState("");
  const [editing, setEditing] = useState<Jd | null>(null);
  const [selectedId, setSelectedId] = useState(""); // "" 未选 / "generic" 通用 / 其余为 JD id
  const [qlist, setQlist] = useState<Qlist | null>(null);
  const [records, setRecords] = useState<InterviewRecord[]>([]);

  /* ---------- 右栏：对话 ---------- */
  const [session, setSession] = useState<SessionMeta | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);
  const [qstatus, setQstatus] = useState<Record<number, "answered" | "skipped">>({});
  const [progress, setProgress] = useState<{ consumed: number; total: number } | null>(null);
  const [saved, setSaved] = useState<any>(null);
  const [polish, setPolish] = useState<any>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const scrollBottom = () =>
    requestAnimationFrame(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; });

  const loadRecords = () => getInterviewRecords().then((r) => setRecords(r.data || [])).catch(() => {});
  const reloadJds = () => listJds().then((r) => setJds(r.data.items || [])).catch(() => {});

  const checkSaved = async () => {
    const raw = localStorage.getItem(SAVED_KEY);
    if (!raw) return;
    try {
      const m = JSON.parse(raw);
      const r = await getInterviewState(m.session_id);
      if (r.data.resumable) setSaved({ ...m, ...r.data });
      else localStorage.removeItem(SAVED_KEY);
    } catch { localStorage.removeItem(SAVED_KEY); }
  };

  useEffect(() => { reloadJds(); loadRecords(); checkSaved(); }, []);
  useEffect(() => { scrollBottom(); }, [msgs]);

  const push = (...m: Msg[]) => setMsgs((prev) => [...prev, ...m]);
  const qtypeOf = (text: string) => qlist?.questions.find((q) => q.question === text)?.qtype;
  const qIndexOf = (text: string) => qlist?.questions.findIndex((q) => q.question === text) ?? -1;
  const lastQuestion = () => [...msgs].reverse().find((m): m is Extract<Msg, { kind: "q" }> => m.kind === "q");

  const newQMsg = (d: any): Msg => {
    const text = d.question || d.next_question || "";
    return {
      kind: "q",
      round: d.round ?? 1,
      text,
      qtype: qtypeOf(text),
      followup: (d.next_type || d.type) === "followup",
    };
  };

  /* ---------- JD ---------- */

  const parseText = async () => {
    if (!jdText.trim()) return;
    setBusy(true);
    try {
      const r = await parseJdText(jdText);
      if (r.data.error) return alert(r.data.error);
      setEditing(r.data);
      setJdText("");
      reloadJds();
    } finally { setBusy(false); }
  };

  const uploadImage = async (f: File) => {
    setBusy(true);
    try {
      const r = await parseJdImage(f);
      if (r.data.error) return alert(r.data.error);
      setEditing(r.data);
      reloadJds();
    } finally { setBusy(false); }
  };

  const confirmJd = async () => {
    if (!editing) return;
    const r = await updateJd(editing.id, {
      title: editing.title, company: editing.company, parsed: editing.parsed, status: "confirmed",
    });
    setEditing(null);
    setSelectedId(String(editing.id));
    setQlist(null);
    reloadJds();
    return r.data;
  };

  /* ---------- 题单 ---------- */

  const gen = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      const r = await generateQlist(selectedId === "generic" ? null : Number(selectedId), QLIST_QUOTA);
      if (r.data.error) return alert(r.data.error);
      setQlist(r.data);
    } finally { setBusy(false); }
  };

  const start = async () => {
    if (!qlist) return;
    setBusy(true);
    try {
      const sid = `iv-${Date.now()}`;
      const label = selectedId === "generic" ? "通用场" : `${jds.find((j) => j.id === Number(selectedId))?.title || "岗位"} 定制场`;
      const r = await startInterview({ topic: "mixed", session_id: sid, qlist_id: qlist.id });
      setSession({ id: sid, topicName: label, qlistId: qlist.id });
      localStorage.setItem(SAVED_KEY, JSON.stringify({ session_id: sid, topicName: label, qlist_id: qlist.id }));
      setMsgs([newQMsg({ ...r.data, type: "question" })]);
      setFinished(false);
      setQstatus({});
      if (r.data.progress) setProgress(r.data.progress);
    } finally { setBusy(false); }
  };

  const resume = async () => {
    if (!saved) return;
    setBusy(true);
    try {
      setSession({ id: saved.session_id, topicName: saved.topicName, qlistId: saved.qlist_id });
      let qtype: string | undefined;
      if (saved.qlist_id) {
        const d = await getQlist(saved.qlist_id);
        if (d.data && !d.data.error) {
          setQlist(d.data);
          qtype = (d.data.questions || []).find((q: any) => q.question === saved.question)?.qtype;
        }
      }
      if (saved.progress) setProgress(saved.progress);
      setMsgs([
        { kind: "sys", text: `已恢复未完成场次 · ${saved.topicName}` },
        { kind: "q", round: saved.round || 1, text: saved.question || "", qtype, followup: saved.waiting_for === "followup" },
      ]);
      setFinished(false);
      setSaved(null);
    } finally { setBusy(false); }
  };

  /* ---------- 作答 ---------- */

  const submit = async () => {
    const q = lastQuestion();
    if (!session || !q || !answer.trim() || busy) return;
    const ans = answer.trim();
    setAnswer("");
    push({ kind: "a", text: ans });
    setBusy(true);
    try {
      const d = (await answerInterview(session.id, ans)).data;
      const idx = qIndexOf(q.text);
      if (idx >= 0) setQstatus((s) => ({ ...s, [idx]: "answered" }));
      push({
        kind: "s", score: d.score, dims: d.dims || null, qScore: d.question_score,
        feedback: d.feedback, degraded: d.judge_degraded, question: q.text, answer: ans,
      });
      if (d.progress) setProgress(d.progress);
      if (d.finished) {
        push({ kind: "report", text: d.summary || "（无记录）" });
        setFinished(true);
        localStorage.removeItem(SAVED_KEY);
        loadRecords();
      } else if (d.next_question) {
        push(newQMsg(d));
      }
    } catch (e: any) {
      push({ kind: "sys", text: "请求失败：" + e.message });
    } finally { setBusy(false); }
  };

  const skip = async () => {
    const q = lastQuestion();
    if (!session || busy) return;
    setBusy(true);
    try {
      const d = (await skipQuestion(session.id)).data;
      if (q) {
        const idx = qIndexOf(q.text);
        if (idx >= 0) setQstatus((s) => ({ ...s, [idx]: "skipped" }));
      }
      push({ kind: "sys", text: "已跳过本题（不计分）" });
      if (d.progress) setProgress(d.progress);
      if (d.finished) {
        push({ kind: "report", text: d.summary || "（无记录）" });
        setFinished(true);
        localStorage.removeItem(SAVED_KEY);
        loadRecords();
      } else push(newQMsg(d));
    } finally { setBusy(false); }
  };

  const pick = async (index: number) => {
    if (!session || busy || finished) return;
    setBusy(true);
    try {
      const d = (await pickQuestion(session.id, index)).data;
      push({ kind: "sys", text: `已切换到第 ${index + 1} 题` }, newQMsg(d));
      if (d.progress) setProgress(d.progress);
    } finally { setBusy(false); }
  };

  const end = async () => {
    if (!session || busy) return;
    setBusy(true);
    try {
      const r = await endInterview(session.id);
      if (r.data.saved) {
        push({ kind: "report", text: r.data.summary });
      } else {
        push({ kind: "sys", text: "本场无作答记录，未生成复盘报告" });
      }
      setFinished(true);
      localStorage.removeItem(SAVED_KEY);
      loadRecords();
    } catch {} finally { setBusy(false); }
  };

  const resetAll = () => {
    setSession(null);
    setMsgs([]);
    setFinished(false);
    setQstatus({});
    setProgress(null);
    setSaved(null);
  };

  const doPolish = async (m: Extract<Msg, { kind: "s" }>) => {
    setBusy(true);
    try {
      const r = await polishAnswer(m.question, m.answer);
      setPolish(r.data);
    } finally { setBusy(false); }
  };

  const awaiting = !!session && !finished && !busy && msgs.length > 0 && msgs[msgs.length - 1].kind === "q";
  const confirmedJds = jds.filter((j) => j.status === "confirmed");

  return (
    <div className="flex h-full">
      {/* ================= 左栏：设置 / 题单 / 历史 ================= */}
      <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200/70 bg-[#fafbfc]">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">

          {saved && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4">
              <p className="text-sm font-semibold text-slate-900">有一场未完成的面试</p>
              <p className="mt-1 text-xs text-slate-500">{saved.topicName} · 第 {saved.round} 题</p>
              <div className="mt-3 flex gap-2">
                <Button size="sm" onClick={resume} disabled={busy}><RotateCcw className="h-3.5 w-3.5" /> 继续</Button>
                <Button size="sm" variant="ghost" onClick={() => { localStorage.removeItem(SAVED_KEY); setSaved(null); }}>放弃</Button>
              </div>
            </div>
          )}

          {/* JD 输入 */}
          <section className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-slate-800">
              <BriefcaseBusiness className="h-4 w-4 text-brand-600" /> 岗位 JD
            </h2>
            <Textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={4}
              disabled={!!session}
              placeholder="粘贴岗位描述文本…"
              className="text-[13px]"
            />
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              <Button size="sm" onClick={parseText} disabled={busy || !!session || !jdText.trim()}>解析文本</Button>
              <Button size="sm" variant="secondary" onClick={() => fileRef.current?.click()} disabled={busy || !!session}>
                <ImageUp className="h-3.5 w-3.5" /> JD 截图
              </Button>
            </div>
            <input ref={fileRef} type="file" accept=".png,.jpg,.jpeg,.webp" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadImage(f); e.target.value = ""; }} />
            <Select
              value={selectedId}
              onChange={(e) => { setSelectedId(e.target.value); setQlist(null); }}
              disabled={!!session}
              className="mt-2.5 w-full"
            >
              <option value="">选择已确认 JD…</option>
              {confirmedJds.map((j) => (
                <option key={j.id} value={j.id}>{j.title || "未命名岗位"}{j.company ? ` · ${j.company}` : ""}</option>
              ))}
              <option value="generic">— 通用模式（不指定 JD）—</option>
            </Select>
          </section>

          {/* 题单 */}
          <section className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-slate-800">
              <Wand2 className="h-4 w-4 text-brand-600" /> 面试题单
              {progress && <span className="ml-auto text-xs font-normal text-slate-400">{progress.consumed}/{progress.total}</span>}
            </h2>
            {!qlist ? (
              <>
                <Button size="sm" onClick={gen} disabled={busy || !!session || !selectedId} className="w-full">
                  <Wand2 className="h-3.5 w-3.5" /> {busy ? "生成中（约 1 分钟）…" : "生成三类题单"}
                </Button>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">
                  结合简历与知识库生成：技术八股 ×{QLIST_QUOTA["eight-part"]} · 项目深挖 ×{QLIST_QUOTA.project} · 业务场景 ×{QLIST_QUOTA.business}
                </p>
              </>
            ) : (
              <>
                <div className="mb-2.5 flex flex-wrap gap-1.5">
                  {Object.entries(QLIST_QUOTA).map(([k, n]) => (
                    <Tag key={k} color={QTYPE_COLORS[k]}>{QTYPE_NAMES[k]} ×{n}</Tag>
                  ))}
                </div>
                <ul className="space-y-1.5">
                  {qlist.questions.map((q, i) => {
                    const st = qstatus[i];
                    return (
                      <li key={i}>
                        <button
                          onClick={() => pick(i)}
                          disabled={!session || finished || busy || st === "answered"}
                          className="flex w-full items-start gap-2 rounded-xl border border-slate-200/80 px-3 py-2.5 text-left transition enabled:hover:border-brand-400 enabled:hover:shadow-sm disabled:cursor-default disabled:opacity-90"
                        >
                          <span className="mt-0.5 shrink-0 text-xs font-semibold text-slate-400">Q{i + 1}</span>
                          <span className="min-w-0 flex-1">
                            <span className={`block truncate text-[13px] leading-snug ${st === "skipped" ? "text-slate-400 line-through" : "text-slate-700"}`}>
                              {q.question}
                            </span>
                            <span className="mt-1 inline-block"><Tag color={QTYPE_COLORS[q.qtype] || "gray"}>{QTYPE_NAMES[q.qtype] || q.qtype}</Tag></span>
                          </span>
                          {st === "answered" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />}
                          {st === "skipped" && <SkipForward className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                {!session && (
                  <Button onClick={start} disabled={busy} className="mt-3 w-full">
                    <Play className="h-4 w-4" /> 开始面试（共 {qlist.total} 题）
                  </Button>
                )}
                {session && !finished && <p className="mt-2.5 text-center text-xs text-slate-400">面试进行中，点击题目可挑题</p>}
                {finished && (
                  <Button variant="secondary" onClick={resetAll} className="mt-3 w-full">
                    <RotateCcw className="h-4 w-4" /> 再来一场
                  </Button>
                )}
              </>
            )}
          </section>

          {/* 历史场次 */}
          <section className="rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm">
            <h2 className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-slate-800">
              <History className="h-4 w-4 text-slate-400" /> 历史场次
            </h2>
            {records.length === 0 ? (
              <p className="py-3 text-center text-xs text-slate-400">暂无场次</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {records.slice(0, 8).map((r) => (
                  <li key={r.session_id} className="flex items-center justify-between py-2.5 text-[13px]">
                    <span className="font-medium text-slate-700">{TOPIC_NAMES[r.topic] || r.topic}</span>
                    <span className="text-xs text-slate-400">{r.rounds} 题 · 均分 <b className="text-slate-700">{r.avg_score?.toFixed(1)}</b></span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </aside>

      {/* ================= 右栏：对话流 ================= */}
      <section className="flex h-full min-w-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6">
          {msgs.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <Mic2 className="h-7 w-7" />
              </span>
              <div>
                <p className="text-[15px] font-semibold text-slate-700">准备开始一场模拟面试</p>
                <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-slate-400">
                  在左侧贴入 JD 生成三类题单，或选择通用模式直接开考；面试官会逐题提问、追问深挖并五维评分
                </p>
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-5">
              {msgs.map((m, i) => {
                if (m.kind === "q") {
                  return (
                    <div key={i} className="flex justify-start">
                      <div className="max-w-[85%] rounded-2xl border border-slate-200/70 bg-white px-5 py-4 shadow-sm">
                        <div className="mb-1.5 flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-400">Q{m.round}</span>
                          {m.qtype && <Tag color={QTYPE_COLORS[m.qtype] || "gray"}>{QTYPE_NAMES[m.qtype] || m.qtype}</Tag>}
                          {m.followup && <Tag color="amber">深挖追问</Tag>}
                        </div>
                        <p className="text-[15px] leading-relaxed text-slate-900">{m.text}</p>
                      </div>
                    </div>
                  );
                }
                if (m.kind === "a") {
                  return (
                    <div key={i} className="flex justify-end">
                      <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-brand-600 px-4 py-3 text-sm leading-relaxed text-white shadow-sm">
                        {m.text}
                      </div>
                    </div>
                  );
                }
                if (m.kind === "s") {
                  return (
                    <div key={i} className="flex justify-start">
                      <div className="w-full max-w-[85%] rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
                        {m.degraded && <p className="mb-3 rounded-xl bg-amber-50 px-3.5 py-2 text-xs text-amber-700">评分服务降级，本题按 5 分兜底记录。</p>}
                        <div className="flex items-center gap-4">
                          <p className="text-3xl font-bold tracking-tight text-brand-600">
                            {m.score}<span className="text-sm font-normal text-slate-400"> /10</span>
                          </p>
                          <div className="min-w-0 flex-1">
                            {m.dims && <ScoreDims dims={m.dims} />}
                            {m.qScore != null && (
                              <p className="mt-1.5 text-xs text-slate-400">本题综合 <b className="text-slate-600">{m.qScore}</b> 分（首答 50% + 追问均分 50%）</p>
                            )}
                          </div>
                          <Button size="sm" variant="secondary" onClick={() => doPolish(m)} disabled={busy}>
                            <Sparkles className="h-3.5 w-3.5" /> 打磨答案
                          </Button>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap border-t border-slate-100 pt-3 text-sm leading-relaxed text-slate-700">{m.feedback}</p>
                      </div>
                    </div>
                  );
                }
                if (m.kind === "report") {
                  return (
                    <div key={i} className="flex justify-start">
                      <div className="w-full rounded-2xl border border-brand-100 bg-brand-50/40 p-5 shadow-sm">
                        <p className="mb-3 flex items-center gap-2 text-[15px] font-semibold text-slate-900">
                          <CheckCircle2 className="h-[18px] w-[18px] text-brand-600" /> 面试复盘报告
                        </p>
                        <div className="max-h-96 overflow-y-auto rounded-xl bg-white p-4">
                          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">{m.text}</pre>
                        </div>
                        <Button size="sm" className="mt-3" onClick={resetAll}>完成，再来一场</Button>
                      </div>
                    </div>
                  );
                }
                return (
                  <p key={i} className="py-1 text-center text-xs text-slate-400">{m.text}</p>
                );
              })}
              {busy && (
                <p className="text-center text-xs text-slate-400">面试官思考中…</p>
              )}
            </div>
          )}
        </div>

        {/* 底部固定输入栏 */}
        <div className="border-t border-slate-200/70 bg-white px-8 py-4">
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <VoiceInput onText={(t) => setAnswer((v) => (v ? v.replace(/\s+$/, "") + " " + t : t))} />
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
              rows={2}
              disabled={!awaiting}
              placeholder={session ? (finished ? "本场面试已结束" : "输入回答，Enter 发送，Shift+Enter 换行…") : "先在左侧生成题单并开始面试"}
              className="flex-1 resize-none rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm leading-relaxed outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50"
            />
            <Button onClick={submit} disabled={!awaiting || !answer.trim()} className="w-10 px-0" title="提交回答">
              <Send className="h-4 w-4" />
            </Button>
            <Button variant="secondary" onClick={skip} disabled={!session || finished || busy} title="跳过本题">
              <SkipForward className="h-4 w-4" />
            </Button>
            <Button variant="ghost" onClick={end} disabled={!session || finished || busy} title="结束面试" className="text-rose-500 hover:bg-rose-50 hover:text-rose-600">
              <StopCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* JD 解析草稿确认弹窗 */}
      {editing && (
        <Modal title="JD 解析结果确认" onClose={() => setEditing(null)}>
          <div className="grid gap-2.5">
            <Input value={editing.title || ""} onChange={(e) => setEditing({ ...editing, title: e.target.value })} placeholder="岗位名" />
            <Input value={editing.company || ""} onChange={(e) => setEditing({ ...editing, company: e.target.value })} placeholder="公司" />
            <Textarea
              value={(editing.parsed?.skills || []).join("\n")}
              onChange={(e) => setEditing({ ...editing, parsed: { ...editing.parsed, skills: e.target.value.split("\n") } })}
              rows={4}
              placeholder="技能要求（每行一条）"
            />
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setEditing(null)}>关闭</Button>
            <Button onClick={confirmJd}><Check className="h-4 w-4" /> 确认无误</Button>
          </div>
        </Modal>
      )}

      {/* 三档答案打磨弹窗 */}
      {polish && (
        <Modal title="三档答案打磨" onClose={() => setPolish(null)} wide>
          {polish?.versions && Object.entries(polish.versions).map(([tier, v]: any) => (
            <div key={tier} className="mb-5">
              <p className="mb-2 text-sm font-semibold text-slate-800">{tier}</p>
              <div className="grid gap-2.5 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-200 p-3.5 text-sm leading-relaxed">{v.zh}</div>
                <div className="rounded-xl bg-slate-50 p-3.5 text-sm leading-relaxed text-slate-700">{v.en}</div>
              </div>
            </div>
          ))}
          {polish?.tips?.length > 0 && (
            <div className="rounded-xl bg-amber-50 px-4 py-3">
              <p className="mb-1.5 text-sm font-semibold text-amber-800">表达建议</p>
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-700">
                {polish.tips.map((t: string, i: number) => <li key={i}>{t}</li>)}
              </ul>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
