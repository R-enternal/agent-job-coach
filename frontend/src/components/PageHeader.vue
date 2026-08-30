<script setup lang="ts">
defineProps<{ title: string; desc?: string }>();
</script>

<template>
  <div class="mb-8 flex items-start justify-between gap-4">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ title }}</h1>
      <p v-if="desc" class="mt-2 text-base text-slate-500">{{ desc }}</p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
