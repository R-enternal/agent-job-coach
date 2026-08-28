<template>
  <div class="jd-view">
    <div class="card input-card">
      <h3>📋 粘贴岗位 JD</h3>
      <el-input
        v-model="jd"
        type="textarea"
        :rows="10"
        placeholder="把 Boss 直聘/拉勾上的岗位描述粘贴到这里，Agent 会解析技能要求并与你的简历/项目匹配…"
      />
      <div class="actions">
        <el-button @click="fillDemo">填入示例 JD</el-button>
        <el-button type="primary" :loading="loading" @click="run">生成匹配报告</el-button>
      </div>
    </div>

    <div v-if="result" class="card result-card">
      <h3>📊 匹配度诊断报告</h3>
      <pre class="result">{{ result }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../api";

const jd = ref("");
const result = ref("");
const loading = ref(false);

const demoJd = `岗位：AI Agent 应用开发实习生（合肥）
职责：参与智能问答 Agent 的研发，负责 RAG 知识库构建、工具调用与流式输出优化。
要求：
1. 熟悉 Python，了解 FastAPI 后端开发
2. 了解 LangChain / LangGraph 等 Agent 编排框架
3. 有 RAG 或向量数据库（Chroma/FAISS）项目经验
4. 熟悉 DeepSeek / OpenAI 兼容 API 调用
5. 有量化评测意识（准确率、召回率）`;

function fillDemo() {
  jd.value = demoJd;
}

async function run() {
  if (!jd.value.trim()) return;
  loading.value = true;
  result.value = "";
  const r = await api.post("/agent/chat", {
    question: "帮我评估一下这个 JD 的匹配度并给出简历优化建议：" + jd.value,
    session_id: "jd-" + Date.now(),
  });
  result.value = r.data.answer;
  loading.value = false;
}
</script>

<style scoped>
.jd-view { max-width: 900px; margin: 0 auto; display: grid; gap: 16px; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; }
.input-card h3 { margin-bottom: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.result-card h3 { margin-bottom: 12px; }
.result { white-space: pre-wrap; line-height: 1.8; font-family: inherit; max-height: 65vh; overflow-y: auto; }
</style>
