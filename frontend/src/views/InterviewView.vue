<template>
  <div class="iv-view">
    <!-- 未开始：选择主题 / 题单 -->
    <div v-if="!session" class="setup">
      <h2>🎤 模拟面试</h2>
      <p>选择主题现场出题，或按 JD 定制题单开考：出题 → 作答 → 评分 → 追问 → 复盘报告</p>
      <div class="topics">
        <el-card v-for="t in topics" :key="t.value" class="topic" shadow="hover" @click="startTopic(t)">
          <h3>{{ t.label }}</h3>
          <p>{{ t.desc }}</p>
        </el-card>
      </div>

      <div class="qlist-start card">
        <h3>📝 按题单开考</h3>
        <div class="qlist-row">
          <el-select v-model="selectedQlistId" placeholder="选择题单（在 JD 定制页生成）" class="qlist-select">
            <el-option
              v-for="q in qlists"
              :key="q.id"
              :value="q.id"
              :label="`题单 #${q.id} · ${q.total} 题${q.jd_id ? ' · JD #' + q.jd_id : ' · 通用'} · ${(q.created_at || '').slice(0, 10)}`"
            />
          </el-select>
          <el-button type="primary" :disabled="!selectedQlistId" :loading="starting" @click="startQlist">
            开考
          </el-button>
        </div>
      </div>

      <!-- 历史场次与提升 -->
      <div class="card history-card">
        <div class="card-head">
          <h3>📈 历史场次与复测提升</h3>
          <el-select v-model="compareTopic" placeholder="选主题看提升" size="small" style="width: 150px" @change="loadCompare">
            <el-option v-for="t in topics" :key="t.value" :value="t.value" :label="t.label" />
          </el-select>
        </div>
        <div v-if="compare" class="compare-line">
          <template v-if="compare.first_vs_latest">
            共 {{ compare.n_sessions }} 场：首场每题均分
            <b>{{ compare.first_vs_latest.first_final_avg }}</b> → 最近场
            <b>{{ compare.first_vs_latest.latest_final_avg }}</b>
            <el-tag :type="compare.first_vs_latest.delta >= 0 ? 'success' : 'danger'" size="small">
              {{ compare.first_vs_latest.delta >= 0 ? "+" : "" }}{{ compare.first_vs_latest.delta }}
            </el-tag>
          </template>
          <span v-else class="muted">{{ compare.n_sessions ? "仅 1 场，再练一场即可看提升" : "该主题暂无场次" }}</span>
        </div>
        <el-table :data="records" size="small" v-loading="loadingRecords">
          <el-table-column prop="session_id" label="场次" width="170" show-overflow-tooltip />
          <el-table-column label="主题" width="110">
            <template #default="{ row }">{{ topicName(row.topic) }}</template>
          </el-table-column>
          <el-table-column prop="rounds" label="题数" width="70" />
          <el-table-column label="场均分" width="80">
            <template #default="{ row }">{{ row.avg_score?.toFixed(1) ?? "-" }}</template>
          </el-table-column>
          <el-table-column label="时间">
            <template #default="{ row }">{{ (row.created_at || "").replace("T", " ").slice(0, 16) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 面试中 -->
    <div v-else class="session">
      <el-alert :closable="false" class="round-alert" type="info">
        <template #title>
          第 {{ current.round }} 题 · {{ session.topicName }}
          <template v-if="session.mode === 'qlist' && progress">
            （题单进度 {{ progress.consumed }}/{{ progress.total }}）
          </template>
        </template>
      </el-alert>
      <el-progress
        v-if="session.mode === 'qlist' && progress"
        :percentage="progress.total ? Math.round((progress.consumed / progress.total) * 100) : 0"
        :stroke-width="8"
        class="progress"
      />

      <div class="question card">
        <div class="q-head">
          <el-tag v-if="current.type === 'followup'" type="warning" size="small">深挖追问</el-tag>
          <h3>{{ current.question }}</h3>
        </div>
      </div>

      <!-- 作答区 -->
      <div class="answer card" v-if="!current.feedback">
        <el-input
          v-model="answer"
          type="textarea"
          :rows="6"
          placeholder="输入你的回答，尽量结构化：先结论、再展开、最后量化…"
        />
        <div class="actions">
          <el-button @click="quit">结束面试</el-button>
          <el-button v-if="session.mode === 'qlist'" @click="showPicker = true">挑题</el-button>
          <el-button :loading="acting" @click="skip">跳过本题</el-button>
          <VoiceInput @text="onVoiceText" />
          <el-button type="primary" :loading="acting" @click="submit">提交回答</el-button>
        </div>
      </div>

      <!-- 评分结果 -->
      <div v-else class="result card">
        <el-alert
          v-if="current.degraded"
          title="评分服务降级，本题按 5 分兜底记录，建议人工复核"
          type="warning"
          :closable="false"
          class="degraded-alert"
        />
        <el-result icon="success" :title="'本题得分 ' + current.score + ' / 10'">
          <template #sub-title>
            <div class="feedback">{{ current.feedback }}</div>
            <div v-if="current.dims && Object.keys(current.dims).length" class="dims-row">
              <el-tag
                v-for="(label, key) in DIM_LABELS"
                :key="key"
                v-show="current.dims[key] != null"
                size="small"
                effect="plain"
              >{{ label }} {{ current.dims[key] }}</el-tag>
            </div>
            <div v-if="current.questionScore != null" class="final-score">
              本题综合 <b>{{ current.questionScore }}</b> 分（首答 50% + 追问均分 50%）
            </div>
          </template>
          <template #extra>
            <el-button :loading="polishing" @click="polish">✨ 打磨答案</el-button>
            <el-button type="primary" v-if="current.nextQuestion" :loading="acting" @click="next">
              {{ current.nextType === "followup" ? "回答追问 →" : "下一题 →" }}
            </el-button>
            <el-button v-else @click="quit">返回</el-button>
          </template>
        </el-result>
      </div>

      <!-- 挑题抽屉 -->
      <el-drawer v-model="showPicker" title="挑题（点击切换）" size="420px">
        <div
          v-for="(q, i) in qlistQuestions"
          :key="i"
          class="pick-item"
          :class="{ active: i === currentQIndex, done: answeredIdx.has(i) }"
          @click="pick(i)"
        >
          <div class="pick-head">
            <span class="q-no">Q{{ i + 1 }}</span>
            <el-tag size="small">{{ topicName(q.qtype) }}</el-tag>
            <el-tag v-if="answeredIdx.has(i)" size="small" type="success" effect="plain">已答</el-tag>
            <el-tag v-if="skippedIdx.has(i)" size="small" type="info" effect="plain">已跳过</el-tag>
          </div>
          <div class="pick-text">{{ q.question }}</div>
        </div>
      </el-drawer>
    </div>

    <!-- 复盘报告（根级：主动结束面试后 session 已重置，dialog 仍需可见） -->
    <el-dialog v-model="showSummary" title="📋 面试复盘报告" width="70%">
      <pre class="summary">{{ summary }}</pre>
    </el-dialog>

    <!-- 答案打磨（三档双语） -->
    <el-dialog v-model="showPolish" title="✨ 答案打磨（三档双语）" width="720px">
      <template v-if="polishResult">
        <el-tabs v-model="polishTab">
          <el-tab-pane v-for="t in ['30s', '1min', '2min']" :key="t" :label="t" :name="t">
            <template v-if="polishResult.versions && polishResult.versions[t]">
              <h4>中文</h4>
              <div class="polish-text">{{ polishResult.versions[t].zh }}</div>
              <h4>English</h4>
              <div class="polish-text">{{ polishResult.versions[t].en }}</div>
            </template>
            <div v-else class="muted">该档位未生成</div>
          </el-tab-pane>
        </el-tabs>
        <div v-if="polishResult.tips && polishResult.tips.length" class="polish-tips">
          <h4>表达建议</h4>
          <ul><li v-for="(t, i) in polishResult.tips" :key="i">{{ t }}</li></ul>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import VoiceInput from "../components/VoiceInput.vue";
