<script setup lang="ts">
import { X } from "lucide-vue-next";

defineProps<{ title: string; wide?: boolean }>();
const emit = defineEmits<{ (e: "close"): void }>();
</script>

<template>
  <div
    class="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/30 p-5 backdrop-blur-[2px]"
    @click="emit('close')"
  >
    <div
      class="max-h-[82vh] w-full overflow-y-auto rounded-2xl bg-white p-7 shadow-xl"
      :class="wide ? 'max-w-2xl' : 'max-w-lg'"
      @click.stop
    >
      <div class="mb-5 flex items-center justify-between">
        <h3 class="text-lg font-semibold text-slate-900">{{ title }}</h3>
        <button
          class="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          @click="emit('close')"
        >
          <X class="h-4 w-4" />
        </button>
      </div>
      <slot />
    </div>
  </div>
</template>
