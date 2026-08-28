<template>
  <div class="pv-view">
    <div class="toolbar">
      <el-select v-model="project" placeholder="选择项目" style="width: 220px">
        <el-option label="仓维云（仓脉智诊）" value="仓维云" />
        <el-option label="JobPilot 求职助手" value="JobPilot" />
      </el-select>
      <el-button type="primary" :loading="loading" @click="run('dig')">🔍 面试官深挖</el-button>
      <el-button :loading="loading" @click="run('intro')">🎙️ 项目介绍话术</el-button>
      <el-select v-model="minutes" style="width: 130px" v-if="mode === 'intro'">
        <el-option label="0.5 分钟" :value="0.5" />
        <el-option label="1 分钟" :value="1" />
        <el-option label="3 分钟" :value="3" />
      </el-select>
    </div>

    <div v-if="result" class="card">
      <div class="result-head">
        <el-tag type="success">{{ mode === 'dig' ? '深挖追问' : '介绍话术' }}</el-tag>
        <span class="project-name">{{ project }}</span>
      </div>
      <pre class="result">{{ result }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../api";

const project = ref("仓维云");
const mode = ref("dig");
const minutes = ref(1);
const result = ref("");
const loading = ref(false);

async function run(m) {
  mode.value = m;
  loading.value = true;
  result.value = "";
  const q =
    m === "dig"
      ? `请深挖项目 ${project.value} 的 5 个面试追问`
      : `请生成项目 ${project.value} 的 ${minutes.value} 分钟面试介绍话术`;
  const r = await api.post("/agent/chat", {
    question: q,
    session_id: "proj-" + Date.now(),
  });
  result.value = r.data.answer;
  loading.value = false;
}
</script>

<style scoped>
.pv-view { max-width: 900px; margin: 0 auto; }
.toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; }
.result-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.project-name { font-weight: 600; }
.result { white-space: pre-wrap; line-height: 1.8; font-family: inherit; max-height: 65vh; overflow-y: auto; }
</style>