import {
  startInterview,
  answerInterview,
  pickQuestion,
  skipQuestion,
  endInterview,
  listQlists,
  getQlist,
  getRecords,
  getCompare,
  polishAnswer,
} from "../api";

const TOPIC_NAMES = {
  agent: "Agent 专项",
  rag: "RAG 专项",
  project: "项目深挖",
  "eight-part": "八股基础",
  hr: "HR 面",
  mixed: "综合",
};

const topics = [
  { value: "agent", label: "Agent 专项", desc: "LangGraph / ReAct / 工具调用 / 记忆" },
  { value: "rag", label: "RAG 专项", desc: "切块 / 混合检索 / RRF / 评测" },
  { value: "project", label: "项目深挖", desc: "仓维云 / JobPilot 细节追问" },
  { value: "eight-part", label: "八股基础", desc: "Python / FastAPI / 数据库" },
  { value: "hr", label: "HR 面", desc: "自我介绍 / 项目故事 / 职业规划" },
];

const topicName = (t) => TOPIC_NAMES[t] || t;

// 五维评分维名（与后端 _DIM_KEYS 对齐）
const DIM_LABELS = {
  correctness: "正确性",
  depth: "深度",
  structure: "结构",
  expression: "表达",
  risk_awareness: "风险意识",
};

