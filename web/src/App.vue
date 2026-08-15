<script setup lang="ts">
import { useRoute } from "vue-router";

// ルートパラメータが変わるだけ(例: /s-12/career → /s-12/financial)では
// 既定でコンポーネントが使い回される。S-12のように「戻る」がなく前へ進むだけの
// 画面では、その使い回しが答えの残留につながるためfullPathをkeyにして必ず作り直す。
const route = useRoute();
</script>

<template>
  <router-view :key="route.fullPath" />
</template>
