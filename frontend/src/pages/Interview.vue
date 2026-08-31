<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  BriefcaseBusiness, Check, CheckCircle2, History, ImageUp, Mic2, Play,
  RotateCcw, Send, SkipForward, Sparkles, StopCircle, Wand2,
} from "lucide-vue-next";
import {
  answerInterview, endInterview, generateQlist, getInterviewHistory, getInterviewRecords,
  getInterviewState, getQlist, listJds, parseJdImage, parseJdText, pickQuestion, polishAnswer,
  skipQuestion, startInterview, updateJd,
} from "../api";
import { InterviewRecord, Jd, Qlist, QLIST_QUOTA, QTYPE_NAMES, TOPIC_NAMES } from "../lib/types";
import UButton from "../components/UButton.vue";
import UInput from "../components/UInput.vue";
import UModal from "../components/UModal.vue";
import USelect from "../components/USelect.vue";
import UTag from "../components/UTag.vue";
import UTextarea from "../components/UTextarea.vue";
import ScoreDims from "../components/ScoreDims.vue";
import VoiceInput from "../components/VoiceInput.vue";

const SAVED_KEY = "ajc_active_interview";
const QTYPE_COLORS: Record<string, string> = { "eight-part": "blue", project: "green", business: "violet" };

/* 对话流消息：问题 / 回答 / 评分卡 / 系统提示 / 复盘报告 */
type Msg =
  | { kind: "q"; round: number; text: string; qtype?: string; followup?: boolean }
  | { kind: "a"; text: string }
  | { kind: "s"; score?: number; dims?: Record<string, number> | null; qScore?: number | null; feedback: string; degraded?: boolean; question: string; answer: string }
  | { kind: "sys"; text: string }
  | { kind: "report"; text: string };

interface SessionMeta {
  id: string;
  topicName: string;
  qlistId: number;
}

/* ---------- 左栏：设置 ---------- */
const jds = ref<Jd[]>([]);
const jdText = ref("");
const editing = ref<Jd | null>(null);
const selectedId = ref(""); // "" 未选 / "generic" 通用 / 其余为 JD id
const qlist = ref<Qlist | null>(null);
const records = ref<InterviewRecord[]>([]);

/* ---------- 右栏：对话 ---------- */
const session = ref<SessionMeta | null>(null);
const msgs = ref<Msg[]>([]);
const answer = ref("");
const busy = ref(false);
const finished = ref(false);
const qstatus = ref<Record<number, "answered" | "skipped">>({});
const progress = ref<{ consumed: number; total: number } | null>(null);
const saved = ref<any>(null);
const polish = ref<any>(null);

const scrollRef = ref<HTMLDivElement | null>(null);
const fileRef = ref<HTMLInputElement | null>(null);
const scrollBottom = () =>
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  });

const loadRecords = () =>
  getInterviewRecords()
    .then((r) => (records.value = r.data || []))
    .catch(() => {});

/* 历史场次回放：事件流在 Redis（7 天 TTL），过期仅留 MySQL 汇总 */
const replay = ref<{ title: string; rounds: any[] } | null>(null);
const openReplay = async (r: InterviewRecord) => {
  const title = `${TOPIC_NAMES[r.topic] || r.topic} · ${r.rounds} 题 · 均分 ${
    r.avg_score != null ? r.avg_score.toFixed(1) : "-"
  }`;
  try {
    const res = await getInterviewHistory(r.session_id);
    replay.value = { title, rounds: res.data.rounds || [] };
  } catch {
    replay.value = { title, rounds: [] };
  }
};
const reloadJds = () =>
  listJds()
    .then((r) => (jds.value = r.data.items || []))
    .catch(() => {});

const checkSaved = async () => {
  const raw = localStorage.getItem(SAVED_KEY);
  if (!raw) return;
  try {
    const m = JSON.parse(raw);
    const r = await getInterviewState(m.session_id);
    if (r.data.resumable) saved.value = { ...m, ...r.data };
    else localStorage.removeItem(SAVED_KEY);
  } catch {
    localStorage.removeItem(SAVED_KEY);
  }
};

