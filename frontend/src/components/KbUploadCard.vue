<script setup lang="ts">
import { ref } from "vue";
import { UploadCloud } from "lucide-vue-next";
import { kbUpload } from "../api";
import { KB_CATEGORIES } from "../lib/types";
import Card from "./Card.vue";
import SectionTitle from "./SectionTitle.vue";
import Spinner from "./Spinner.vue";
import UButton from "./UButton.vue";
import USelect from "./USelect.vue";

const ACCEPT = ".md,.markdown,.txt,.html,.pdf,.docx";

const emit = defineEmits<{ (e: "uploaded"): void }>();

const category = ref("project");
const busy = ref(false);
const results = ref<string[]>([]);
const fileRef = ref<HTMLInputElement | null>(null);

const upload = async (files: FileList) => {
  busy.value = true;
  const logs: string[] = [];
  for (const f of Array.from(files)) {
    try {
      const r = await kbUpload(f, category.value);
      logs.push(r.data.error ? `✕ ${f.name}：${r.data.error}` : `✓ ${f.name}（${r.data.chunks} 块）`);
    } catch (e: any) {
      logs.push(`✕ ${f.name}：${e.message}`);
    }
  }
  results.value = [...logs, ...results.value].slice(0, 8);
  busy.value = false;
  emit("uploaded");
};

const onFiles = (e: Event) => {
  const input = e.target as HTMLInputElement;
  if (input.files?.length) upload(input.files);
  input.value = "";
};
</script>

<template>
  <Card>
    <SectionTitle>知识库资料</SectionTitle>
    <p class="-mt-1 text-sm text-slate-400">题库、项目文档、岗位资料等，上传后自动解析切块入库</p>
    <div class="mt-3.5 flex items-center gap-2.5">
      <USelect v-model="category" class="flex-1">
        <option v-for="c in ['project', 'interview', 'jd']" :key="c" :value="c">{{ KB_CATEGORIES[c] }}</option>
      </USelect>
      <UButton :disabled="busy" @click="fileRef?.click()">
        <UploadCloud class="h-4 w-4" /> {{ busy ? "上传中…" : "选择文件" }}
      </UButton>
      <input ref="fileRef" type="file" :accept="ACCEPT" multiple hidden @change="onFiles" />
    </div>
    <p class="mt-2.5 text-sm text-slate-400">支持 md / txt / html / pdf / docx，可多选；简历请用左侧卡片</p>
    <Spinner v-if="busy" label="解析入库中…" />
    <ul v-if="results.length" class="mt-4 space-y-2 rounded-xl bg-slate-50 px-5 py-4 text-sm text-slate-600">
      <li v-for="(r, i) in results" :key="i" :class="r.startsWith('✕') ? 'text-rose-500' : ''">{{ r }}</li>
    </ul>
  </Card>
</template>
