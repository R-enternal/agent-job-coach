import { useEffect, useRef, useState } from "react";
import { FileText, FileUp, RefreshCw, Trash2, UploadCloud } from "lucide-react";
import { getResume, kbDeleteDocument, kbDocuments, kbUpload, upsertResume } from "../api";
import { KB_CATEGORIES, KbDocument } from "../lib/types";
import { Button, Card, Empty, PageHeader, SectionTitle, Select, Spinner, Tag, Textarea } from "../components/ui";

const ACCEPT = ".md,.markdown,.txt,.html,.pdf,.docx";

/** 上传入库的文件 source 带 "{category}_" 前缀，展示时去掉 */
const displayName = (doc: KbDocument) =>
  doc.source.startsWith(`${doc.category}_`) ? doc.source.slice(doc.category.length + 1) : doc.source;

const TAG_COLORS: Record<string, string> = {
  resume: "blue",
  project: "green",
  interview: "amber",
  jd: "violet",
};

export default function Library() {
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [filter, setFilter] = useState("");
  const [listKey, setListKey] = useState(0);
  const reloadDocs = () => kbDocuments().then((r) => setDocs(r.data.items || [])).catch(() => {});
  useEffect(() => { reloadDocs(); }, [listKey]);

  const shown = docs.filter((d) => !filter || d.category === filter);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-10 py-8">
        <PageHeader title="资料库" desc="简历与知识库资料统一入库，自动解析切块，供知识问答与面试出题引用" />

        <div className="grid gap-5 lg:grid-cols-2">
          <ResumeCard onUploaded={() => setListKey((k) => k + 1)} />
          <KbUploadCard onUploaded={() => setListKey((k) => k + 1)} />
        </div>

      <Card className="mt-5 p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 pt-5 pb-4">
          <SectionTitle>已入库资料</SectionTitle>
          <div className="flex items-center gap-1.5">
            {["", "resume", "project", "interview", "jd"].map((c) => (
              <button
                key={c}
                onClick={() => setFilter(c)}
                className={`h-8 rounded-full px-3 text-xs font-medium transition ${
                  filter === c ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                }`}
              >
                {c ? KB_CATEGORIES[c] : "全部"}
              </button>
            ))}
            <Button variant="ghost" size="sm" onClick={reloadDocs} title="刷新列表">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        {shown.length === 0 ? (
          <Empty text="暂无资料，先从上方上传" />
        ) : (
          <ul className="divide-y divide-slate-100 border-t border-slate-100">
            {shown.map((d) => (
              <li key={d.source} className="flex items-center gap-3 px-6 py-3.5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                  <FileText className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">{displayName(d)}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{d.chunks} 个知识块</p>
                </div>
                <Tag color={TAG_COLORS[d.category] || "gray"}>{d.category_name || KB_CATEGORIES[d.category] || d.category}</Tag>
                <button
                  onClick={async () => {
                    if (!confirm(`删除「${displayName(d)}」的全部 ${d.chunks} 个知识块？`)) return;
                    await kbDeleteDocument(d.source);
                    reloadDocs();
                  }}
                  className="rounded-lg p-2 text-slate-300 transition hover:bg-rose-50 hover:text-rose-500"
                  title="删除"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
      </div>
    </div>
  );
}

/* ---------- 简历卡：粘贴文本（结构化解析）或传文件 ---------- */

function ResumeCard({ onUploaded }: { onUploaded: () => void }) {
  const [text, setText] = useState("");
  const [content, setContent] = useState<Record<string, string[]> | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getResume().then((r) => {
      if (r.data && !r.data.error) {
        setText(r.data.raw_text || "");
        setContent(r.data.content && Object.keys(r.data.content).length ? r.data.content : null);
      }
    }).catch(() => {});
  }, []);

  const save = async () => {
    if (!text.trim()) return;
    setSaving(true);
    setMsg("");
    try {
      const r = await upsertResume(text);
      setContent(r.data.content && Object.keys(r.data.content).length ? r.data.content : null);
      setMsg("已保存并解析");
    } finally {
      setSaving(false);
    }
  };

  const uploadFile = async (f: File) => {
    setSaving(true);
    setMsg("");
    try {
      const r = await kbUpload(f, "resume");
      setMsg(r.data.error ? r.data.error : `已入库：${r.data.filename}（${r.data.chunks} 块）`);
      onUploaded();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <SectionTitle>简历</SectionTitle>
      <p className="-mt-1 text-xs text-slate-400">粘贴文本自动解析要点（面试出题的主要素材）；或直接上传简历文件入库</p>
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        className="mt-3"
        placeholder="粘贴简历全文（教育 / 技能 / 实习 / 项目 / 获奖）…"
      />
      <div className="mt-3 flex items-center gap-2">
        <Button onClick={save} disabled={saving || !text.trim()}>{saving ? "解析中…" : "保存并解析"}</Button>
        <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={saving}>
          <FileUp className="h-4 w-4" /> 传文件
        </Button>
        <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadFile(f); e.target.value = ""; }} />
        {msg && <span className="text-xs text-emerald-600">{msg}</span>}
      </div>
      {content && (
        <div className="mt-4 space-y-2.5">
          {(["education", "skills", "experiences"] as const).map((k) =>
            content[k]?.length ? (
              <div key={k} className="rounded-xl bg-slate-50 px-4 py-3">
                <p className="mb-1.5 text-xs font-semibold text-slate-500">
                  {k === "education" ? "教育经历" : k === "skills" ? "技能" : "实习 / 项目 / 获奖"}
                </p>
                <ul className="list-disc space-y-1 pl-4 text-[13px] leading-relaxed text-slate-700">
                  {content[k].map((v, i) => <li key={i}>{v}</li>)}
                </ul>
              </div>
            ) : null
          )}
        </div>
      )}
    </Card>
  );
}

/* ---------- 知识库资料卡：分类 + 多文件上传 ---------- */

function KbUploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [category, setCategory] = useState("project");
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = async (files: FileList) => {
    setBusy(true);
    const logs: string[] = [];
    for (const f of Array.from(files)) {
      try {
        const r = await kbUpload(f, category);
        logs.push(r.data.error ? `✕ ${f.name}：${r.data.error}` : `✓ ${f.name}（${r.data.chunks} 块）`);
      } catch (e: any) {
        logs.push(`✕ ${f.name}：${e.message}`);
      }
    }
    setResults((r) => [...logs, ...r].slice(0, 8));
    setBusy(false);
    onUploaded();
  };

  return (
    <Card>
      <SectionTitle>知识库资料</SectionTitle>
      <p className="-mt-1 text-xs text-slate-400">题库、项目文档、岗位资料等，上传后自动解析切块入库</p>
      <div className="mt-3 flex items-center gap-2">
        <Select value={category} onChange={(e) => setCategory(e.target.value)} className="flex-1">
          {(["project", "interview", "jd"] as const).map((c) => (
            <option key={c} value={c}>{KB_CATEGORIES[c]}</option>
          ))}
        </Select>
        <Button onClick={() => fileRef.current?.click()} disabled={busy}>
          <UploadCloud className="h-4 w-4" /> {busy ? "上传中…" : "选择文件"}
        </Button>
        <input ref={fileRef} type="file" accept={ACCEPT} multiple hidden onChange={(e) => { if (e.target.files?.length) upload(e.target.files); e.target.value = ""; }} />
      </div>
      <p className="mt-2 text-xs text-slate-400">支持 md / txt / html / pdf / docx，可多选；简历请用左侧卡片</p>
      {busy && <Spinner label="解析入库中…" />}
      {results.length > 0 && (
        <ul className="mt-3 space-y-1.5 rounded-xl bg-slate-50 px-4 py-3 text-xs text-slate-600">
          {results.map((r, i) => (
            <li key={i} className={r.startsWith("✕") ? "text-rose-500" : ""}>{r}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}