onMounted(() => {
  reloadJds();
  loadRecords();
  checkSaved();
});
watch(() => msgs.value.length, scrollBottom);

const push = (...m: Msg[]) => msgs.value.push(...m);
const qtypeOf = (text: string) => qlist.value?.questions.find((q) => q.question === text)?.qtype;
const qIndexOf = (text: string) => qlist.value?.questions.findIndex((q) => q.question === text) ?? -1;
const lastQuestion = () => [...msgs.value].reverse().find((m): m is Extract<Msg, { kind: "q" }> => m.kind === "q");

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
  if (!jdText.value.trim()) return;
  busy.value = true;
  try {
    const r = await parseJdText(jdText.value);
    if (r.data.error) return alert(r.data.error);
    editing.value = r.data;
    jdText.value = "";
    reloadJds();
  } finally {
    busy.value = false;
  }
};

const uploadImage = async (f: File) => {
  busy.value = true;
  try {
    const r = await parseJdImage(f);
    if (r.data.error) return alert(r.data.error);
    editing.value = r.data;
    reloadJds();
  } finally {
    busy.value = false;
  }
};

const onJdImage = (e: Event) => {
  const input = e.target as HTMLInputElement;
  const f = input.files?.[0];
  if (f) uploadImage(f);
  input.value = "";
};

const confirmJd = async () => {
  if (!editing.value) return;
  const cur = editing.value;
  await updateJd(cur.id, {
    title: cur.title,
    company: cur.company,
    parsed: cur.parsed,
    status: "confirmed",
  });
  editing.value = null;
  selectedId.value = String(cur.id);
  qlist.value = null;
  reloadJds();
};

const editingSkills = computed({
  get: () => (editing.value?.parsed?.skills || []).join("\n"),
  set: (v: string) => {
    if (editing.value) editing.value.parsed = { ...editing.value.parsed, skills: v.split("\n") };
  },
});

const onSelectJd = (v: string) => {
  selectedId.value = v;
  qlist.value = null;
};

/* ---------- 题单 ---------- */

const gen = async () => {
  if (!selectedId.value) return;
  busy.value = true;
  try {
    const r = await generateQlist(selectedId.value === "generic" ? null : Number(selectedId.value), QLIST_QUOTA);
    if (r.data.error) return alert(r.data.error);
    qlist.value = r.data;
  } finally {
    busy.value = false;
  }
};

const start = async () => {
  if (!qlist.value) return;
  busy.value = true;
  try {
    const sid = `iv-${Date.now()}`;
    const label =
      selectedId.value === "generic"
        ? "通用场"
        : `${jds.value.find((j) => j.id === Number(selectedId.value))?.title || "岗位"} 定制场`;
    const r = await startInterview({ topic: "mixed", session_id: sid, qlist_id: qlist.value.id });
    session.value = { id: sid, topicName: label, qlistId: qlist.value.id };
    localStorage.setItem(SAVED_KEY, JSON.stringify({ session_id: sid, topicName: label, qlist_id: qlist.value.id }));
    msgs.value = [newQMsg({ ...r.data, type: "question" })];
    finished.value = false;
    qstatus.value = {};
    if (r.data.progress) progress.value = r.data.progress;
  } finally {
    busy.value = false;
  }
};

const resume = async () => {
  if (!saved.value) return;
  busy.value = true;
  try {
    const s = saved.value;
    session.value = { id: s.session_id, topicName: s.topicName, qlistId: s.qlist_id };
    let qtype: string | undefined;
    if (s.qlist_id) {
      const d = await getQlist(s.qlist_id);
      if (d.data && !d.data.error) {
        qlist.value = d.data;
        qtype = (d.data.questions || []).find((q: any) => q.question === s.question)?.qtype;
      }
    }
    if (s.progress) progress.value = s.progress;
    msgs.value = [
      { kind: "sys", text: `已恢复未完成场次 · ${s.topicName}` },
      { kind: "q", round: s.round || 1, text: s.question || "", qtype, followup: s.waiting_for === "followup" },
    ];
    finished.value = false;
    saved.value = null;
  } finally {
    busy.value = false;
  }
};

