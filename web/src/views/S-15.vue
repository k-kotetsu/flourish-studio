<script setup lang="ts">
/**
 * S-15 現在地レポート生成中。04_画面設計(screen-list.md S-15)、07_デザイン原則7.4。
 * 画面到達時に`POST /assessments`→ジョブ完了待ち→`GET /assessments/{id}`まで一気に行い、
 * 成功したら結果をストアへ保存してS-16へ、失敗したら同じ画面の中身をエラー表示に入れ替える
 * (別画面へ遷移しない・自動リトライしない)。
 * S-16は「AI生成が成功した場合のみ到達する画面」で状態バリエーションを持たない
 * (06_ワイヤーフレーム3章)ため、結果取得の失敗もここで扱い、S-16には成功時だけ進む判断とした。
 */
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { generateAssessmentReport } from "../api/assessments";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import { CURRENT_QUESTION_SET_VERSION } from "../domain/questions";
import { useAssessmentAnswersStore } from "../stores/assessmentAnswers";
import { useAssessmentResultStore } from "../stores/assessmentResult";
import { useFreeTextAnswersStore } from "../stores/freeTextAnswers";

const router = useRouter();
const answersStore = useAssessmentAnswersStore();
const freeTextStore = useFreeTextAnswersStore();
const resultStore = useAssessmentResultStore();

const failed = ref(false);
let controller: AbortController | null = null;

async function generate(): Promise<void> {
  failed.value = false;
  controller = new AbortController();
  try {
    const result = await generateAssessmentReport(
      answersStore.scaleAnswers,
      freeTextStore.answers,
      CURRENT_QUESTION_SET_VERSION,
      controller.signal,
    );
    resultStore.setResult(result);
    router.push("/s-16");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
  }
}

onMounted(() => {
  // S-14を経ずに直接開かれた場合など、揃っていなければS-11からやり直す
  if (answersStore.scaleAnswers.length !== 24 || freeTextStore.answers.length !== 8) {
    router.replace("/s-11");
    return;
  }
  generate();
});

onUnmounted(() => {
  controller?.abort();
});

function backToAnswers(): void {
  router.push("/s-14");
}
</script>

<template>
  <div class="s15">
    <AppHeaderFlow
      title="現在地レポート"
      :percent="83"
      left-action="none"
    />
    <GeneratingScreen
      message="4つの領域それぞれについて、いまの状態を整理しています"
      :failed="failed"
      error-title="うまくレポートを作れませんでした"
      error-message="通信の状態を確かめて、もう一度試してみてください。書いていただいた内容は、ちゃんと残っています。"
      back-label="回答に戻る"
      @retry="generate"
      @back="backToAnswers"
    />
  </div>
</template>

<style scoped>
.s15 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
