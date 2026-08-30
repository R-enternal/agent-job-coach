<script setup lang="ts">
defineProps<{ modelValue?: string }>();
const emit = defineEmits<{ (e: "update:modelValue", v: string): void }>();
const onInput = (e: Event) => emit("update:modelValue", (e.target as HTMLTextAreaElement).value);
</script>

<template>
  <textarea
    :value="modelValue"
    class="w-full rounded-xl border border-slate-200/80 bg-white px-4 py-3 text-base leading-relaxed text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 disabled:bg-slate-50"
    @input="onInput"
  />
</template>
