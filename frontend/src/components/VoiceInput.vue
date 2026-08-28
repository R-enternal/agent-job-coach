<template>
  <el-button-group class="voice-input">
    <el-tooltip :content="unsupported ? '当前浏览器不支持语音输入，推荐 Chrome / Edge' : (recording ? '点击停止识别' : '语音输入')" placement="top">
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

// 语音输入（Web Speech API）：识别出的文本通过 text 事件抛给父组件追加到输入框。
// 纯前端能力，不经过后端；浏览器不支持时按钮禁用并给提示。支持 zh-CN / en-US 切换。
const emit = defineEmits(["text"]);

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const unsupported = !SpeechRecognition;
const recording = ref(false);
const lang = ref("zh-CN");
let recognizer = null;

function switchLang() {
  lang.value = lang.value === "zh-CN" ? "en-US" : "zh-CN";
}

function toggle() {
  if (unsupported) {
    ElMessage.warning("当前浏览器不支持语音输入，推荐 Chrome / Edge");
    return;
  }
  if (recording.value) {
    recognizer?.stop();
    return;
  }
  recognizer = new SpeechRecognition();
  recognizer.lang = lang.value;
  recognizer.continuous = true;      // 长作答可持续识别
  recognizer.interimResults = false; // 只取最终句，避免中间结果抖动
  recognizer.onresult = (e) => {
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) emit("text", e.results[i][0].transcript);
    }
  };
  recognizer.onerror = (e) => {
    if (e.error === "not-allowed") {
      ElMessage.error("麦克风权限被拒绝，请在浏览器地址栏允许麦克风");
    } else if (e.error !== "aborted") {
      ElMessage.warning("语音识别异常：" + e.error);
    }
    recording.value = false;
  };
  recognizer.onend = () => {
    recording.value = false;
  };
  recognizer.start();
  recording.value = true;
}

onBeforeUnmount(() => {
  recognizer?.abort();
});
</script>

<style scoped>
.voice-input { flex: none; }
.lang-btn { min-width: 44px; }
</style>
