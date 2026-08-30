<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { FileText, RefreshCw, Trash2 } from "lucide-vue-next";
import { kbDeleteDocument, kbDocuments } from "../api";
import { KB_CATEGORIES, KbDocument } from "../lib/types";
import Card from "../components/Card.vue";
import Empty from "../components/Empty.vue";
import PageHeader from "../components/PageHeader.vue";
import SectionTitle from "../components/SectionTitle.vue";
import UButton from "../components/UButton.vue";
import UTag from "../components/UTag.vue";
import ResumeCard from "../components/ResumeCard.vue";
import KbUploadCard from "../components/KbUploadCard.vue";

/** 上传入库的文件 source 带 "{category}_" 前缀，展示时去掉 */
const displayName = (doc: KbDocument) =>
  doc.source.startsWith(`${doc.category}_`) ? doc.source.slice(doc.category.length + 1) : doc.source;

const TAG_COLORS: Record<string, string> = {
  resume: "blue",
  project: "green",
  interview: "amber",
  jd: "violet",
};

const FILTERS = ["", "resume", "project", "interview", "jd"];

const docs = ref<KbDocument[]>([]);
const filter = ref("");

const reloadDocs = () =>
  kbDocuments()
    .then((r) => (docs.value = r.data.items || []))
    .catch(() => {});

onMounted(reloadDocs);

const shown = computed(() => docs.value.filter((d) => !filter.value || d.category === filter.value));

const removeDoc = async (d: KbDocument) => {
  if (!confirm(`删除「${displayName(d)}」的全部 ${d.chunks} 个知识块？`)) return;
  await kbDeleteDocument(d.source);
  reloadDocs();
};
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="mx-auto max-w-6xl px-12 py-10">
      <PageHeader title="资料库" desc="简历与知识库资料统一入库，自动解析切块，供知识问答与面试出题引用" />

      <div class="grid gap-6 lg:grid-cols-2">
        <ResumeCard @uploaded="reloadDocs" />
        <KbUploadCard @uploaded="reloadDocs" />
      </div>

      <Card class="mt-6 !p-0">
        <div class="flex flex-wrap items-center justify-between gap-3 px-7 pb-5 pt-6">
          <SectionTitle class="!mb-0">已入库资料</SectionTitle>
          <div class="flex items-center gap-2">
            <button
              v-for="c in FILTERS"
              :key="c"
              class="h-9 rounded-full px-3.5 text-sm font-medium transition"
              :class="filter === c ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
              @click="filter = c"
            >
              {{ c ? KB_CATEGORIES[c] : "全部" }}
            </button>
            <UButton variant="ghost" size="sm" title="刷新列表" @click="reloadDocs">
              <RefreshCw class="h-4 w-4" />
            </UButton>
          </div>
        </div>
        <Empty v-if="shown.length === 0" text="暂无资料，先从上方上传" />
        <ul v-else class="divide-y divide-slate-100 border-t border-slate-100">
          <li v-for="d in shown" :key="d.source" class="flex items-center gap-3.5 px-7 py-4">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <FileText class="h-4 w-4" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-base font-medium text-slate-800">{{ displayName(d) }}</p>
              <p class="mt-0.5 text-sm text-slate-400">{{ d.chunks }} 个知识块</p>
            </div>
            <UTag :color="TAG_COLORS[d.category] || 'gray'">
              {{ d.category_name || KB_CATEGORIES[d.category] || d.category }}
            </UTag>
            <button
              class="rounded-lg p-2 text-slate-300 transition hover:bg-rose-50 hover:text-rose-500"
              title="删除"
              @click="removeDoc(d)"
            >
              <Trash2 class="h-4 w-4" />
            </button>
          </li>
        </ul>
      </Card>
    </div>
  </div>
</template>
