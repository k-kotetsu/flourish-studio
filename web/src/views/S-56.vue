<script setup lang="ts">
/**
 * S-56 領域：年間目標の設定。04_画面設計(screen-list.md S-56)、05_質問・コンテンツ設計9.6、
 * 10_AIプロンプト設計4.7(P-07 GOAL_HINTS)、09_API設計5.10・5.11、
 * 06_ワイヤーフレーム(wireframe-spec.md「S-56 年間目標 | ‹ 戻る | 領域名 | 5 / 5 | 100%」、
 * mockup.html s56()「理想の状態を上部に置く。AIは自動で提案しない。ボタンを押したときだけ
 * 候補が画面内に出る。1個で確定できる」)。
 *
 * S-51〜S-55で集めた選択式回答・対話全文・選んだ案・編集後の理想状態と、ここで入力する
 * 目標1〜3個を`POST /area-plans`でまとめて確定する(ここではじめて保存される)。
 * AIヒント(`POST /ai/goal-hints`)は画面遷移せず、押したときだけ画面内のローディングで
 * 処理する(生成中画面を挟まない、9.6の例外)。失敗しても`確定する`は止めない
 * (ユーザーは自分で書ける)。
 *
 * 【判断】目標欄は既定で2つ表示し(mockup.html s56()「2つ目（任意）」)、「＋ 目標を追加」で
 * 3つ目まで増やせる。1つ目のみ必須で、空欄は確定時に取り除く(9.6「無理に3個作らせない」)。
 * 【判断】確定成功後、この領域の作成フローで使った`areaChoices`/`areaDialogue`/`areaProposals`
 * ストアをリセットする。これらは確定前の一時状態を運ぶためだけのものであり、成果物は
 * サーバーに保存済みのため、同じ領域を作り直す(S-57「AIと話して見直す」、P4-7未実装)ときに
 * 前回の入力が残っていると混乱するため。
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { generateGoalHints } from "../api/goalHints";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";
import { useAreaProposalsStore } from "../stores/areaProposals";

const MAX_GOALS = 3;

const route = useRoute();
const router = useRouter();
const choicesStore = useAreaChoicesStore();
const dialogueStore = useAreaDialogueStore();
const proposalsStore = useAreaProposalsStore();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const hasSelectedProposal = computed(() => proposalsStore.selectedProposal !== null);
const hasEditedIdealState = computed(() => proposalsStore.editedIdealState !== null);
const idealState = computed(() => proposalsStore.editedIdealState ?? "");

const goals = ref<string[]>(["", ""]);
const canAddGoal = computed(() => goals.value.length < MAX_GOALS);
const trimmedGoals = computed(() =>
  goals.value.map((goal) => goal.trim()).filter((goal) => goal.length > 0),
);
const canConfirm = computed(
  () => trimmedGoals.value.length >= 1 && trimmedGoals.value.length <= MAX_GOALS,
);

function goalPlaceholder(index: number): string {
  if (index === 0) return "";
  return `${index + 1}つ目（任意）`;
}

function addGoal(): void {
  if (!canAddGoal.value) return;
  goals.value.push("");
}

const hintLoading = ref(false);
const hintErrorMessage = ref("");
const hints = ref<string[] | null>(null);
let hintController: AbortController | null = null;

async function requestHints(): Promise<void> {
  if (!area || hintLoading.value) return;
  hintErrorMessage.value = "";
  hintLoading.value = true;
  hintController = new AbortController();

  try {
    hints.value = await generateGoalHints(
      area,
      idealState.value,
      trimmedGoals.value,
      hintController.signal,
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    hintErrorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  } finally {
    hintLoading.value = false;
  }
}

function applyHint(hint: string): void {
  const emptyIndex = goals.value.findIndex((goal) => goal.trim().length === 0);
  if (emptyIndex !== -1) {
    goals.value[emptyIndex] = hint;
    return;
  }
  if (canAddGoal.value) {
    goals.value.push(hint);
  }
}

const confirming = ref(false);
const confirmErrorMessage = ref("");

async function confirm(): Promise<void> {
  if (!area || !canConfirm.value || confirming.value) return;
  const selectedProposal = proposalsStore.selectedProposal;
  if (!selectedProposal || !proposalsStore.selectedDirection) return;

  confirming.value = true;
  confirmErrorMessage.value = "";

  try {
    await createAreaPlan({
      area,
      choices: choicesStore.asChoices,
      messages: dialogueStore.messages,
      selected_direction: proposalsStore.selectedDirection,
      selected_label: selectedProposal.label,
      original_ideal_state: selectedProposal.ideal_state,
      ideal_state: idealState.value,
      goals: trimmedGoals.value.map((body, index) => ({ body, sort_order: index + 1 })),
    });
    choicesStore.reset();
    dialogueStore.reset();
    proposalsStore.reset();
    router.push("/s-41");
  } catch (error) {
    confirmErrorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  } finally {
    confirming.value = false;
  }
}

function goBack(): void {
  if (!area) return;
  router.push(`/s-55/${AREA_META[area].slug}`);
}

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-51/S-54/S-55と同じ判断)
    router.replace("/s-50");
    return;
  }
  if (!hasSelectedProposal.value) {
    router.replace(`/s-54/${AREA_META[area].slug}`);
    return;
  }
  if (!hasEditedIdealState.value) {
    // S-55を経ずに直接開かれた場合など、編集後の理想状態が無ければ同じ領域のS-55からやり直す
    router.replace(`/s-55/${AREA_META[area].slug}`);
  }
});

onUnmounted(() => {
  hintController?.abort();
});
</script>

<template>
  <div
    v-if="meta && hasSelectedProposal && hasEditedIdealState"
    class="s56"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="100"
      step="5 / 5"
      left-action="back"
      @back="goBack"
    />

    <div class="s56__body">
      <div class="s56__ideal-card">
        <p class="s56__ideal-label">
          {{ meta.en }}の理想の状態
        </p>
        <p class="s56__ideal-text">
          {{ idealState }}
        </p>
      </div>

      <div class="s56__question">
        <p class="s56__question-text">
          その状態に近づくために、今年取り組むことを書いてください。
          <span class="s56__question-sub">（1〜3個）</span>
        </p>

        <div
          v-for="(_goal, index) in goals"
          :key="index"
          class="s56__field"
        >
          <input
            v-model="goals[index]"
            type="text"
            class="s56__input"
            :placeholder="goalPlaceholder(index)"
            :aria-label="index === 0 ? '1つ目の目標' : `${index + 1}つ目の目標（任意）`"
          >
        </div>
      </div>

      <button
        v-if="canAddGoal"
        type="button"
        class="s56__ghost-button"
        @click="addGoal"
      >
        ＋ 目標を追加
      </button>

      <div class="s56__rule" />

      <div
        v-if="hints"
        class="s56__hints-card"
      >
        <p class="s56__hints-label">
          AIからのヒント
        </p>
        <p class="s56__hints-sub">
          例として3つ挙げてみました。そのまま使っても、書き換えても大丈夫です。
        </p>
        <button
          v-for="hint in hints"
          :key="hint"
          type="button"
          class="s56__hint-option"
          @click="applyHint(hint)"
        >
          {{ hint }}
        </button>
      </div>
      <div
        v-else
        class="s56__hint-prompt"
      >
        <p class="s56__hint-sub">
          思いつかないときは
        </p>
        <button
          type="button"
          class="s56__ghost-button"
          :disabled="hintLoading"
          @click="requestHints"
        >
          {{ hintLoading ? "考えています…" : "AIにヒントをもらう" }}
        </button>
      </div>

      <p
        v-if="hintErrorMessage"
        class="s56__error"
      >
        {{ hintErrorMessage }}
      </p>
    </div>

    <div class="s56__cta">
      <AppButton
        :disabled="!canConfirm || confirming"
        @click="confirm"
      >
        確定する
      </AppButton>
      <p
        v-if="!canConfirm"
        class="s56__hint"
      >
        目標を1つ書くと、確定できます
      </p>
      <p
        v-if="confirmErrorMessage"
        class="s56__error"
      >
        {{ confirmErrorMessage }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.s56 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s56__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s56__ideal-card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s56__ideal-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s56__ideal-text {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s56__question {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s56__question-text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s56__question-sub {
  color: var(--text-sub);
}

.s56__field {
  display: flex;
}

.s56__input {
  width: 100%;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
}

.s56__input::placeholder {
  color: var(--text-faint);
}

.s56__input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s56__ghost-button {
  align-self: center;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-button);
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-caption);
  font-weight: 500;
  cursor: pointer;
}

.s56__ghost-button:disabled {
  color: var(--text-faint);
  cursor: default;
}

.s56__ghost-button:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s56__rule {
  height: 1px;
  background: var(--border);
}

.s56__hint-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.s56__hint-sub {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s56__hints-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s56__hints-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s56__hints-sub {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s56__hint-option {
  text-align: left;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
  cursor: pointer;
}

.s56__hint-option:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s56__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s56__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s56__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
