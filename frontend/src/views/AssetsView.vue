<template>
  <div class="assets-view">
    <!-- 简历底稿 -->
    <div class="card">
      <h3>📄 简历底稿</h3>
      <p class="tip">粘贴简历纯文本，保存时 LLM 自动解析为结构化要点，供题单生成与问答 Agent 引用</p>
      <el-input
        v-model="resumeText"
        type="textarea"
        :rows="8"
        placeholder="粘贴简历全文（教育/技能/实习/项目/获奖）…"
      />
      <div class="actions">
        <el-button type="primary" :loading="savingResume" @click="saveResume">保存底稿</el-button>
      </div>
      <div v-if="resumeContent" class="parsed">
        <h4>结构化要点（{{ resumeVersion }}，更新于 {{ resumeUpdatedAt }}）</h4>
        <template v-for="(label, key) in resumeLabels" :key="key">
          <div v-if="resumeContent[key]?.length" class="parsed-block">
            <b>{{ label }}</b>
            <ul>
              <li v-for="(item, i) in resumeContent[key]" :key="i">{{ item }}</li>
            </ul>
          </div>
        </template>
      </div>
    </div>

    <!-- 项目档案 -->
    <div class="card">
      <div class="card-head">
        <div>
          <h3>🗂 项目档案</h3>
          <p class="tip">面试中"项目深挖"题型的素材来源；可手工新增，或从知识库 project 文档让 LLM 抽取草稿后确认</p>
        </div>
        <div class="actions">
          <el-button :loading="extracting" @click="extractDraft">从知识库抽取草稿</el-button>
          <el-button type="primary" @click="openEdit(null)">新增项目</el-button>
        </div>
      </div>
      <el-table :data="projects" v-loading="loadingProjects">
        <el-table-column prop="name" label="项目名" width="180" />
        <el-table-column prop="one_liner" label="一句话简介" show-overflow-tooltip />
        <el-table-column prop="tech_stack" label="技术栈" width="220" show-overflow-tooltip />
        <el-table-column label="来源" width="110">
          <template #default="{ row }">
            <el-tag :type="row.source === 'llm_extract' ? 'warning' : 'info'" size="small">
              {{ row.source === "llm_extract" ? "LLM 抽取" : "手工" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="removeProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 项目编辑/草稿确认弹窗 -->
    <el-dialog v-model="showEdit" :title="form.id ? '编辑项目' : (form.source === 'llm_extract' ? '确认 LLM 抽取草稿' : '新增项目')" width="640px">
      <el-alert
        v-if="form.source === 'llm_extract'"
        title="以下为 LLM 从知识库抽取的草稿，请核对修改后保存"
        type="warning"
        :closable="false"
        class="draft-alert"
      />
      <el-form label-width="90px">
        <el-form-item label="项目名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="一句话简介"><el-input v-model="form.one_liner" /></el-form-item>
        <el-form-item label="技术栈"><el-input v-model="form.tech_stack" placeholder="Python | FastAPI | LangGraph" /></el-form-item>
        <el-form-item label="亮点">
          <el-input
            v-model="highlightsText"
            type="textarea"
            :rows="4"
            placeholder="每行一条，尽量量化（如：召回率 50%→100%）"
          />
        </el-form-item>
        <el-form-item label="STAR">
          <div class="star-grid">
            <el-input v-model="form.star.situation" placeholder="Situation 背景/痛点" />
            <el-input v-model="form.star.task" placeholder="Task 你的任务" />
            <el-input v-model="form.star.action" placeholder="Action 关键行动" />
            <el-input v-model="form.star.result" placeholder="Result 量化结果" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="savingProject" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  upsertResume,
  getResume,
  listProjects,
  createProject,
  updateProject,
  deleteProject,
  extractProjectDraft,
} from "../api";

const resumeLabels = { education: "教育经历", skills: "技能", experiences: "实习/项目/获奖" };

// ---- 简历底稿 ----
const resumeText = ref("");
const resumeContent = ref(null);
const resumeVersion = ref("");
const resumeUpdatedAt = ref("");
const savingResume = ref(false);

async function loadResume() {
  const r = await getResume();
  const d = r.data;
  if (d && !d.error) {
    resumeText.value = d.raw_text || "";
    resumeContent.value = d.content && Object.keys(d.content).length ? d.content : null;
    resumeVersion.value = d.version;
    resumeUpdatedAt.value = (d.updated_at || "").replace("T", " ").slice(0, 19);
  }
}

async function saveResume() {
  if (!resumeText.value.trim()) return ElMessage.warning("请先粘贴简历文本");
  savingResume.value = true;
  try {
    const r = await upsertResume(resumeText.value);
    ElMessage.success("简历底稿已保存并解析");
    resumeContent.value = r.data.content && Object.keys(r.data.content).length ? r.data.content : null;
    resumeUpdatedAt.value = (r.data.updated_at || "").replace("T", " ").slice(0, 19);
    resumeVersion.value = r.data.version;
  } finally {
    savingResume.value = false;
  }
}

// ---- 项目档案 ----
const projects = ref([]);
const loadingProjects = ref(false);
const showEdit = ref(false);
const savingProject = ref(false);
const extracting = ref(false);
const form = ref(emptyForm());
const highlightsText = ref("");

function emptyForm() {
  return {
    id: null,
    name: "",
    one_liner: "",
    tech_stack: "",
    star: { situation: "", task: "", action: "", result: "" },
    source: "manual",
  };
}

async function loadProjects() {
  loadingProjects.value = true;
  try {
    const r = await listProjects();
    projects.value = r.data.items || [];
  } finally {
    loadingProjects.value = false;
  }
}

function openEdit(row) {
  if (row) {
    form.value = {
      id: row.id,
      name: row.name,
      one_liner: row.one_liner || "",
      tech_stack: row.tech_stack || "",
      star: { situation: "", task: "", action: "", result: "", ...(row.star || {}) },
      source: row.source || "manual",
    };
    highlightsText.value = (row.highlights || []).join("\n");
  } else {
    form.value = emptyForm();
    highlightsText.value = "";
  }
  showEdit.value = true;
}

async function extractDraft() {
  extracting.value = true;
  try {
    const r = await extractProjectDraft();
    const d = r.data;
    if (d.error) return ElMessage.warning(d.error);
    form.value = {
      id: null,
      name: d.name || "",
      one_liner: d.one_liner || "",
      tech_stack: d.tech_stack || "",
      star: { situation: "", task: "", action: "", result: "", ...(d.star || {}) },
      source: "llm_extract",
    };
    highlightsText.value = (d.highlights || []).join("\n");
    showEdit.value = true;
  } finally {
    extracting.value = false;
  }
}

async function saveProject() {
  if (!form.value.name.trim()) return ElMessage.warning("项目名不能为空");
  const payload = {
    name: form.value.name,
    one_liner: form.value.one_liner,
    tech_stack: form.value.tech_stack,
    highlights: highlightsText.value.split("\n").map((s) => s.trim()).filter(Boolean),
    star: form.value.star,
    source: form.value.source,
  };
  savingProject.value = true;
  try {
    if (form.value.id) {
      await updateProject(form.value.id, payload);
    } else {
      await createProject(payload);
    }
    ElMessage.success("项目档案已保存");
    showEdit.value = false;
    loadProjects();
  } finally {
    savingProject.value = false;
  }
}

async function removeProject(row) {
  await ElMessageBox.confirm(`确认删除项目档案「${row.name}」？`, "删除确认", { type: "warning" });
  await deleteProject(row.id);
  ElMessage.success("已删除");
  loadProjects();
}

onMounted(() => {
  loadResume();
  loadProjects();
});
</script>

<style scoped>
.assets-view { max-width: 960px; margin: 0 auto; display: grid; gap: 16px; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.card h3 { margin-bottom: 6px; }
.tip { color: #6b7280; font-size: 13px; margin-bottom: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.card-head .actions { margin-top: 0; }
.parsed { margin-top: 16px; border-top: 1px dashed #e5e7eb; padding-top: 12px; }
.parsed h4 { font-size: 13px; color: #6b7280; margin-bottom: 10px; }
.parsed-block { margin-bottom: 10px; }
.parsed-block b { font-size: 14px; }
.parsed-block ul { padding-left: 20px; color: #374151; line-height: 1.8; font-size: 13px; }
.draft-alert { margin-bottom: 14px; }
.star-grid { display: grid; gap: 8px; width: 100%; }
</style>