// ---- 启动区 ----
const session = ref(null);
const current = ref({});
const answer = ref("");
const acting = ref(false);
const starting = ref(false);
const showSummary = ref(false);
const summary = ref("");
const qlists = ref([]);
const selectedQlistId = ref(null);
const records = ref([]);
const loadingRecords = ref(false);
const compareTopic = ref("");
const compare = ref(null);

// ---- 题单模式 ----
const progress = ref(null);
const qlistQuestions = ref([]);
const showPicker = ref(false);
const currentQIndex = ref(-1);
const answeredIdx = ref(new Set());
const skippedIdx = ref(new Set());

// ---- 答案打磨（M5.5） ----
const lastAnswer = ref("");      // submit 后 answer 清空，打磨要用原答
const polishing = ref(false);
const showPolish = ref(false);
const polishResult = ref(null);
const polishTab = ref("30s");

async function polish() {
  if (!lastAnswer.value.trim()) return ElMessage.warning("没有可打磨的原答");
  polishing.value = true;
  try {
    const r = await polishAnswer(current.value.question, lastAnswer.value);
    if (r.data.error) return ElMessage.warning(r.data.error);
    polishResult.value = r.data;
    polishTab.value = "30s";
    showPolish.value = true;
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "打磨失败");
  } finally {
    polishing.value = false;
  }
}

async function loadSetup() {
  try {
    const r = await listQlists();
    qlists.value = r.data.items || [];
  } catch { /* 题单列表失败不阻塞主题模式 */ }
  loadingRecords.value = true;
  try {
    const r = await getRecords();
    records.value = r.data || [];
  } finally {
    loadingRecords.value = false;
  }
}

async function loadCompare(topic) {
  if (!topic) return;
  const r = await getCompare(topic);
  compare.value = r.data;
}

function applyInterrupt(sessionId, d) {
  // start/answer/pick/skip 返回后统一落到"待作答"状态
  current.value = {
    round: d.round,
    question: d.question || d.next_question || "",
    type: d.next_type || "question",
    feedback: "",
  };
  if (d.progress) progress.value = d.progress;
  if (session.value?.mode === "qlist") {
    currentQIndex.value = qlistQuestions.value.findIndex(
      (q) => q.question === current.value.question
    );
  }
}

function handleFinish(d) {
  if (d.finished) {
    if (session.value) session.value.finished = true; // 防 quit 重复调 /end
    summary.value = d.summary || "（无复盘）";
    showSummary.value = true;
  }
}

async function startTopic(t) {
  starting.value = true;
  try {
    const sid = "iv-" + Date.now();
    const r = await startInterview({ topic: t.value, session_id: sid });
    session.value = { id: sid, topic: t.value, topicName: t.label, mode: "topic" };
    progress.value = null;
    qlistQuestions.value = [];
    applyInterrupt(sid, r.data);
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "启动失败");
  } finally {
    starting.value = false;
  }
}

async function startQlist() {
  starting.value = true;
  try {
    const sid = "iv-" + Date.now();
    const [detail, r] = await Promise.all([
      getQlist(selectedQlistId.value),
      startInterview({ topic: "mixed", session_id: sid, qlist_id: selectedQlistId.value }),
    ]);
    qlistQuestions.value = detail.data.questions || [];
    answeredIdx.value = new Set();
    skippedIdx.value = new Set();
    session.value = { id: sid, topic: "mixed", topicName: `题单 #${selectedQlistId.value}`, mode: "qlist" };
    progress.value = r.data.progress || null;
    applyInterrupt(sid, r.data);
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "启动失败");
  } finally {
    starting.value = false;
  }
}

function onVoiceText(text) {
  // 语音识别结果追加到作答框（与已有文本之间补空格）
  const t = (text || "").trim();
  if (!t) return;
  answer.value = answer.value ? answer.value.replace(/\s+$/, "") + " " + t : t;
}

async function submit() {
  if (!answer.value.trim()) return;
  acting.value = true;
  try {
    const r = await answerInterview(session.value.id, answer.value);
    const d = r.data;
    if (session.value.mode === "qlist" && currentQIndex.value >= 0) {
      answeredIdx.value = new Set([...answeredIdx.value, currentQIndex.value]);
    }
    lastAnswer.value = answer.value;
    answer.value = "";
    if (d.finished) {
      current.value = { ...current.value, score: d.score, feedback: d.feedback, questionScore: d.question_score, degraded: d.judge_degraded, dims: d.dims || null, nextQuestion: null };
      handleFinish(d);
    } else {
      current.value = {
        ...current.value,
        score: d.score,
        feedback: d.feedback,
        questionScore: d.question_score,
        degraded: d.judge_degraded,
        dims: d.dims || null,
        nextQuestion: d.next_question || null,
        nextType: d.next_type || "question",
        nextRound: d.round,
        nextProgress: d.progress || null,
      };
    }
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "提交失败");
  } finally {
    acting.value = false;
  }
}

