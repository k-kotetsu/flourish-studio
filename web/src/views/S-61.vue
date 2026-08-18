<script setup lang="ts">
/**
 * S-61 Weekly Reflection：回答。04_画面設計(screen-list.md S-61)、
 * 05_質問・コンテンツ設計10.1〜10.2、09_API設計5.13、
 * 06_ワイヤーフレーム(wireframe-spec.md「S-61 WR回答 | × 中断 | 振り返り | − | −」、
 * mockup.html s61()「3段階を横並びのセグメントに変更。領域はアイコン＋小さな英字ラベルで
 * 示し、目標文より弱くする」)。
 *
 * `GET /reflections/context`で回答対象の目標一覧を取得する(目標0件でも200＋空配列、409にしない)。
 * 保存はせず(スキルflourish-api「入力途中を送らない」)、送信ボタンで`reflectionAnswers`ストアに
 * 入れてS-62へ渡す(S-14→S-15と同じ設計。実際の`POST /reflections`はS-62側＝P5-2で行う)。
 *
 * 【判断】ヘッダーは「‹ 戻る」ではなく「× 中断」だがプログレスバーは無い、という
 * AppHeaderFlow/AppHeaderSingleのどちらにも無かった組み合わせのため、AppHeaderSingleに
 * `leftAction`（既定`back`）を追加して`cancel`を選べるようにした(既存呼び出し元の見た目は
 * 変わらない)。中断はInterruptDialogを必ず挟む(7.2、S-51と同じ設計)。
 * 【判断】4領域アイコン自体はP7-3が未着手のため、mockup.htmlの「小さな英字ラベル」部分のみを
 * 採用し、アイコンは付けない(S-41が確立した扱いを踏襲)。
 * 【判断】直接URLで開かれるなどして目標が0件だった場合、screen-list.mdの前提「目標が1個以上
 * あること」を満たさないため、この画面フローの入口であるS-41へ`router.replace`する
 * (未知の領域パラメータをS-50へ戻すS-51/S-54/S-55と同じ考え方)。
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getReflectionContext, type ReflectionGoal } from "../api/reflections";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import InterruptDialog from "../components/InterruptDialog.vue";
import { AREA_META } from "../domain/questions";
import { useReflectionAnswersStore } from "../stores/reflectionAnswers";
import type { ReflectionStatus } from "../stores/reflectionAnswers";

const STATUS_OPTIONS: { value: ReflectionStatus; label: string }[] = [
  { value: "ON_TRACK", label: "進んでいる" },
  { value: "STALLED", label: "止まっている" },
  { value: "REVISE", label: "見直したい" },
];

const router = useRouter();
const reflectionAnswersStore = useReflectionAnswersStore();

const goals = ref<ReflectionGoal[] | null>(null);
const errorMessage = ref("");
const answers = ref<Record<string, ReflectionStatus>>({});
const note = ref("");

onMounted(async () => {
  try {
    const context = await getReflectionContext();
    if (context.goals.length === 0) {
      router.replace("/s-41");
      return;
    }
    goals.value = context.goals;
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function setStatus(goalKey: string, status: ReflectionStatus): void {
  answers.value[goalKey] = status;
}

const canSubmit = computed(
  () => goals.value !== null && goals.value.every((goal) => answers.value[goal.goal_key] !== undefined),
);

const dialogOpen = ref(false);

function openDialog(): void {
  dialogOpen.value = true;
}

function continueFlow(): void {
  dialogOpen.value = false;
}

function leaveFlow(): void {
  dialogOpen.value = false;
  router.push("/s-41");
}

function submit(): void {
  if (!goals.value || !canSubmit.value) return;

  reflectionAnswersStore.setAnswers({
    statuses: goals.value.map((goal) => ({
      goal_key: goal.goal_key,
      status: answers.value[goal.goal_key],
    })),
    note: note.value.trim().length > 0 ? note.value.trim() : null,
  });
  router.push("/s-62");
}
</script>

<template>
  <div class="s61">
    <AppHeaderSingle
      title="振り返り"
      left-action="cancel"
      @cancel="openDialog"
    />

    <div
      v-if="goals"
      class="s61__body"
    >
      <div class="s61__intro">
        それぞれの目標が、今週どうだったか近いものを選んでみてください。
      </div>

      <div
        v-for="goal in goals"
        :key="goal.goal_key"
        class="s61__row"
      >
        <p class="s61__area-label">
          {{ AREA_META[goal.area].en }}
        </p>
        <p class="s61__goal-body">
          {{ goal.body }}
        </p>
        <div
          class="s61__status-row"
          role="radiogroup"
          :aria-label="`${goal.body}の状態`"
        >
          <label
            v-for="option in STATUS_OPTIONS"
            :key="option.value"
            class="s61__status-cell"
            :class="{ 's61__status-cell--selected': answers[goal.goal_key] === option.value }"
          >
            <input
              type="radio"
              :name="`status-${goal.goal_key}`"
              class="s61__status-input"
              :checked="answers[goal.goal_key] === option.value"
              @change="setStatus(goal.goal_key, option.value)"
            >
            <span>{{ option.label }}</span>
          </label>
        </div>
      </div>

      <div class="s61__rule" />

      <div class="s61__note">
        <p class="s61__note-text">
          今週、目標を進めるうえで困ったことや、気になったことがあれば教えてください。
          <span class="s61__note-sub">（任意）</span>
        </p>
        <textarea
          v-model="note"
          class="s61__note-area"
          rows="4"
          aria-label="自由記述（任意）"
        />
      </div>
    </div>

    <p
      v-else-if="errorMessage"
      class="s61__error"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="goals"
      class="s61__cta"
    >
      <AppButton
        :disabled="!canSubmit"
        @click="submit"
      >
        送信する
      </AppButton>
      <p
        v-if="!canSubmit"
        class="s61__hint"
      >
        すべて選ぶと、送信できます
      </p>
    </div>

    <InterruptDialog
      :open="dialogOpen"
      @continue="continueFlow"
      @leave="leaveFlow"
    />
  </div>
</template>

<style scoped>
.s61 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s61__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s61__intro {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s61__row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s61__area-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-faint);
  font-family: var(--font-latin);
}

.s61__goal-body {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s61__status-row {
  display: flex;
  gap: var(--space-1);
}

.s61__status-cell {
  position: relative;
  flex: 1 1 0;
  min-height: var(--tap-target-min);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  padding: var(--space-1);
  font-size: var(--font-size-caption);
  cursor: pointer;
}

.s61__status-cell--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
  font-weight: 600;
}

.s61__status-cell:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s61__status-input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.s61__rule {
  height: 1px;
  background: var(--border);
}

.s61__note {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s61__note-text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s61__note-sub {
  color: var(--text-sub);
}

.s61__note-area {
  min-height: 96px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  resize: vertical;
}

.s61__note-area:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s61__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s61__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  border-top: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s61__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
