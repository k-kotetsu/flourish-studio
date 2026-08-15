import { createRouter, createWebHistory } from "vue-router";
import PlaceholderView from "../views/PlaceholderView.vue";
import ComponentGalleryView from "../views/ComponentGalleryView.vue";
import S11View from "../views/S-11.vue";
import S12View from "../views/S-12.vue";

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
      // ファイル名は画面IDに合わせる(dev-environment.md 8章「web/src/views/のファイル名を画面IDにする」)
      path: "/s-11",
      name: "s-11",
      component: S11View,
    },
    {
      // 4領域共通の1画面。:areaで領域を切り替える(Career→Financial→Physical→Socialの順)
      path: "/s-12/:area",
      name: "s-12",
      component: S12View,
    },
    {
      // Storybook相当の内部確認用画面（P1-16の完了条件）。ユーザー導線には出さない
      path: "/_gallery",
      name: "component-gallery",
      component: ComponentGalleryView,
    },
  ],
});
