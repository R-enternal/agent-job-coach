import { createRouter, createWebHistory } from "vue-router";

import ChatView from "../views/ChatView.vue";
import InterviewView from "../views/InterviewView.vue";
import ProjectView from "../views/ProjectView.vue";
import JdMatchView from "../views/JdMatchView.vue";
import AssetsView from "../views/AssetsView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/chat" },
    { path: "/chat", component: ChatView, meta: { title: "知识问答", icon: "ChatDotRound" } },
    { path: "/assets", component: AssetsView, meta: { title: "素材库", icon: "Collection" } },
    { path: "/jd", component: JdMatchView, meta: { title: "JD 定制", icon: "DataAnalysis" } },
    { path: "/interview", component: InterviewView, meta: { title: "模拟面试", icon: "Microphone" } },
    { path: "/project", component: ProjectView, meta: { title: "项目深挖", icon: "FolderOpened" } },
  ],
});

export default router;
