<script setup lang="ts">
import { onMounted, ref } from "vue";
import { FileUp } from "lucide-vue-next";
import { getResume, kbUpload, upsertResume } from "../api";
import Card from "./Card.vue";
import SectionTitle from "./SectionTitle.vue";
import UButton from "./UButton.vue";
import UTextarea from "./UTextarea.vue";

const ACCEPT = ".md,.markdown,.txt,.html,.pdf,.docx";

const emit = defineEmits<{ (e: "uploaded"): void }>();

const text = ref("");
const content = ref<Record<string, string[]> | null>(null);
const saving = ref(false);
const msg = ref("");
const fileRef = ref<HTMLInputElement | null>(null);

onMounted(() => {
  getResume()
    .then((r) => {
      if (r.data && !r.data.error) {
        text.value = r.data.raw_text || "";
        content.value = r.data.content && Object.keys(r.data.content).length ? r.data.content : null;
      }
    })
    .catch(() => {});
});

const save = async () => {
  if (!text.value.trim()) return;
  saving.value = true;
  msg.value = "";
  try {
    const r = await upsertResume(text.value);
    content.value = r.data.content && Object.keys(r.data.content).length ? r.data.content : null;
    msg.value = "已保存并解析";
  } finally {
    saving.value = false;
  }
};

const uploadFile = async (f: File) => {
  saving.value = true;
  msg.value = "";
  try {
    const r = await kbUpload(f, "resume");
    msg.value = r.data.error ? r.data.error : `已入库：${r.data.filename}（${r.data.chunks} 块）`;
    emit("uploaded");
  } finally {
    saving.value = false;
  }
};

const onFile = (e: Event) => {
  const input = e.target as HTMLInputElement;
  const f = input.files?.[0];
  if (f) uploadFile(f);
  input.value = "";
};

const SECTION_LABELS: Record<string, string> = {
  education: "教育经历",
  skills: "技能",
  experiences: "实习 / 项目 / 获奖",
};
</script>

<template>
  <Card>
    <SectionTitle>简历</SectionTitle>
    <p class="-mt-1 text-sm text-slate-400">粘贴文本自动解析要点（面试出题的主要素材）；或直接上传简历文件入库</p>
    <UTextarea
      v-model="text"
      :rows="8"
      class="mt-3.5"
      placeholder="粘贴简历全文（教育 / 技能 / 实习 / 项目 / 获奖）…"
    />
    <div class="mt-4 flex items-center gap-2.5">
      <UButton :disabled="saving || !text.trim()" @click="save">{{ saving ? "解析中…" : "保存并解析" }}</UButton>
      <UButton variant="secondary" :disabled="saving" @click="fileRef?.click()">
        <FileUp class="h-4 w-4" /> 传文件
      </UButton>
      <input ref="fileRef" type="file" :accept="ACCEPT" hidden @change="onFile" />
      <span v-if="msg" class="text-sm text-emerald-600">{{ msg }}</span>
    </div>
    <div v-if="content" class="mt-5 space-y-3">
      <template v-for="k in ['education', 'skills', 'experiences']" :key="k">
        <div v-if="content[k]?.length" class="rounded-xl bg-slate-50 px-5 py-4">
          <p class="mb-2 text-sm font-semibold text-slate-500">{{ SECTION_LABELS[k] }}</p>
          <ul class="list-disc space-y-1.5 pl-4 text-base leading-relaxed text-slate-700">
            <li v-for="(v, i) in content[k]" :key="i">{{ v }}</li>
          </ul>
        </div>
      </template>
    </div>
  </Card>
</template>
