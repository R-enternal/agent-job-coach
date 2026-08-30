<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";
import { Mic, Square } from "lucide-vue-next";

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

const emit = defineEmits<{ (e: "text", t: string): void }>();

const supported = getCtor() !== null;
const recording = ref(false);
const lang = ref("zh-CN");
let rec: RecognitionLike | null = null;

onBeforeUnmount(() => rec?.abort());

const stop = () => {
  recording.value = false;
  try {
    rec?.stop();
  } catch {}
};

const toggle = () => {
  const Ctor = getCtor();
  if (!Ctor) return;
  if (recording.value) return stop();
  const r = new Ctor();
  r.lang = lang.value;
  r.continuous = true;
  r.interimResults = true;
  r.onresult = (e) => {
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const res = e.results[i];
      if (res.isFinal && res[0]?.transcript) emit("text", res[0].transcript);
    }
  };
  r.onerror = () => {
    recording.value = false;
  };
  r.onend = () => {
    recording.value = false;
  };
  rec = r;
  try {
    r.start();
    recording.value = true;
  } catch {
    recording.value = false;
  }
};

const toggleLang = () => {
  lang.value = lang.value === "zh-CN" ? "en-US" : "zh-CN";
};
</script>

<template>
  <span v-if="!supported" class="text-sm text-slate-400">语音需 Chrome/Edge</span>
  <div v-else class="flex items-center gap-1.5">
    <button
      type="button"
      :title="recording ? '停止识别' : '语音输入'"
      class="flex h-11 w-11 items-center justify-center rounded-xl border transition"
      :class="
        recording
          ? 'border-rose-200 bg-rose-50 text-rose-600'
          : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
      "
      @click="toggle"
    >
      <Square v-if="recording" class="h-4 w-4" />
      <Mic v-else class="h-4 w-4" />
    </button>
    <button
      type="button"
      :disabled="recording"
      title="切换识别语言"
      class="h-11 rounded-xl border border-slate-200 bg-white px-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
      @click="toggleLang"
    >
      {{ lang === "zh-CN" ? "中" : "EN" }}
    </button>
  </div>
</template>
