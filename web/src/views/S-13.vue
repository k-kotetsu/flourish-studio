<script setup lang="ts">
/**
 * S-13 自由記述の問い生成中。04_画面設計(screen-list.md S-13)、07_デザイン原則7.4。
 * 画面到達時に`POST /ai/assessment-questions`を呼び、成功したら結果をストアへ保存してS-14へ、
 * 失敗したら同じ画面の中身をエラー表示に入れ替える(別画面へ遷移しない・自動リトライしない)。
 */
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { generateAssessmentQuestions } from "../api/assessmentQuestions";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import { CURRENT_QUESTION_SET_VERSION } from "../domain/questions";
import { useAssessmentAnswersStore } from "../stores/assessmentAnswers";
import { useAssessmentQuestionsStore } from "../stores/assessmentQuestions";

const router = useRouter();
const answersStore = useAssessmentAnswersStore();
const questionsStore = useAssessmentQuestionsStore();

const failed = ref(false);
let controller: AbortController | null = null;

async function generate(): Promise<void> {
  failed.value = false;
  controller = new AbortController();
  try {
    const questions = await generateAssessmentQuestions(
      answersStore.scaleAnswers,
      CURRENT_QUESTION_SET_VERSION,
      controller.signal,
    );
    questionsStore.setQuestions(questions);
    router.push("/s-14");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
  }
}

onMounted(() => {
  // S-12を経ずに直接開かれた場合など、24件揃っていなければS-11からやり直す
  if (answersStore.scaleAnswers.length !== 24) {
    router.replace("/s-11");
    return;
  }
  generate();
});

onUnmounted(() => {
  controller?.abort();
});

function backToAnswers(): void {
  // 直前まで回答していたSocialへ戻す(仕様は「S-12へ」とのみ定め、4領域中どこかまでは
  // 明記していない判断。もう一度見直す対象は直前に完了した領域が自然なため、この選択とした)
  router.push("/s-12/social");
}
</script>

<template>
  <div class="s13">
    <AppHeaderFlow
      title="現在地レポート"
      :percent="67"
      left-action="none"
    />
    <GeneratingScreen
      message="あなたに合わせた質問を用意しています"
      :failed="failed"
      error-title="うまく読み取れませんでした"
      error-message="通信の状態を確かめて、もう一度試してみてください。選んでいただいた内容は、ちゃんと残っています。"
      back-label="回答に戻る"
      @retry="generate"
      @back="backToAnswers"
    />
  </div>
</template>

<style scoped>
.s13 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
