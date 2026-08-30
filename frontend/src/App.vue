<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
import { Briefcase, Home as HomeIcon, MessageSquare, Library, Mic2 } from "lucide-vue-next";

const NAV = [
  { to: "/", label: "首页", icon: HomeIcon, end: true },
  { to: "/chat", label: "知识问答", icon: MessageSquare, end: false },
  { to: "/library", label: "资料库", icon: Library, end: false },
  { to: "/interview", label: "模拟面试", icon: Mic2, end: false },
];
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[#f7f8fa]">
    <!-- 左侧固定侧栏 -->
    <aside class="flex w-64 shrink-0 flex-col border-r border-slate-200/60 bg-white">
      <RouterLink to="/" class="flex h-[4.5rem] items-center gap-3 border-b border-slate-100 px-6">
        <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
          <Briefcase class="h-5 w-5" />
        </span>
        <span>
          <span class="block text-base font-semibold leading-tight tracking-tight text-slate-900">Agent Job Coach</span>
          <span class="mt-0.5 block text-xs leading-tight text-slate-400">AI 求职陪练</span>
        </span>
      </RouterLink>
      <nav class="flex-1 space-y-1.5 overflow-y-auto p-4">
        <RouterLink
          v-for="n in NAV"
          :key="n.to"
          :to="n.to"
          custom
          v-slot="{ route, navigate, isActive, isExactActive }"
        >
          <a
            :href="route.href"
            class="flex h-12 items-center gap-3 rounded-xl px-4 text-base transition"
            :class="(n.end ? isExactActive : isActive)
              ? 'bg-brand-50 font-medium text-brand-700'
              : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'"
            @click="navigate"
          >
            <component :is="n.icon" class="h-5 w-5" />
            {{ n.label }}
          </a>
        </RouterLink>
      </nav>
      <p class="border-t border-slate-100 px-6 py-3.5 text-xs text-slate-300">v3.0 · 题单化面试陪练</p>
    </aside>

    <!-- 右侧全高内容区（各页面自管内部滚动） -->
    <main class="h-full min-w-0 flex-1">
      <RouterView />
    </main>
  </div>
</template>
