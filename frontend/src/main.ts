import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import Home from "./pages/Home.vue";
import Chat from "./pages/Chat.vue";
import LibraryPage from "./pages/Library.vue";
import Interview from "./pages/Interview.vue";
import "./index.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Home },
    { path: "/chat", component: Chat },
    { path: "/library", component: LibraryPage },
    { path: "/interview", component: Interview },
    { path: "/:pathMatch(.*)*", component: Home },
  ],
});

createApp(App).use(router).mount("#app");
