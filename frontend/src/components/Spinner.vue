<script setup lang="ts">
import { Loader2 } from "lucide-vue-next";

defineProps<{ label?: string }>();
</script>

<template>
  <div class="flex items-center justify-center gap-2 py-8 text-base text-slate-400">
    <Loader2 class="h-4 w-4 animate-spin" />
    {{ label || "加载中…" }}
  </div>
</template>
