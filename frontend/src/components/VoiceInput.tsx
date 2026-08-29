import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";

type RecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: any) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: any) => void) | null;
};

function getCtor(): (new () => RecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export default function VoiceInput({ onText }: { onText: (t: string) => void }) {
  const [supported] = useState(() => getCtor() !== null);
  const [recording, setRecording] = useState(false);
  const [lang, setLang] = useState("zh-CN");
  const recRef = useRef<RecognitionLike | null>(null);

  useEffect(() => () => recRef.current?.abort(), []);

  const stop = () => {
    setRecording(false);
    try {
      recRef.current?.stop();
    } catch {}
  };

  const toggle = () => {
    const Ctor = getCtor();
    if (!Ctor) return;
    if (recording) return stop();
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;
    let got = false;
    rec.onresult = (e) => {
      got = true;
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal && r[0]?.transcript) onText(r[0].transcript);
      }
    };
    rec.onerror = () => setRecording(false);
    rec.onend = () => setRecording(false);
    recRef.current = rec;
    try {
      rec.start();
      setRecording(true);
    } catch {
      setRecording(false);
    }
  };

  if (!supported) {
    return <span className="text-xs text-slate-400">语音需 Chrome/Edge</span>;
  }

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={toggle}
        className={`flex h-10 w-10 items-center justify-center rounded-xl border transition ${
          recording
            ? "border-rose-200 bg-rose-50 text-rose-600"
            : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
        }`}
        title={recording ? "停止识别" : "语音输入"}
      >
        {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
      </button>
      <button
        type="button"
        onClick={() => setLang(lang === "zh-CN" ? "en-US" : "zh-CN")}
        disabled={recording}
        className="h-10 rounded-xl border border-slate-200 bg-white px-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        title="切换识别语言"
      >
        {lang === "zh-CN" ? "中" : "EN"}
      </button>
    </div>
  );
}
