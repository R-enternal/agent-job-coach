import { NavLink, Route, Routes } from "react-router-dom";
import { Briefcase, Home as HomeIcon, MessageSquare, Library, Mic2 } from "lucide-react";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import LibraryPage from "./pages/Library";
import Interview from "./pages/Interview";

const NAV = [
  { to: "/", label: "首页", icon: HomeIcon, end: true },
  { to: "/chat", label: "知识问答", icon: MessageSquare, end: false },
  { to: "/library", label: "资料库", icon: Library, end: false },
  { to: "/interview", label: "模拟面试", icon: Mic2, end: false },
];

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-[#f6f7f9]">
      {/* 左侧固定侧栏 */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200/70 bg-white">
        <NavLink to="/" className="flex h-16 items-center gap-2.5 border-b border-slate-100 px-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
            <Briefcase className="h-[18px] w-[18px]" />
          </span>
          <span>
            <span className="block text-[15px] font-semibold leading-tight tracking-tight text-slate-900">Agent Job Coach</span>
            <span className="block text-[11px] leading-tight text-slate-400">AI 求职陪练</span>
          </span>
        </NavLink>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex h-11 items-center gap-3 rounded-xl px-3.5 text-sm transition ${
                  isActive
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"
                }`
              }
            >
              <n.icon className="h-[18px] w-[18px]" />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <p className="border-t border-slate-100 px-5 py-3 text-[11px] text-slate-300">v2.0 · 题单化面试陪练</p>
      </aside>

      {/* 右侧全高内容区（各页面自管内部滚动） */}
      <main className="h-full min-w-0 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
    </div>
  );
}
