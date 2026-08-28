<template>
  <div class="chat-view">
    <div class="chat-box" ref="chatBox">
      <div class="welcome" v-if="!messages.length">
        <h3>👋 欢迎使用 Agent Job Coach 知识问答</h3>
        <p>你可以问我：</p>
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
import { ref, nextTick } from "vue";
import { chatStream } from "../api";
import VoiceInput from "../components/VoiceInput.vue";

const input = ref("");
const loading = ref(false);
const messages = ref([]);
const chatBox = ref(null);
const sessionId = "chat-" + Date.now();

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
    await chatStream(q, sessionId, (event, data) => {
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
}
</script>

<style scoped>
.chat-view { display: flex; flex-direction: column; height: 100%; }
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
