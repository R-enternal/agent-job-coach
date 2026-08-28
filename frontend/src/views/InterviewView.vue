<template>
  <div class="iv-view">
    <!-- 未开始：选择主题 -->
    <div v-if="!session" class="setup">
      <h2>🎤 模拟面试</h2>
      <p>选择面试主题，Agent 将扮演面试官：出题 → 追问 → 评分 → 生成复盘报告</p>
      <div class="topics">
        <el-card v-for="t in topics" :key="t.value" class="topic" shadow="hover" @click="start(t.value)">
          <h3>{{ t.label }}</h3>
          <p>{{ t.desc }}</p>
        </el-card>
      </div>
    </div>

    <!-- 面试中 -->
    <div v-else class="session">
      <el-alert
        :title="'第 ' + current.round + ' 题 · ' + current.topicName"
        type="info"
        :closable="false"
        class="round-alert"
      />
      <div class="question card">
        <h3>{{ current.question }}</h3>
      </div>

      <div class="answer card" v-if="!current.feedback">
        <el-input
          v-model="answer"
          type="textarea"
          :rows="6"
          placeholder="输入你的回答，尽量结构化：先结论、再展开、最后量化…"
        />
        <div class="actions">
          <el-button @click="quit">结束面试</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">提交回答</el-button>
        </div>
      </div>

      <div v-else class="result card">
        <el-result icon="success" :title="'本题得分 ' + current.score + ' / 10'">
          <template #sub-title>
            <div class="feedback">{{ current.feedback }}</div>
          </template>
          <template #extra>
            <el-button type="primary" v-if="current.nextQuestion" :loading="submitting" @click="next">
              {{ current.nextType === 'followup' ? '回答追问 →' : '下一题 →' }}
            </el-button>
            <el-button v-else @click="quit">返回</el-button>
          </template>
        </el-result>
      </div>

      <!-- 复盘报告 -->
      <el-dialog v-model="showSummary" title="📋 面试复盘报告" width="70%">
        <pre class="summary">{{ summary }}</pre>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../api";

const topics = [
  { value: "agent", label: "Agent 专项", desc: "LangGraph / ReAct / 工具调用 / 记忆" },
  { value: "rag", label: "RAG 专项", desc: "切块 / 混合检索 / RRF / 评测" },
  { value: "project", label: "项目深挖", desc: "仓维云 / JobPilot 细节追问" },
  { value: "eight-part", label: "八股基础", desc: "Python / FastAPI / 数据库" },
  { value: "hr", label: "HR 面", desc: "自我介绍 / 项目故事 / 职业规划" },
];

const session = ref(null);
const current = ref({});
const answer = ref("");
const submitting = ref(false);
const showSummary = ref(false);
const summary = ref("");

async function start(topic) {
  session.value = { id: "iv-" + Date.now(), topic };
  const topicName = topics.find((t) => t.value === topic)?.label || topic;
  const r = await api.post("/interview/start", { topic, session_id: session.value.id });
  current.value = {
    round: r.data.round,
    question: r.data.question,
    topicName,
    feedback: "",
  };
}

async function submit() {
  if (!answer.value.trim()) return;
  submitting.value = true;
  const r = await api.post("/interview/answer", {
    session_id: session.value.id,
    answer: answer.value,
  });
  const d = r.data;
  current.value = {
    ...current.value,
    score: d.score,
    feedback: d.feedback,
    nextQuestion: d.next_question || null,
    nextType: d.next_type || 'question',
  };
  answer.value = "";
  if (d.finished) {
    summary.value = d.summary || "（无复盘）";
    showSummary.value = true;
  }
  submitting.value = false;
}

async function next() {
  submitting.value = true;
  current.value = {
    round: current.value.round + 1,
    question: current.value.nextQuestion,
    topicName: current.value.topicName,
    feedback: "",
    nextType: null,
  };
  submitting.value = false;
}

function quit() {
  session.value = null;
  current.value = {};
  showSummary.value = false;
}
</script>

<style scoped>
.iv-view { height: 100%; }
.setup { max-width: 900px; margin: 0 auto; text-align: center; padding-top: 30px; }
.setup h2 { margin-bottom: 8px; }
.setup p { color: #6b7280; margin-bottom: 28px; }
.topics { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }
.topic { cursor: pointer; }
.topic h3 { margin-bottom: 6px; }
.topic p { color: #6b7280; font-size: 13px; }
.session { max-width: 900px; margin: 0 auto; }
.round-alert { margin-bottom: 16px; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; margin-bottom: 16px; }
.question h3 { line-height: 1.7; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.feedback { text-align: left; line-height: 1.8; padding: 0 20px; }
.summary { white-space: pre-wrap; font-family: inherit; line-height: 1.8; max-height: 60vh; overflow-y: auto; }
</style>