const dropSaved = () => {
  localStorage.removeItem(SAVED_KEY);
  saved.value = null;
};

/* ---------- 作答 ---------- */

const submit = async () => {
  const q = lastQuestion();
  if (!session.value || !q || !answer.value.trim() || busy.value) return;
  const ans = answer.value.trim();
  answer.value = "";
  push({ kind: "a", text: ans });
  busy.value = true;
  try {
    const d = (await answerInterview(session.value.id, ans)).data;
    const idx = qIndexOf(q.text);
    if (idx >= 0) qstatus.value = { ...qstatus.value, [idx]: "answered" };
    push({
      kind: "s", score: d.score, dims: d.dims || null, qScore: d.question_score,
      feedback: d.feedback, degraded: d.judge_degraded, question: q.text, answer: ans,
    });
    if (d.progress) progress.value = d.progress;
    if (d.finished) {
      push({ kind: "report", text: d.summary || "（无记录）" });
      finished.value = true;
      localStorage.removeItem(SAVED_KEY);
      loadRecords();
    } else if (d.next_question) {
      push(newQMsg(d));
    }
  } catch (e: any) {
    answer.value = ans; // 失败回填，避免白答
    push({ kind: "sys", text: "请求失败：" + e.message });
  } finally {
    busy.value = false;
  }
};

const skip = async () => {
  const q = lastQuestion();
  if (!session.value || busy.value) return;
  busy.value = true;
  try {
    const d = (await skipQuestion(session.value.id)).data;
    if (q) {
      const idx = qIndexOf(q.text);
      if (idx >= 0) qstatus.value = { ...qstatus.value, [idx]: "skipped" };
    }
    push({ kind: "sys", text: "已跳过本题（不计分）" });
    if (d.progress) progress.value = d.progress;
    if (d.finished) {
      push({ kind: "report", text: d.summary || "（无记录）" });
      finished.value = true;
      localStorage.removeItem(SAVED_KEY);
      loadRecords();
    } else {
      push(newQMsg(d));
    }
  } finally {
    busy.value = false;
  }
};

const pick = async (index: number) => {
  if (!session.value || busy.value || finished.value) return;
  busy.value = true;
  try {
    const d = (await pickQuestion(session.value.id, index)).data;
    push({ kind: "sys", text: `已切换到第 ${index + 1} 题` }, newQMsg(d));
    if (d.progress) progress.value = d.progress;
  } finally {
    busy.value = false;
  }
};

const end = async () => {
  if (!session.value || busy.value) return;
  busy.value = true;
  try {
    const r = await endInterview(session.value.id);
    if (r.data.saved) {
      push({ kind: "report", text: r.data.summary });
    } else {
      push({ kind: "sys", text: "本场无作答记录，未生成复盘报告" });
    }
    finished.value = true;
    localStorage.removeItem(SAVED_KEY);
    loadRecords();
  } catch {
  } finally {
    busy.value = false;
  }
};

const resetAll = () => {
  session.value = null;
  msgs.value = [];
  finished.value = false;
  qstatus.value = {};
  progress.value = null;
  saved.value = null;
};

const doPolish = async (m: Extract<Msg, { kind: "s" }>) => {
  busy.value = true;
  try {
    const r = await polishAnswer(m.question, m.answer);
    polish.value = r.data;
  } finally {
    busy.value = false;
  }
};

const onAnswerKeydown = (e: KeyboardEvent) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    submit();
  }
};

const onVoiceAnswer = (t: string) => {
  answer.value = answer.value ? answer.value.replace(/\s+$/, "") + " " + t : t;
};

