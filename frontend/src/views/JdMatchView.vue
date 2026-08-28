<template>
  <div class="jd-view">
    <!-- 录入：文本 / 截图双通道 -->
    <div class="card">
      <h3>📋 录入岗位 JD</h3>
      <p class="tip">粘贴 JD 文本或上传招聘 App 截图，LLM 解析后先存草稿，确认无误才会用于生成题单</p>
      <el-input
        v-model="jdText"
        type="textarea"
        :rows="8"
        placeholder="把 Boss 直聘/拉勾上的岗位描述粘贴到这里…"
      />
      <div class="actions">
        <el-upload
          :show-file-list="false"
          accept=".png,.jpg,.jpeg,.webp"
          :http-request="uploadImage"
        >
          <el-button :loading="parsingImage">📷 上传 JD 截图</el-button>
        </el-upload>
        <el-button type="primary" :loading="parsingText" @click="parseText">解析文本</el-button>
      </div>
    </div>

    <!-- 草稿回显编辑 -->
    <div v-if="editing" class="card">
      <div class="card-head">
        <h3>✏️ 解析结果（{{ editing.status === "confirmed" ? "已确认" : "草稿待确认" }}）</h3>
        <el-tag :type="editing.status === 'confirmed' ? 'success' : 'warning'" size="small">
          {{ editing.status === "confirmed" ? "confirmed" : "draft" }}
        </el-tag>
      </div>
      <el-form label-width="90px">
        <el-form-item label="岗位名"><el-input v-model="editing.title" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="editing.company" /></el-form-item>
        <el-form-item label="岗位画像"><el-input v-model="editing.parsed.summary" /></el-form-item>
        <el-form-item label="技能要求">
          <el-input v-model="skillsText" type="textarea" :rows="4" placeholder="每行一条" />
        </el-form-item>
        <el-form-item label="经验要求">
          <el-input v-model="experienceText" type="textarea" :rows="3" placeholder="每行一条" />
        </el-form-item>
        <el-form-item label="软实力">
          <el-input v-model="softText" type="textarea" :rows="2" placeholder="每行一条" />
        </el-form-item>
      </el-form>
      <div class="actions">
        <el-button @click="editing = null">关闭</el-button>
        <el-button :loading="saving" @click="saveEdit(false)">保存修改</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit(true)">确认无误</el-button>
      </div>
    </div>

    <!-- JD 列表 -->
    <div class="card">
      <h3>🗃 已录入 JD</h3>
      <el-table :data="jds" v-loading="loadingList">
        <el-table-column prop="title" label="岗位" min-width="160" show-overflow-tooltip />
        <el-table-column prop="company" label="公司" width="140" show-overflow-tooltip />
        <el-table-column label="来源" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source === 'screenshot' ? 'warning' : 'info'">
              {{ row.source === "screenshot" ? "截图" : "文本" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'confirmed' ? 'success' : 'warning'">
              {{ row.status === "confirmed" ? "已确认" : "草稿" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">查看/编辑</el-button>
            <el-button
              v-if="row.status === 'confirmed'"
              link
              type="success"
              :loading="generatingId === row.id"
              @click="genQlist(row)"
            >生成题单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 题单展示 -->
    <el-dialog v-model="showQlist" title="📝 定制题单" width="720px">
      <div v-if="qlist" class="qlist">
        <p class="tip">共 {{ qlist.total }} 题（LLM 定制 + 题库补齐），可在「模拟面试」页按此题单开考</p>
        <div v-for="(q, i) in qlist.questions" :key="i" class="q-item">
          <div class="q-head">
            <span class="q-no">Q{{ i + 1 }}</span>
            <el-tag size="small">{{ topicName(q.qtype) }}</el-tag>
            <el-tag size="small" :type="difficultyType(q.difficulty)">{{ q.difficulty }}</el-tag>
            <el-tag size="small" :type="q.source === 'kb' ? 'info' : 'success'" effect="plain">
              {{ q.source === "kb" ? "题库补齐" : "LLM 定制" }}
            </el-tag>
          </div>
          <div class="q-text">{{ q.question }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { parseJdText, parseJdImage, listJds, updateJd, generateQlist } from "../api";

const TOPIC_NAMES = {
  agent: "Agent 专项",
  rag: "RAG 专项",
  project: "项目深挖",
  "eight-part": "八股基础",
  hr: "HR 面",
  mixed: "综合",
};

const jdText = ref("");
const parsingText = ref(false);
const parsingImage = ref(false);
const jds = ref([]);
const loadingList = ref(false);
const editing = ref(null);
const skillsText = ref("");
const experienceText = ref("");
const softText = ref("");
const saving = ref(false);
const generatingId = ref(null);
const showQlist = ref(false);
const qlist = ref(null);

const topicName = (t) => TOPIC_NAMES[t] || t;
const difficultyType = (d) => ({ easy: "info", medium: "warning", hard: "danger" }[d] || "info");

async function loadJds() {
  loadingList.value = true;
  try {
    const r = await listJds();
    jds.value = r.data.items || [];
  } finally {
    loadingList.value = false;
  }
}

function fillEditor(entry) {
  if (entry.error) return ElMessage.warning(entry.error);
  editing.value = {
    ...entry,
    parsed: { title: entry.title, company: entry.company, summary: "", skills: [], experience: [], soft: [], ...(entry.parsed || {}) },
  };
  skillsText.value = (editing.value.parsed.skills || []).join("\n");
  experienceText.value = (editing.value.parsed.experience || []).join("\n");
  softText.value = (editing.value.parsed.soft || []).join("\n");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function parseText() {
  if (!jdText.value.trim()) return ElMessage.warning("请先粘贴 JD 文本");
  parsingText.value = true;
  try {
    const r = await parseJdText(jdText.value);
    fillEditor(r.data);
    loadJds();
    ElMessage.success("解析完成，请核对草稿");
  } finally {
    parsingText.value = false;
  }
}

async function uploadImage({ file }) {
  parsingImage.value = true;
  try {
    const r = await parseJdImage(file);
    fillEditor(r.data);
    loadJds();
    ElMessage.success("截图识别完成，请核对草稿");
  } finally {
    parsingImage.value = false;
  }
}

function openEdit(row) {
  fillEditor(row);
}

async function saveEdit(confirm) {
  const p = editing.value.parsed;
  const payload = {
    title: editing.value.title,
    company: editing.value.company,
    parsed: {
      ...p,
      skills: skillsText.value.split("\n").map((s) => s.trim()).filter(Boolean),
      experience: experienceText.value.split("\n").map((s) => s.trim()).filter(Boolean),
      soft: softText.value.split("\n").map((s) => s.trim()).filter(Boolean),
    },
  };
  if (confirm) payload.status = "confirmed";
  saving.value = true;
  try {
    const r = await updateJd(editing.value.id, payload);
    if (r.data.error) return ElMessage.warning(r.data.error);
    ElMessage.success(confirm ? "已确认，可用于生成题单" : "修改已保存");
    fillEditor(r.data);
    loadJds();
  } finally {
    saving.value = false;
  }
}

async function genQlist(row) {
  generatingId.value = row.id;
  try {
    const r = await generateQlist(row.id);
    if (r.data.error) return ElMessage.warning(r.data.error);
    qlist.value = r.data;
    showQlist.value = true;
  } finally {
    generatingId.value = null;
  }
}

onMounted(loadJds);
</script>

<style scoped>
.jd-view { max-width: 960px; margin: 0 auto; display: grid; gap: 16px; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; }
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.card h3 { margin-bottom: 6px; }
.card-head h3 { margin-bottom: 0; }
.tip { color: #6b7280; font-size: 13px; margin-bottom: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.qlist .q-item { border-bottom: 1px dashed #e5e7eb; padding: 12px 0; }
.q-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.q-no { font-weight: 700; color: #6b7280; }
.q-text { line-height: 1.7; }
</style>
