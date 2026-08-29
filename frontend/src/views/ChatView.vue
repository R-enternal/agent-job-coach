<template>
  <div class="chat-view">
    <!-- 多会话管理栏 -->
    <div class="session-bar">
      <el-select
        v-model="sessionId"
        placeholder="选择会话"
        style="width: 300px"
        @change="switchSession"
      >
        <el-option
          v-for="s in sessions"
          :key="s.session_id"
          :value="s.session_id"
          :label="sessionLabel(s)"
        />
      </el-select>
      <el-button @click="newSession">＋ 新建会话</el-button>
      <el-button
        v-if="sessionId"
        type="danger"
        plain
        :loading="deleting"
        @click="removeSession"
      >删除</el-button>
      <span v-if="sessionId" class="session-id" :title="sessionId">
        {{ sessionId.slice(0, 12) }}…
      </span>
    </div>

    <div class="chat-box" ref="chatBox" v-loading="loadingHistory">
      <div class="welcome" v-if="!messages.length && !loadingHistory">
        <h3>👋 欢迎使用 Agent Job Coach 知识问答</h3>
        <p>会话已持久化：切页面不丢记录；可新建/切换多个会话（如按岗位分开）</p>
        <el-tag class="sug" @click="ask('什么是 LangGraph 状态图？')">什么是 LangGraph 状态图？</el-tag>
        <el-tag class="sug" @click="ask('RAG 混合检索为什么用 RRF？')">RAG 为什么用 RRF 融合？</el-tag>
        <el-tag class="sug" @click="ask('帮我整理一下 function calling 的知识点')">整理 function calling 笔记</el-tag>
        <el-tag class="sug" @click="ask('仓维云项目有什么亮点？')">仓维云项目亮点</el-tag>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
        <div class="bubble" v-if="m.role === 'user'">{{ m.content }}</div>
        <div v-else class="bubble ai">
          <div v-if="m.tools && m.tools.length" class="tools">
            <el-tag v-for="t in m.tools" :key="t" size="small" type="info">
              🔧 {{ t }}
            </el-tag>
          </div>
          <div class="content">{{ m.content }}</div>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <el-input
        v-model="input"
        placeholder="输入你的求职问题，Enter 发送…"
        size="large"
        @keyup.enter="send"
        :disabled="loading"
      />
      <VoiceInput @text="onVoiceText" />
      <el-button type="primary" size="large" :loading="loading" @click="send">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { chatStream, listSessions, getChatHistory, deleteChatSession } from "../api";
import VoiceInput from "../components/VoiceInput.vue";

const SESSION_KEY = "ajc_active_chat_session";

const input = ref("");
const loading = ref(false);
const loadingHistory = ref(false);
const deleting = ref(false);
const messages = ref([]);
const sessions = ref([]);
const chatBox = ref(null);
// 会话 id 持久化到 localStorage：切页面/刷新不丢
const sessionId = ref(localStorage.getItem(SESSION_KEY) || "chat-" + Date.now());

function sessionLabel(s) {
  const t = new Date((s.updated_at || 0) * 1000);
  const time = isNaN(t) ? "" : t.toLocaleString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
  return `${s.preview || "新会话"} · ${s.message_count} 条${time ? " · " + time : ""}`;
}

function persistSession() {
  localStorage.setItem(SESSION_KEY, sessionId.value);
}

function onVoiceText(text) {
  // 语音识别结果追加到输入框（与已有文本之间补空格）
  const t = (text || "").trim();
  if (!t) return;
  input.value = input.value ? input.value.replace(/\s+$/, "") + " " + t : t;
}

async function scrollBottom() {
  await nextTick();
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight;
}

async function loadSessions() {
  try {
    const r = await listSessions();
    sessions.value = r.data.items || [];
  } catch {
    sessions.value = [];
  }
}

async function loadHistory(sid) {
  loadingHistory.value = true;
  try {
    const r = await getChatHistory(sid);
    messages.value = (r.data.messages || []).map((m) => ({
      role: m.role === "assistant" ? "ai" : "user",
      content: m.content || "",
      tools: m.tools || [],
    }));
    await scrollBottom();
  } catch {
    messages.value = [];
  } finally {
    loadingHistory.value = false;
  }
}

function newSession() {
  sessionId.value = "chat-" + Date.now();
  messages.value = [];
  persistSession();
}

async function switchSession(sid) {
  sessionId.value = sid;
  persistSession();
  await loadHistory(sid);
}

async function removeSession() {
  if (!sessionId.value) return;
  await ElMessageBox.confirm(
    `确认删除会话「${sessionId.value.slice(0, 16)}…」？历史记录不可恢复。`,
    "删除确认",
    { type: "warning" }
  );
  deleting.value = true;
  try {
    await deleteChatSession(sessionId.value);
    sessions.value = sessions.value.filter((s) => s.session_id !== sessionId.value);
    ElMessage.success("会话已删除");
    newSession();
    loadSessions();
  } finally {
    deleting.value = false;
  }
}

async function ask(q) {
  input.value = q;
  await send();
}

async function send() {
  const q = input.value.trim();
  if (!q || loading.value) return;
  input.value = "";
  messages.value.push({ role: "user", content: q });
  const ai = { role: "ai", content: "", tools: [] };
  messages.value.push(ai);
  loading.value = true;
  await scrollBottom();

  try {
    await chatStream(q, sessionId.value, (event, data) => {
      if (event === "tool_call") {
        if (!ai.tools.includes(data.data)) ai.tools.push(data.data);
      } else if (event === "content") {
        ai.content += data.data;
      } else if (event === "error") {
        ai.content = "出错了：" + data.data;
      }
      scrollBottom();
    });
  } catch (e) {
    ai.content = "请求失败：" + e.message;
  }
  loading.value = false;
  scrollBottom();
  // 消息落库后刷新会话列表（首条摘要/消息数）
  loadSessions();
}

onMounted(async () => {
  await loadSessions();
  // 当前会话已存在（历史会话）→ 恢复消息；否则视为新会话留空
  if (sessions.value.some((s) => s.session_id === sessionId.value)) {
    await loadHistory(sessionId.value);
  }
});
</script>

<style scoped>
.chat-view { display: flex; flex-direction: column; height: 100%; }
.session-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.session-id { color: #9ca3af; font-size: 12px; margin-left: auto; }
.chat-box {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}
.welcome { text-align: center; padding-top: 60px; color: #6b7280; }
.welcome h3 { margin-bottom: 12px; color: #111827; }
.sug { margin: 6px; cursor: pointer; }
.msg-row { margin-bottom: 16px; display: flex; }
.msg-row.user { justify-content: flex-end; }
.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #eef2ff;
  color: #111827;
  white-space: pre-wrap;
  line-height: 1.7;
}
.msg-row.user .bubble { background: #2563eb; color: #fff; }
.bubble.ai { background: #f3f4f6; }
.tools { margin-bottom: 8px; }
.tools .el-tag { margin-right: 6px; }
.input-bar { display: flex; gap: 12px; padding: 16px 0 4px; }
</style>
