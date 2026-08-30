<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{ variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "md" | "sm" }>(),
  { variant: "primary", size: "md" }
);

const VARIANTS: Record<string, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40",
  secondary: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40",
  ghost: "text-slate-500 hover:bg-slate-100 hover:text-slate-700",
  danger: "border border-rose-100 text-rose-500 hover:bg-rose-50",
};

const cls = computed(() => {
  const s = props.size === "sm" ? "h-9 px-3.5 text-sm" : "h-11 px-5 text-base";
  return `inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:cursor-not-allowed ${s} ${VARIANTS[props.variant]}`;
});
</script>

<template>
  <button :class="cls"><slot /></button>
</template>
