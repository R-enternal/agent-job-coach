<script setup lang="ts">
withDefaults(defineProps<{ color?: string }>(), { color: "blue" });

const COLORS: Record<string, string> = {
  blue: "bg-brand-50 text-brand-700",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  gray: "bg-slate-100 text-slate-600",
  red: "bg-rose-50 text-rose-700",
  violet: "bg-violet-50 text-violet-700",
};
</script>

<template>
  <span
    class="inline-flex items-center rounded-full px-3 py-0.5 text-sm font-medium"
    :class="COLORS[color] || COLORS.blue"
  >
    <slot />
  </span>
</template>
