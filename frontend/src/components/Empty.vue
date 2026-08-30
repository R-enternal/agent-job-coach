<script setup lang="ts">
import { Inbox } from "lucide-vue-next";

defineProps<{ text: string }>();
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2.5 py-10 text-slate-400">
    <Inbox class="h-7 w-7" />
    <p class="text-base">{{ text }}</p>
  </div>
</template>
