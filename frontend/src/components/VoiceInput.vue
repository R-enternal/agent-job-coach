<template>
  <el-button-group class="voice-input">
    <el-tooltip
      :content="unsupported ? '当前浏览器不支持语音输入，推荐 Chrome / Edge' : (recording ? '点击停止识别' : '语音输入')"
      placement="top"
    >
      <el-button :type="recording ? 'danger' : 'default'" :disabled="unsupported" @click="toggle">
        <el-icon><Microphone /></el-icon>
        {{ recording ? "停止" : "语音" }}
      </el-button>
    </el-tooltip>
    <el-tooltip content="切换识别语言（中/英）" placement="top">
      <el-button :disabled="unsupported || recording" class="lang-btn" @click="switchLang">
        {{ lang === "zh-CN" ? "中" : "EN" }}
      </el-button>
    </el-tooltip>
  </el-button-group>
</template>

<script setup>
import { onBeforeUnmount, ref } from "vue";
import { ElMessage } from "element-plus";
import { Microphone } from "@element-plus/icons-vue";

// 语音输入（Web Speech API）：识别文本通过 text 事件抛给父组件。
// 健壮性：start 异常兜底、interimResults 让识别结果及时出现（只取最终句）、
// 停止即时复位 + abort 兜底（onend 不触发也能关）、无识别/无权限给明确提示。
const emit = defineEmits(["text"]);

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const unsupported = !SpeechRecognition;
const recording = ref(false);
const lang = ref("zh-CN");
let recognizer = null;
let stopFallbackTimer = null;
let noResultTimer = null;

function switchLang() {
  lang.value = lang.value === "zh-CN" ? "en-US" : "zh-CN";
}

function clearTimers() {
  if (stopFallbackTimer) { clearTimeout(stopFallbackTimer); stopFallbackTimer = null; }
  if (noResultTimer) { clearTimeout(noResultTimer); noResultTimer = null; }
}

function stopNow() {
  // 立即复位（按钮马上可点），再 stop()，onend 未触发则 1 秒后 abort() 兜底
  recording.value = false;
  clearTimers();
  try { recognizer?.stop(); } catch { /* ignore */ }
  stopFallbackTimer = setTimeout(() => {
    try { recognizer?.abort(); } catch { /* ignore */ }
    recognizer = null;
    stopFallbackTimer = null;
  }, 1000);
}

function toggle() {
  if (unsupported) {
    ElMessage.warning("当前浏览器不支持语音输入，推荐 Chrome / Edge");
    return;
  }
  if (recording.value) {
    stopNow();
    return;
  }
  let rec;
  try {
    rec = new SpeechRecognition();
  } catch (e) {
    ElMessage.warning("无法启动语音识别：" + (e.message || e));
    return;
  }
  recognizer = rec;
  rec.lang = lang.value;
  rec.continuous = true;      // 长作答可持续识别
  rec.interimResults = true;  // 打开中间结果，识别更快出现；下方只取 isFinal
  let gotAnyResult = false;
  rec.onresult = (e) => {
    gotAnyResult = true;
    if (noResultTimer) { clearTimeout(noResultTimer); noResultTimer = null; }
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i];
      if (r.isFinal && r[0] && r[0].transcript) emit("text", r[0].transcript);
    }
  };
  rec.onerror = (e) => {
    if (e.error === "not-allowed") {
      ElMessage.error("麦克风权限被拒绝，请在浏览器地址栏允许麦克风后重试");
    } else if (e.error === "no-speech") {
      if (!gotAnyResult) ElMessage.warning("没有听到声音，请靠近麦克风或检查是否静音");
    } else if (e.error !== "aborted" && e.error !== "no-speech") {
      ElMessage.warning("语音识别异常：" + e.error);
    }
    recording.value = false;
  };
  rec.onend = () => {
    recording.value = false;
    clearTimers();
  };
  try {
    rec.start();
  } catch (e) {
    ElMessage.warning("语音识别启动失败：" + (e.message || e));
    recording.value = false;
    recognizer = null;
    return;
  }
  recording.value = true;
  // 10 秒无任何识别结果给提示（持续监听不中断）
  noResultTimer = setTimeout(() => {
    if (recording.value && !gotAnyResult) {
      ElMessage.info("正在聆听…如果一直没反应，请检查麦克风权限");
    }
    noResultTimer = null;
  }, 10000);
}

onBeforeUnmount(() => {
  clearTimers();
  try { recognizer?.abort(); } catch { /* ignore */ }
  recognizer = null;
});
</script>

<style scoped>
.voice-input { flex: none; }
.lang-btn { min-width: 44px; }
</style>
