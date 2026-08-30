<script setup lang="ts">
defineProps<{ modelValue?: string | number }>();
const emit = defineEmits<{ (e: "update:modelValue", v: string): void }>();
const onChange = (e: Event) => emit("update:modelValue", (e.target as HTMLSelectElement).value);
</script>

<template>
  <select
    :value="modelValue"
    class="h-11 rounded-xl border border-slate-200/80 bg-white px-3.5 text-base text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10"
    @change="onChange"
  >
    <slot />
  </select>
</template>
