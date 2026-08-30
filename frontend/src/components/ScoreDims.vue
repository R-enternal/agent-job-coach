<script setup lang="ts">
import { DIM_LABELS } from "../lib/types";

defineProps<{ dims?: Record<string, number> | null }>();

const ENTRIES = Object.entries(DIM_LABELS);
</script>

<template>
  <div v-if="dims && Object.keys(dims).length" class="flex flex-wrap justify-center gap-2">
    <template v-for="[k, label] in ENTRIES" :key="k">
      <span
        v-if="dims[k] != null"
        class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
      >
        {{ label }} <b class="text-slate-900">{{ dims[k] }}</b>
      </span>
    </template>
  </div>
</template>
