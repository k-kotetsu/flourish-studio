<script setup lang="ts">
/**
 * S-53 領域：3案生成中。04_画面設計(screen-list.md S-53)、07_デザイン原則7.4、
 * 06_ワイヤーフレーム(wireframe-spec.md 6章、mockup.html s53())。
 *
 * 画面到達時に`POST /ai/area-proposals`を呼び、成功したら結果をストアへ保存してS-54へ、
 * 失敗したら同じ画面の中身をエラー表示に入れ替える(別画面へ遷移しない・自動リトライしない、
 * S-33〔P3-7〕と同じ構成)。
 *
 * **バーは直前のステップ(S-52、2/5=40%)の位置で止め、ステップ番号は出さない。**
 * wireframe-spec.md 1.1の表(S-53: step「なし」)・48行目の一般則
 * (「生成中画面(...S-53...)はステップ番号を出さない」)、およびmockup.html s53()の
 * `pct:40`をそのまま採用した。6章本文の見出し「戻るなし＋プログレス（3 / 5）」は
 * この一般則・表・mockupと食い違うが、S-33が同種の食い違いを解決した判断
 * (直前のステップの位置で止める)をそのまま踏襲した。
 */
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { generateAreaProposals } from "../api/areaProposals";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";
import { useAreaProposalsStore } from "../stores/areaProposals";

const route = useRoute();
const router = useRouter();
const choicesStore = useAreaChoicesStore();
const dialogueStore = useAreaDialogueStore();
const proposalsStore = useAreaProposalsStore();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const failed = ref(false);
let controller: AbortController | null = null;

async function generate(): Promise<void> {
  if (!area) return;
  failed.value = false;
  controller = new AbortController();
  try {
    const result = await generateAreaProposals(
      area,
      choicesStore.asChoices,
      dialogueStore.messages,
      controller.signal,
    );
    proposalsStore.setProposals(result.proposals);
    router.push(`/s-54/${AREA_META[area].slug}`);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
  }
}

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-52と同じ判断)
    router.replace("/s-50");
    return;
  }
  // S-52を経ずに直接開かれた場合など、2往復完了していなければその領域のS-52からやり直す
  if (!dialogueStore.canCreateIdealState) {
    router.replace(`/s-52/${AREA_META[area].slug}`);
    return;
  }
  generate();
});

onUnmounted(() => {
  controller?.abort();
});

function backToDialogue(): void {
  if (!area) return;
  router.push(`/s-52/${AREA_META[area].slug}`);
}
</script>

<template>
  <div
    v-if="meta"
    class="s53"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="40"
      left-action="none"
    />
    <GeneratingScreen
      message="選んでくださった内容とここまでのお話から、3つの方向で候補を用意しています"
      :failed="failed"
      error-title="うまく候補を作れませんでした"
      error-message="通信の状態を確かめて、もう一度試してみてください。ここまでのお話は、ちゃんと残っています。"
      back-label="対話に戻る"
      @retry="generate"
      @back="backToDialogue"
    />
  </div>
</template>

<style scoped>
.s53 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
