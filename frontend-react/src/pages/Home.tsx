import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Library, MessageSquare, Mic2 } from "lucide-react";
import { getInterviewRecords } from "../api";
import { InterviewRecord, TOPIC_NAMES } from "../lib/types";
import { Card, Empty } from "../components/ui";

const ENTRIES = [
  {
    to: "/chat",
    title: "知识问答",
    desc: "多会话 RAG 检索问答，回答基于你的资料库，支持语音输入",
    icon: MessageSquare,
    iconBg: "bg-brand-50 text-brand-600",
  },
  {
    to: "/library",
    title: "资料库",
    desc: "简历与题库 / 项目文档统一上传，自动解析切块入库",
    icon: Library,
    iconBg: "bg-emerald-50 text-emerald-600",
  },
  {
    to: "/interview",
    title: "模拟面试",
    desc: "贴 JD 生成三类题单，AI 面试官追问深挖 + 五维评分 + 复盘",
    icon: Mic2,
    iconBg: "bg-violet-50 text-violet-600",
  },
];

export default function Home() {
  const [records, setRecords] = useState<InterviewRecord[]>([]);

  useEffect(() => {
    getInterviewRecords().then((r) => setRecords(r.data || [])).catch(() => {});
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-10 py-10">
        <section className="pb-10 pt-6 text-center">
          <h1 className="text-[28px] font-semibold tracking-tight text-slate-900">把资料，变成打动面试官的回答</h1>
          <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-slate-500">
            上传简历与知识库资料，粘贴 JD 生成定制题单，AI 面试官逐题追问、五维评分、复盘提升。
          </p>
        </section>

        <section className="grid gap-5 sm:grid-cols-3">
          {ENTRIES.map((e) => (
            <Link
              key={e.to}
              to={e.to}
              className="group rounded-2xl border border-slate-200/70 bg-white p-7 shadow-[0_1px_3px_rgba(15,23,42,0.05)] transition hover:-translate-y-1 hover:shadow-lg"
            >
              <div className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-2xl ${e.iconBg}`}>
                <e.icon className="h-[22px] w-[22px]" />
              </div>
              <h2 className="text-base font-semibold text-slate-900">{e.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{e.desc}</p>
              <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-brand-600">
                进入 <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </section>

        <section className="mt-10">
          <h2 className="mb-4 text-[15px] font-semibold text-slate-900">最近面试</h2>
          <Card className="p-0">
            {records.length === 0 ? (
              <Empty text="还没有面试记录，从一次模拟面试开始" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {records.slice(0, 6).map((r) => (
                  <li key={r.session_id} className="flex items-center justify-between px-6 py-4 text-sm">
                    <span className="font-medium text-slate-700">{TOPIC_NAMES[r.topic] || r.topic}</span>
                    <span className="text-xs text-slate-400">
                      {r.rounds} 题 · 均分 <b className="text-sm text-slate-700">{r.avg_score?.toFixed(1)}</b>
                      {r.created_at && <> · {new Date(r.created_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</>}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      </div>
    </div>
  );
}
