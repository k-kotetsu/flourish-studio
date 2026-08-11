import { createRouter, createWebHistory } from "vue-router";
import PlaceholderView from "../views/PlaceholderView.vue";
import ComponentGalleryView from "../views/ComponentGalleryView.vue";

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
    {
      // Storybook相当の内部確認用画面（P1-16の完了条件）。ユーザー導線には出さない
      path: "/_gallery",
      name: "component-gallery",
      component: ComponentGalleryView,
    },
  ],
});
