<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from "vue";
import { Plus, Trash2, Send } from "lucide-vue-next";
import { chatStream, deleteChatSession, getChatHistory, listSessions } from "../api";
import { ChatMessage, Session } from "../lib/types";
import Empty from "../components/Empty.vue";
import UButton from "../components/UButton.vue";
import UTag from "../components/UTag.vue";
import VoiceInput from "../components/VoiceInput.vue";

const SESSION_KEY = "ajc_active_chat_session";
const EXAMPLES = ["什么是 LangGraph 状态图？", "RAG 为什么用 RRF 融合？", "仓维云项目有什么亮点？"];

const sessionId = ref(localStorage.getItem(SESSION_KEY) || `chat-${Date.now()}`);
const sessions = ref<Session[]>([]);
const messages = ref<ChatMessage[]>([]);
const input = ref("");
const loading = ref(false);
const boxRef = ref<HTMLDivElement | null>(null);

const scrollBottom = () =>
  nextTick(() => {
    if (boxRef.value) boxRef.value.scrollTop = boxRef.value.scrollHeight;
  });

const reloadSessions = () =>
  listSessions()
    .then((r) => (sessions.value = r.data.items || []))
    .catch(() => {});

const loadHistory = async (sid: string) => {
  try {
    const r = await getChatHistory(sid);
    messages.value = (r.data.messages || []).map((m: any) => ({
      role: m.role === "assistant" ? "ai" : "user",
      content: m.content || "",
      tools: m.tools || [],
    }));
  } catch {
    messages.value = [];
  }
  scrollBottom();
};

const switchSession = (sid: string) => {
  sessionId.value = sid;
  localStorage.setItem(SESSION_KEY, sid);
  loadHistory(sid);
};

const newSession = () => {
  const sid = `chat-${Date.now()}`;
  sessionId.value = sid;
  localStorage.setItem(SESSION_KEY, sid);
  messages.value = [];
};

const removeSession = async () => {
  if (!confirm("删除当前会话？历史记录不可恢复。")) return;
  await deleteChatSession(sessionId.value);
  sessions.value = sessions.value.filter((x) => x.session_id !== sessionId.value);
  newSession();
  reloadSessions();
};

const send = async () => {
  const q = input.value.trim();
  if (!q || loading.value) return;
  input.value = "";
  // AI 气泡需要流式追加内容，必须用 reactive 对象才能触发模板更新
  const ai = reactive<ChatMessage>({ role: "ai", content: "", tools: [] });
  messages.value.push({ role: "user", content: q }, ai);
  loading.value = true;
  scrollBottom();
  try {
    await chatStream(q, sessionId.value, (event, data) => {
      if (event === "tool_call") {
        ai.tools = ai.tools || [];
        if (!ai.tools.includes(data.data)) ai.tools.push(data.data);
      } else if (event === "content") {
        ai.content += data.data;
      } else if (event === "error") {
        ai.content = "出错了：" + data.data;
      }
      scrollBottom();
    });
  } catch (e: any) {
    ai.content = "请求失败：" + e.message;
    input.value = q; // 失败回填输入框，避免用户重打
  }
  loading.value = false;
  reloadSessions();
};

const onEnter = (e: KeyboardEvent) => {
  if (e.isComposing) return; // 中文输入法组词中，回车是选词而非发送
  send();
};

const onVoice = (t: string) => {
  input.value = input.value ? input.value.replace(/\s+$/, "") + " " + t : t;
};

onMounted(async () => {
  await reloadSessions();
  if (sessions.value.some((s) => s.session_id === sessionId.value)) loadHistory(sessionId.value);
});
</script>

<template>
  <div class="flex h-full gap-6 p-7">
    <!-- 左：会话列表 -->
    <aside class="flex w-72 shrink-0 flex-col rounded-2xl border border-slate-200/60 bg-white p-4 shadow-card">
      <div class="mb-2 flex items-center justify-between px-2 pt-1.5">
        <span class="text-base font-semibold text-slate-700">会话</span>
        <button
          class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          title="新建会话"
          @click="newSession"
        >
          <Plus class="h-4 w-4" />
        </button>
      </div>
      <div class="flex-1 space-y-1.5 overflow-y-auto">
        <button
          v-for="s in sessions"
          :key="s.session_id"
          class="w-full rounded-xl px-3.5 py-3 text-left transition"
          :class="s.session_id === sessionId ? 'bg-brand-50' : 'hover:bg-slate-50'"
          @click="switchSession(s.session_id)"
        >
          <p class="truncate text-base text-slate-700">{{ s.preview || "新会话" }}</p>
          <p class="mt-0.5 text-sm text-slate-400">{{ s.message_count }} 条</p>
        </button>
        <Empty v-if="sessions.length === 0" text="暂无会话" />
      </div>
      <UButton variant="danger" size="sm" class="mt-3 w-full" @click="removeSession">
        <Trash2 class="h-4 w-4" /> 删除当前会话
      </UButton>
    </aside>

    <!-- 右：气泡对话 -->
    <div class="flex flex-1 flex-col rounded-2xl border border-slate-200/60 bg-white shadow-card">
      <div ref="boxRef" class="flex-1 space-y-5 overflow-y-auto p-7">
        <div v-if="messages.length === 0" class="flex h-full flex-col items-center justify-center gap-5 text-slate-400">
          <p class="text-base">问我求职相关问题，试试下方示例</p>
          <div class="flex flex-wrap justify-center gap-2.5">
            <button
              v-for="q in EXAMPLES"
              :key="q"
              class="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-500 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-600"
              @click="input = q"
            >
              {{ q }}
            </button>
          </div>
        </div>
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="flex"
          :class="m.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[78%] rounded-2xl px-5 py-3 text-base leading-relaxed"
            :class="m.role === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-800'"
          >
            <div v-if="m.tools && m.tools.length" class="mb-2 flex flex-wrap gap-1.5">
              <UTag v-for="t in m.tools" :key="t" color="blue">🔧 {{ t }}</UTag>
            </div>
            <p class="whitespace-pre-wrap">{{ m.content || (loading && m.role === "ai" ? "思考中…" : "") }}</p>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2.5 border-t border-slate-100 p-4">
        <VoiceInput @text="onVoice" />
        <input
          v-model="input"
          :disabled="loading"
          placeholder="输入你的求职问题，Enter 发送…"
          class="h-11 flex-1 rounded-xl border border-slate-200 px-4 text-base outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50"
          @keydown.enter="onEnter"
        />
        <UButton class="w-11 px-0" :disabled="loading || !input.trim()" @click="send">
          <Send class="h-4 w-4" />
        </UButton>
      </div>
    </div>
  </div>
</template>
