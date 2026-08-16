<script setup lang="ts">
/**
 * S-33 ありたい姿：3案生成中。04_画面設計(screen-list.md S-33)、07_デザイン原則7.4、
 * 06_ワイヤーフレーム(wireframe-spec.md「生成中画面はステップ番号を出さない」、mockup.html s33())。
 *
 * 画面到達時に`POST /ai/purpose-proposals`を呼び、成功したら結果をストアへ保存してS-34へ、
 * 失敗したら同じ画面の中身をエラー表示に入れ替える(別画面へ遷移しない・自動リトライしない)。
 * バーは直前のステップ(S-32、2/4=50%)の位置で止める。
 */
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { generatePurposeProposals } from "../api/purposeProposals";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const router = useRouter();
const choicesStore = usePurposeChoicesStore();
const dialogueStore = usePurposeDialogueStore();
const proposalsStore = usePurposeProposalsStore();

const failed = ref(false);
let controller: AbortController | null = null;

async function generate(): Promise<void> {
  failed.value = false;
  controller = new AbortController();
  try {
    const result = await generatePurposeProposals(
      choicesStore.asChoices,
      dialogueStore.messages,
      controller.signal,
    );
    proposalsStore.setProposals(result.proposals);
    router.push("/s-34");
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
  }
}

onMounted(() => {
  // S-32を経ずに直接開かれた場合など、対話が無ければS-31からやり直す
  if (!dialogueStore.canCreateProposals) {
    router.replace("/s-31");
    return;
  }
  generate();
});

onUnmounted(() => {
  controller?.abort();
});

function backToDialogue(): void {
  router.push("/s-32");
}
</script>

<template>
  <div class="s33">
    <AppHeaderFlow
      title="ありたい姿"
      :percent="50"
      left-action="none"
    />
    <GeneratingScreen
      message="ここまでのお話から、3つの方向で候補を用意しています"
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
.s33 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>