async function next() {
  // 重赋值前先取出暂存字段，否则 nextRound/nextProgress 会被新对象冲掉（进度条不更新的 bug）
  const { nextRound, nextProgress, nextQuestion, nextType } = current.value;
  current.value = {
    round: nextRound ?? current.value.round + 1,
    question: nextQuestion,
    type: nextType,
    feedback: "",
  };
  if (nextProgress) progress.value = nextProgress;
  if (session.value?.mode === "qlist") {
    currentQIndex.value = qlistQuestions.value.findIndex((q) => q.question === current.value.question);
  }
}

async function skip() {
  acting.value = true;
  try {
    const r = await skipQuestion(session.value.id);
    const d = r.data;
    if (session.value.mode === "qlist" && currentQIndex.value >= 0) {
      skippedIdx.value = new Set([...skippedIdx.value, currentQIndex.value]);
    }
    ElMessage.info("已跳过（不计分，复盘中可见）");
    answer.value = "";
    current.value.feedback = "";
    if (d.finished) {
      handleFinish(d);
    } else {
      applyInterrupt(session.value.id, d);
    }
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "操作失败");
  } finally {
    acting.value = false;
  }
}

async function pick(index) {
  if (index === currentQIndex.value) {
    showPicker.value = false;
    return;
  }
  acting.value = true;
  try {
    const r = await pickQuestion(session.value.id, index);
    answer.value = "";
    current.value.feedback = "";
    applyInterrupt(session.value.id, r.data);
    showPicker.value = false;
  } catch (e) {
    ElMessage.warning(e.response?.data?.detail || "操作失败");
  } finally {
    acting.value = false;
  }
}

async function quit() {
  const s = session.value;
  // 服务端收尾：进行中的场次调 /end 生成复盘报告并落库；已自然结束的场次跳过（防 409）
  if (s && !s.finished) {
    try {
      const r = await endInterview(s.id);
      if (r.data.saved) {
        summary.value = r.data.summary;
        showSummary.value = true;
      } else {
        ElMessage.info(r.data.summary);
      }
    } catch (e) {
      if (e.response?.status !== 409) {
        ElMessage.warning(e.response?.data?.detail || "结束失败");
      }
    }
  }
  session.value = null;
  current.value = {};
  progress.value = null;
  selectedQlistId.value = null;
  compare.value = null;
  loadSetup();
}

onMounted(loadSetup);
</script>

<style scoped>
.iv-view { height: 100%; }
.setup { max-width: 960px; margin: 0 auto; text-align: center; padding-top: 24px; }
.setup h2 { margin-bottom: 8px; }
.setup > p { color: #6b7280; margin-bottom: 24px; }
.topics { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }
.topic { cursor: pointer; }
.topic h3 { margin-bottom: 6px; }
.topic p { color: #6b7280; font-size: 13px; }
.card { background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 20px; margin-top: 16px; text-align: left; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.card h3 { margin-bottom: 10px; }
.card-head h3 { margin-bottom: 0; }
.qlist-row { display: flex; gap: 10px; }
.qlist-select { flex: 1; }
.compare-line { margin-bottom: 10px; color: #374151; font-size: 14px; }
.muted { color: #9ca3af; }
.session { max-width: 900px; margin: 0 auto; }
.round-alert { margin-bottom: 12px; }
.progress { margin-bottom: 14px; }
.session .card { margin-top: 0; margin-bottom: 16px; }
.q-head h3 { line-height: 1.7; display: inline; }
.q-head .el-tag { margin-right: 8px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.feedback { text-align: left; line-height: 1.8; padding: 0 20px; }
.dims-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 12px; }
.final-score { margin-top: 10px; color: #374151; }
.degraded-alert { margin-bottom: 10px; }
.summary { white-space: pre-wrap; font-family: inherit; line-height: 1.8; max-height: 60vh; overflow-y: auto; }
.polish-text { background: #f9fafb; border-radius: 8px; padding: 10px 12px; white-space: pre-wrap; line-height: 1.7; margin-bottom: 12px; }
.polish-tips { margin-top: 8px; }
.polish-tips ul { padding-left: 20px; line-height: 1.8; }
.pick-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; cursor: pointer; }
.pick-item:hover { border-color: #7dd3fc; }
.pick-item.active { border-color: #0ea5e9; background: #f0f9ff; }
.pick-item.done .pick-text { color: #9ca3af; }
.pick-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.q-no { font-weight: 700; color: #6b7280; font-size: 13px; }
.pick-text { font-size: 13px; line-height: 1.6; }
</style>
