import { createRouter, createWebHistory } from "vue-router";
import PlaceholderView from "../views/PlaceholderView.vue";

// SPAは "/app/*" 配下でCloudFrontから配信される(infra/lib/edge-stack.ts)。
// ビルド成果物のアセットURLもこのbaseに合わせる必要がある(vite.config.tsのbaseと対で決める)。
const BASE_URL = "/app/";

export const router = createRouter({
  history: createWebHistory(BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: PlaceholderView,
    },
  ],
});
