<script setup lang="ts">
/**
 * S-62 Weekly Reflection：生成中。04_画面設計(screen-list.md S-62)、07_デザイン原則7.4、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.6 / mockup.html s62())。
 * 画面到達時に`POST /reflections`→ジョブ完了待ち→`GET /reflections/{id}`まで一気に行い、
 * 成功したら結果をストアへ保存してS-63へ、失敗したら同じ画面の中身をエラー表示に入れ替える
 * (別画面へ遷移しない・自動リトライしない、S-15と同じ設計)。
 *
 * 【判断】ヘッダーはプログレスバーを持たない(wireframe-spec.md 7.6「S-62 生成中 |
 * このフローだけプログレスバーがない（1画面で完結するため）」、mockup.html `waiting()`の
 * `hdr()`呼び出しに`pct`が渡っていないことと一致)。S-13/S-15/S-33/S-53が使う
 * `AppHeaderFlow`はバー表示が前提のため使わず、`AppHeaderSingle`に`leftAction="none"`
 * (本タスクで追加)を渡して見出しのみを表示する。
 */
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { generateReflection } from "../api/reflections";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import { useReflectionAnswersStore } from "../stores/reflectionAnswers";
import { useReflectionResultStore } from "../stores/reflectionResult";

const router = useRouter();
const answersStore = useReflectionAnswersStore();
const resultStore = useReflectionResultStore();

const failed = ref(false);
let controller: AbortController | null = null;

async function generate(): Promise<void> {
  failed.value = false;
  controller = new AbortController();
  try {
    const result = await generateReflection(
      answersStore.statuses,
      answersStore.note,
      controller.signal,
    );
    resultStore.setResult(result);
    router.push("/s-63");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
  }
}

onMounted(() => {
  // S-61を経ずに直接開かれた場合など、回答が無ければS-61からやり直す
  if (answersStore.statuses.length === 0) {
    router.replace("/s-61");
    return;
  }
  generate();
});

onUnmounted(() => {
  controller?.abort();
});

function backToAnswers(): void {
  router.push("/s-61");
}
</script>

<template>
  <div class="s62">
    <AppHeaderSingle
      title="振り返り"
      left-action="none"
    />
    <GeneratingScreen
      message="選んでくださった内容と書いてくださったことを、まとめて読んでいます。"
      :failed="failed"
      error-title="うまくまとめられませんでした"
      error-message="通信の状態を確かめて、もう一度試してみてください。回答は、ちゃんと残っています。"
      back-label="回答に戻る"
      @retry="generate"
      @back="backToAnswers"
    />
  </div>
</template>

<style scoped>
.s62 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
