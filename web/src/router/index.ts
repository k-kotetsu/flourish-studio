import { createRouter, createWebHistory } from "vue-router";
import PlaceholderView from "../views/PlaceholderView.vue";
import ComponentGalleryView from "../views/ComponentGalleryView.vue";
import S02View from "../views/S-02.vue";
import S11View from "../views/S-11.vue";
import S12View from "../views/S-12.vue";
import S13View from "../views/S-13.vue";
import S14View from "../views/S-14.vue";
import S15View from "../views/S-15.vue";
import S16View from "../views/S-16.vue";
import S31View from "../views/S-31.vue";
import S32View from "../views/S-32.vue";
import S33View from "../views/S-33.vue";
import S34View from "../views/S-34.vue";
import S35View from "../views/S-35.vue";
import S36View from "../views/S-36.vue";
import S37View from "../views/S-37.vue";
import S50View from "../views/S-50.vue";

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
      path: "/s-02",
      name: "s-02",
      component: S02View,
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
      path: "/s-13",
      name: "s-13",
      component: S13View,
    },
    {
      path: "/s-14",
      name: "s-14",
      component: S14View,
    },
    {
      path: "/s-15",
      name: "s-15",
      component: S15View,
    },
    {
      path: "/s-16",
      name: "s-16",
      component: S16View,
    },
    {
      // S-21(登録)はまだ実装されていないため、この画面への実際の遷移元はまだ無い
      path: "/s-31",
      name: "s-31",
      component: S31View,
    },
    {
      path: "/s-32",
      name: "s-32",
      component: S32View,
    },
    {
      path: "/s-33",
      name: "s-33",
      component: S33View,
    },
    {
      path: "/s-34",
      name: "s-34",
      component: S34View,
    },
    {
      path: "/s-35",
      name: "s-35",
      component: S35View,
    },
    {
      path: "/s-36",
      name: "s-36",
      component: S36View,
    },
    {
      path: "/s-37",
      name: "s-37",
      component: S37View,
    },
    {
      // S-51(P4-2)・S-41(P4-8)はまだ実装されていないため、S-50からの遷移先ルートはまだ無い
      path: "/s-50",
      name: "s-50",
      component: S50View,
    },
    {
      // Storybook相当の内部確認用画面（P1-16の完了条件）。ユーザー導線には出さない
      path: "/_gallery",
      name: "component-gallery",
      component: ComponentGalleryView,
    },
  ],
});
