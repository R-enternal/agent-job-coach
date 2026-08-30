<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { ArrowRight, Library, MessageSquare, Mic2 } from "lucide-vue-next";
import { getInterviewRecords } from "../api";
import { InterviewRecord, TOPIC_NAMES } from "../lib/types";
import Card from "../components/Card.vue";
import Empty from "../components/Empty.vue";

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

const records = ref<InterviewRecord[]>([]);

onMounted(() => {
  getInterviewRecords()
    .then((r) => (records.value = r.data || []))
    .catch(() => {});
});

const fmtTime = (s: string) =>
  new Date(s).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto max-w-6xl px-12 py-12">
      <section class="pb-12 pt-6 text-center">
        <h1 class="text-3xl font-semibold tracking-tight text-slate-900">把资料，变成打动面试官的回答</h1>
        <p class="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-slate-500">
          上传简历与知识库资料，粘贴 JD 生成定制题单，AI 面试官逐题追问、五维评分、复盘提升。
        </p>
      </section>

      <section class="grid gap-6 sm:grid-cols-3">
        <RouterLink
          v-for="e in ENTRIES"
          :key="e.to"
          :to="e.to"
          class="group rounded-2xl border border-slate-200/60 bg-white p-8 shadow-card transition hover:-translate-y-1 hover:shadow-lift"
        >
          <div class="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl" :class="e.iconBg">
            <component :is="e.icon" class="h-6 w-6" />
          </div>
          <h2 class="text-lg font-semibold text-slate-900">{{ e.title }}</h2>
          <p class="mt-2 text-base leading-relaxed text-slate-500">{{ e.desc }}</p>
          <span class="mt-6 inline-flex items-center gap-1.5 text-base font-medium text-brand-600">
            进入 <ArrowRight class="h-4 w-4 transition group-hover:translate-x-0.5" />
          </span>
        </RouterLink>
      </section>

      <section class="mt-12">
        <h2 class="mb-4 text-lg font-semibold text-slate-900">最近面试</h2>
        <Card class="!p-0">
          <Empty v-if="records.length === 0" text="还没有面试记录，从一次模拟面试开始" />
          <ul v-else class="divide-y divide-slate-100">
            <li
              v-for="r in records.slice(0, 6)"
              :key="r.session_id"
              class="flex items-center justify-between px-7 py-5 text-base"
            >
              <span class="font-medium text-slate-700">{{ TOPIC_NAMES[r.topic] || r.topic }}</span>
              <span class="text-sm text-slate-400">
                {{ r.rounds }} 题 · 均分 <b class="text-base text-slate-700">{{ r.avg_score?.toFixed(1) }}</b>
                <template v-if="r.created_at"> · {{ fmtTime(r.created_at) }}</template>
              </span>
            </li>
          </ul>
        </Card>
      </section>
    </div>
  </div>
</template>
