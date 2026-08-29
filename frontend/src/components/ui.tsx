import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { Loader2, Inbox, X } from "lucide-react";

/* ---------- 布局 ---------- */

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200/70 bg-white p-6 shadow-[0_1px_3px_rgba(15,23,42,0.05)] ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({ title, desc, actions }: { title: string; desc?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SectionTitle({ children, extra }: { children: ReactNode; extra?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-[15px] font-semibold text-slate-900">{children}</h2>
      {extra}
    </div>
  );
}

/* ---------- 控件（统一 h-10 / rounded-xl / text-sm） ---------- */

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "md" | "sm";
};

export function Button({ variant = "primary", size = "md", className = "", ...rest }: BtnProps) {
  const v = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40",
    secondary: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40",
    ghost: "text-slate-500 hover:bg-slate-100 hover:text-slate-700",
    danger: "border border-rose-100 text-rose-500 hover:bg-rose-50",
  }[variant];
  const s = size === "sm" ? "h-8 px-3 text-xs" : "h-10 px-4 text-sm";
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-xl font-medium transition disabled:cursor-not-allowed ${s} ${v} ${className}`}
      {...rest}
    />
  );
}

export function Input({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50 ${className}`}
      {...rest}
    />
  );
}

export function Textarea({ className = "", ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm leading-relaxed text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50 ${className}`}
      {...rest}
    />
  );
}

export function Select({ className = "", ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 ${className}`}
      {...rest}
    />
  );
}

/* ---------- 反馈 ---------- */

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label || "加载中…"}
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-slate-400">
      <Inbox className="h-7 w-7" />
      <p className="text-sm">{text}</p>
    </div>
  );
}

export function Tag({ children, color = "blue" }: { children: ReactNode; color?: string }) {
  const map: Record<string, string> = {
    blue: "bg-brand-50 text-brand-700",
    green: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    gray: "bg-slate-100 text-slate-600",
    red: "bg-rose-50 text-rose-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${map[color] || map.blue}`}>
      {children}
    </span>
  );
}

export function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/30 p-5 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className={`max-h-[82vh] w-full overflow-y-auto rounded-2xl bg-white p-6 shadow-xl ${wide ? "max-w-2xl" : "max-w-lg"}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
