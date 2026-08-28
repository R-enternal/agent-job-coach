<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="26"><Briefcase /></el-icon>
        <span>Agent Job Coach</span>
      </div>
      <div class="subtitle">AI 求职智能助手</div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item v-for="r in routes" :key="r.path" :index="r.path">
          <el-icon><component :is="r.meta.icon" /></el-icon>
          <span>{{ r.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ $route.meta.title }}</span>
        <span class="tag">FastAPI · LangGraph · Vue3</span>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from "vue-router";
import { Briefcase } from "@element-plus/icons-vue";

const router = useRouter();
const routes = router.options.routes.filter((r) => r.path !== "/");
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
.layout { height: 100%; }
.aside {
  background: #1f2937;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px 0;
  font-size: 22px;
  font-weight: 700;
  color: #7dd3fc;
}
.subtitle {
  padding: 4px 20px 20px;
  font-size: 12px;
  color: #9ca3af;
}
.menu {
  border-right: none;
  background: transparent;
  --el-menu-text-color: #d1d5db;
  --el-menu-hover-bg-color: #374151;
  --el-menu-active-color: #7dd3fc;
  --el-menu-bg-color: transparent;
}
.menu .el-menu-item.is-active { background: #374151; }
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.page-title { font-size: 18px; font-weight: 600; color: #111827; }
.tag {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 12px;
  border-radius: 12px;
}
.main { background: #f9fafb; }
</style>