const awaiting = computed(
  () =>
    !!session.value &&
    !finished.value &&
    !busy.value &&
    msgs.value.length > 0 &&
    msgs.value[msgs.value.length - 1].kind === "q"
);
const confirmedJds = computed(() => jds.value.filter((j) => j.status === "confirmed"));
const polishVersions = computed<[string, any][]>(() =>
  polish.value?.versions ? Object.entries(polish.value.versions) : []
);
</script>

<template>
  <div class="flex h-full">
    <!-- ================= 左栏：设置 / 题单 / 历史 ================= -->
    <aside class="flex w-[22rem] shrink-0 flex-col border-r border-slate-200/60 bg-[#fafbfc]">
      <div class="flex-1 space-y-5 overflow-y-auto p-5">
        <!-- 断点恢复 -->
        <div v-if="saved" class="rounded-2xl border border-amber-200 bg-amber-50/60 p-5">
          <p class="text-base font-semibold text-slate-900">有一场未完成的面试</p>
          <p class="mt-1.5 text-sm text-slate-500">{{ saved.topicName }} · 第 {{ saved.round }} 题</p>
          <div class="mt-3.5 flex gap-2">
            <UButton size="sm" :disabled="busy" @click="resume"><RotateCcw class="h-4 w-4" /> 继续</UButton>
            <UButton size="sm" variant="ghost" @click="dropSaved">放弃</UButton>
          </div>
        </div>

        <!-- JD 输入 -->
        <section class="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-card">
          <h2 class="mb-3.5 flex items-center gap-2 text-base font-semibold text-slate-800">
            <BriefcaseBusiness class="h-[18px] w-[18px] text-brand-600" /> 岗位 JD
          </h2>
          <UTextarea v-model="jdText" :rows="4" :disabled="!!session" placeholder="粘贴岗位描述文本…" />
          <div class="mt-3 grid grid-cols-2 gap-2">
            <UButton size="sm" :disabled="busy || !!session || !jdText.trim()" @click="parseText">解析文本</UButton>
            <UButton size="sm" variant="secondary" :disabled="busy || !!session" @click="fileRef?.click()">
              <ImageUp class="h-4 w-4" /> JD 截图
            </UButton>
          </div>
          <input ref="fileRef" type="file" accept=".png,.jpg,.jpeg,.webp" hidden @change="onJdImage" />
          <USelect
            :model-value="selectedId"
            :disabled="!!session"
            class="mt-3 w-full"
            @update:model-value="onSelectJd"
          >
            <option value="">选择已确认 JD…</option>
            <option v-for="j in confirmedJds" :key="j.id" :value="String(j.id)">
              {{ j.title || "未命名岗位" }}{{ j.company ? ` · ${j.company}` : "" }}
            </option>
            <option value="generic">— 通用模式（不指定 JD）—</option>
          </USelect>
        </section>

        <!-- 题单 -->
        <section class="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-card">
          <h2 class="mb-3.5 flex items-center gap-2 text-base font-semibold text-slate-800">
            <Wand2 class="h-[18px] w-[18px] text-brand-600" /> 面试题单
            <span v-if="progress" class="ml-auto text-sm font-normal text-slate-400">
              {{ progress.consumed }}/{{ progress.total }}
            </span>
          </h2>
          <template v-if="!qlist">
            <UButton size="sm" class="w-full" :disabled="busy || !!session || !selectedId" @click="gen">
              <Wand2 class="h-4 w-4" /> {{ busy ? "生成中（约 1 分钟）…" : "生成三类题单" }}
            </UButton>
            <p class="mt-2.5 text-sm leading-relaxed text-slate-400">
              结合简历与知识库生成：技术八股 ×{{ QLIST_QUOTA["eight-part"] }} · 项目深挖 ×{{ QLIST_QUOTA.project }} · 业务场景 ×{{ QLIST_QUOTA.business }}
            </p>
          </template>
          <template v-else>
            <div class="mb-3 flex flex-wrap gap-1.5">
              <UTag v-for="(n, k) in QLIST_QUOTA" :key="k" :color="QTYPE_COLORS[k]">
                {{ QTYPE_NAMES[k] }} ×{{ n }}
              </UTag>
            </div>
            <ul class="space-y-2">
              <li v-for="(q, i) in qlist.questions" :key="i">
                <button
                  class="flex w-full items-start gap-2.5 rounded-xl border border-slate-200/80 px-3.5 py-3 text-left transition enabled:hover:border-brand-400 enabled:hover:shadow-sm disabled:cursor-default disabled:opacity-90"
                  :disabled="!session || finished || busy || qstatus[i] === 'answered'"
                  @click="pick(i)"
                >
                  <span class="mt-0.5 shrink-0 text-sm font-semibold text-slate-400">Q{{ i + 1 }}</span>
                  <span class="min-w-0 flex-1">
                    <span
                      class="block truncate text-sm leading-snug"
                      :class="qstatus[i] === 'skipped' ? 'text-slate-400 line-through' : 'text-slate-700'"
                    >
                      {{ q.question }}
                    </span>
                    <span class="mt-1.5 inline-block">
                      <UTag :color="QTYPE_COLORS[q.qtype] || 'gray'">{{ QTYPE_NAMES[q.qtype] || q.qtype }}</UTag>
                    </span>
                  </span>
                  <CheckCircle2 v-if="qstatus[i] === 'answered'" class="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                  <SkipForward v-else-if="qstatus[i] === 'skipped'" class="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                </button>
              </li>
            </ul>
            <UButton v-if="!session" class="mt-3.5 w-full" :disabled="busy" @click="start">
              <Play class="h-4 w-4" /> 开始面试（共 {{ qlist.total }} 题）
            </UButton>
            <p v-else-if="!finished" class="mt-3 text-center text-sm text-slate-400">面试进行中，点击题目可挑题</p>
            <UButton v-if="finished" variant="secondary" class="mt-3.5 w-full" @click="resetAll">
              <RotateCcw class="h-4 w-4" /> 再来一场
            </UButton>
          </template>
        </section>

        <!-- 历史场次 -->
        <section class="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-card">
          <h2 class="mb-2.5 flex items-center gap-2 text-base font-semibold text-slate-800">
            <History class="h-[18px] w-[18px] text-slate-400" /> 历史场次
          </h2>
          <p v-if="records.length === 0" class="py-3 text-center text-sm text-slate-400">暂无场次</p>
          <ul v-else class="divide-y divide-slate-100">
            <li v-for="r in records.slice(0, 8)" :key="r.session_id">
              <button
                class="-mx-2 flex w-[calc(100%+1rem)] items-center justify-between rounded-lg px-2 py-3 text-left text-sm transition hover:bg-brand-50/60"
                title="查看本场问答回放"
                @click="openReplay(r)"
              >
                <span class="font-medium text-slate-700">{{ TOPIC_NAMES[r.topic] || r.topic }}</span>
                <span class="text-sm text-slate-400">
                  {{ r.rounds }} 题 · 均分 <b class="text-slate-700">{{ r.avg_score?.toFixed(1) }}</b>
                </span>
              </button>
            </li>
          </ul>
          <p v-if="records.length" class="mt-1.5 text-xs text-slate-400">点击场次回看问答详情（明细保留 7 天）</p>
        </section>
      </div>
    </aside>

    <!-- ================= 右栏：对话流 ================= -->
    <section class="flex h-full min-w-0 flex-1 flex-col">
      <div ref="scrollRef" class="flex-1 overflow-y-auto px-10 py-8">
        <div v-if="msgs.length === 0" class="flex h-full flex-col items-center justify-center gap-5 text-center">
          <span class="flex h-20 w-20 items-center justify-center rounded-3xl bg-brand-50 text-brand-600">
            <Mic2 class="h-8 w-8" />
          </span>
          <div>
            <p class="text-lg font-semibold text-slate-700">准备开始一场模拟面试</p>
            <p class="mx-auto mt-2 max-w-md text-base leading-relaxed text-slate-400">
              在左侧贴入 JD 生成三类题单，或选择通用模式直接开考；面试官会逐题提问、追问深挖并五维评分
            </p>
          </div>
        </div>
        <div v-else class="mx-auto max-w-3xl space-y-6">
          <template v-for="(m, i) in msgs" :key="i">
            <!-- 面试官问题 -->
            <div v-if="m.kind === 'q'" class="flex justify-start">
              <div class="max-w-[85%] rounded-2xl border border-slate-200/60 bg-white px-6 py-5 shadow-card">
                <div class="mb-2 flex items-center gap-2">
                  <span class="text-sm font-semibold text-slate-400">Q{{ m.round }}</span>
                  <UTag v-if="m.qtype" :color="QTYPE_COLORS[m.qtype] || 'gray'">
                    {{ QTYPE_NAMES[m.qtype] || m.qtype }}
                  </UTag>
                  <UTag v-if="m.followup" color="amber">深挖追问</UTag>
                </div>
                <p class="text-lg leading-relaxed text-slate-900">{{ m.text }}</p>
              </div>
            </div>
            <!-- 用户回答 -->
            <div v-else-if="m.kind === 'a'" class="flex justify-end">
              <div class="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-brand-600 px-5 py-3.5 text-base leading-relaxed text-white shadow-sm">
                {{ m.text }}
              </div>
            </div>
            <!-- 评分卡 -->
            <div v-else-if="m.kind === 's'" class="flex justify-start">
              <div class="w-full max-w-[85%] rounded-2xl border border-slate-200/60 bg-white p-6 shadow-card">
                <p v-if="m.degraded" class="mb-3 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-700">
                  评分服务降级，本题按 5 分兜底记录。
                </p>
                <div class="flex items-center gap-5">
                  <p class="text-4xl font-bold tracking-tight text-brand-600">
                    {{ m.score }}<span class="text-base font-normal text-slate-400"> /10</span>
                  </p>
                  <div class="min-w-0 flex-1">
                    <ScoreDims v-if="m.dims" :dims="m.dims" />
                    <p v-if="m.qScore != null" class="mt-2 text-sm text-slate-400">
                      本题综合 <b class="text-slate-600">{{ m.qScore }}</b> 分（首答 50% + 追问均分 50%）
                    </p>
                  </div>
                  <UButton size="sm" variant="secondary" :disabled="busy" @click="doPolish(m)">
                    <Sparkles class="h-4 w-4" /> 打磨答案
                  </UButton>
                </div>
                <p class="mt-4 whitespace-pre-wrap border-t border-slate-100 pt-4 text-base leading-relaxed text-slate-700">
                  {{ m.feedback }}
                </p>
              </div>
            </div>
            <!-- 复盘报告 -->
            <div v-else-if="m.kind === 'report'" class="flex justify-start">
              <div class="w-full rounded-2xl border border-brand-100 bg-brand-50/40 p-6 shadow-card">
                <p class="mb-3.5 flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <CheckCircle2 class="h-5 w-5 text-brand-600" /> 面试复盘报告
                </p>
                <div class="max-h-96 overflow-y-auto rounded-xl bg-white p-5">
                  <pre class="whitespace-pre-wrap font-sans text-base leading-relaxed text-slate-700">{{ m.text }}</pre>
                </div>
                <UButton size="sm" class="mt-4" @click="resetAll">完成，再来一场</UButton>
              </div>
            </div>
            <!-- 系统提示 -->
            <p v-else class="py-1 text-center text-sm text-slate-400">{{ m.text }}</p>
          </template>
          <p v-if="busy" class="text-center text-sm text-slate-400">面试官思考中…</p>
        </div>
      </div>

      <!-- 底部固定输入栏 -->
      <div class="border-t border-slate-200/60 bg-white px-10 py-5">
        <div class="mx-auto flex max-w-3xl items-end gap-2.5">
          <VoiceInput @text="onVoiceAnswer" />
          <textarea
            v-model="answer"
            rows="2"
            :disabled="!awaiting"
            :placeholder="
              session
                ? finished
                  ? '本场面试已结束'
                  : '输入回答，Enter 发送，Shift+Enter 换行…'
                : '先在左侧生成题单并开始面试'
            "
            class="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-3 text-base leading-relaxed outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50"
            @keydown="onAnswerKeydown"
          />
          <UButton class="w-11 px-0" :disabled="!awaiting || !answer.trim()" title="提交回答" @click="submit">
            <Send class="h-4 w-4" />
          </UButton>
          <UButton variant="secondary" :disabled="!session || finished || busy" title="跳过本题" @click="skip">
            <SkipForward class="h-4 w-4" />
          </UButton>
          <UButton
            variant="ghost"
            class="text-rose-500 hover:bg-rose-50 hover:text-rose-600"
            :disabled="!session || finished || busy"
            title="结束面试"
            @click="end"
          >
            <StopCircle class="h-4 w-4" />
          </UButton>
        </div>
      </div>
    </section>

    <!-- JD 解析草稿确认弹窗 -->
    <UModal v-if="editing" title="JD 解析结果确认" @close="editing = null">
      <div class="grid gap-3">
        <UInput v-model="editing.title" placeholder="岗位名" />
        <UInput v-model="editing.company" placeholder="公司" />
        <UTextarea v-model="editingSkills" :rows="4" placeholder="技能要求（每行一条）" />
      </div>
      <div class="mt-5 flex justify-end gap-2">
        <UButton variant="ghost" @click="editing = null">关闭</UButton>
        <UButton @click="confirmJd"><Check class="h-4 w-4" /> 确认无误</UButton>
      </div>
    </UModal>

    <!-- 三档答案打磨弹窗 -->
    <UModal v-if="polish" title="三档答案打磨" wide @close="polish = null">
      <div v-for="[tier, v] in polishVersions" :key="tier" class="mb-6">
        <p class="mb-2.5 text-base font-semibold text-slate-800">{{ tier }}</p>
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-xl border border-slate-200 p-4 text-base leading-relaxed">{{ v.zh }}</div>
          <div class="rounded-xl bg-slate-50 p-4 text-base leading-relaxed text-slate-700">{{ v.en }}</div>
        </div>
      </div>
      <div v-if="polish.tips?.length" class="rounded-xl bg-amber-50 px-5 py-4">
        <p class="mb-2 text-base font-semibold text-amber-800">表达建议</p>
        <ul class="list-disc space-y-1.5 pl-5 text-base text-amber-700">
          <li v-for="(t, i) in polish.tips" :key="i">{{ t }}</li>
        </ul>
      </div>
    </UModal>

    <!-- 历史场次问答回放 -->
    <UModal v-if="replay" :title="replay.title" wide @close="replay = null">
      <p v-if="replay.rounds.length === 0" class="py-6 text-center text-base text-slate-400">
        该场次无作答明细（明细在 Redis 保留 7 天，过期仅留汇总记录）
      </p>
      <div
        v-for="(rd, i) in replay.rounds"
        :key="i"
        class="mb-4 rounded-xl border border-slate-200/80 p-4"
      >
        <p class="mb-2 text-base font-semibold leading-snug text-slate-800">
          Q{{ rd.round }}　{{ rd.question }}
        </p>
        <p v-if="rd.skipped" class="text-sm text-amber-600">已跳过（不计分）</p>
        <template v-else>
          <p class="whitespace-pre-wrap text-base leading-relaxed text-slate-700">答：{{ rd.answer }}</p>
          <div class="mt-2.5 flex items-center gap-4 border-t border-slate-100 pt-2.5 text-sm text-slate-500">
            <span>评分 <b class="text-brand-600">{{ rd.score }}</b>/10</span>
            <span v-if="rd.question_score != null">
              本题综合 <b class="text-slate-700">{{ rd.question_score }}</b>
            </span>
          </div>
          <ScoreDims v-if="rd.dims && Object.keys(rd.dims).length" :dims="rd.dims" class="mt-2" />
          <p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-500">{{ rd.feedback }}</p>
        </template>
      </div>
    </UModal>
  </div>
</template>
