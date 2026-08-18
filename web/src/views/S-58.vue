<script setup lang="ts">
/**
 * S-58 領域：編集。04_画面設計(screen-list.md S-58)、09_API設計5.12、08_データモデル4.5、
 * 06_ワイヤーフレーム(wireframe-spec.md「S-58 編集 | ‹ 戻る | 領域名を編集 | − | −」、
 * 「フォーム | 理想の状態と目標を直接書き換えるだけ。保存すると S-57 へ戻る」、
 * 「目標の削除 | S-58 でのみ行う。各行に削除ボタン」)。
 *
 * `GET /area-plans/{area}`で現在の理想の状態・目標を取得して編集欄の初期値にし、
 * 「保存する」で`PUT /area-plans/{area}`を呼ぶ(上書きではなく新しいバージョンを作る)。
 * 既存の目標は`goal_key`を保持したまま編集し、削除した目標のキーは送らない(サーバー側で
 * 「送られなかったgoal_keyはその版で削除」として扱う。08_データモデル4.5)。
 * 「＋ 目標を追加」で作った新しい目標には`goal_key`を持たせず、サーバーが採番する。
 *
 * 【判断】ヘッダーはS-37と同じ`AppHeaderSingle`を使う(wireframe-spec.mdの型がS-37と一致)。
 * 【判断】目標は最大3個・最低1個(S-56と同じ上限。空欄は保存時に取り除く)。削除ボタンは
 * ワイヤーフレームに具体的な見た目の指定が無いため、他の逃げ道ボタンと同じテキストボタンで
 * 実装した(スキルflourish-ui「アイコンは線画のみ」に反する装飾アイコンを増やさない判断)。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { type AreaPlanGoalUpdateIn, getAreaPlan, updateAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";

const MAX_GOALS = 3;

interface EditableGoal {
  goalKey: string | null;
  body: string;
}

const route = useRoute();
const router = useRouter();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const loaded = ref(false);
const errorMessage = ref("");
const editedIdealState = ref("");
const goals = ref<EditableGoal[]>([]);
const status = ref<"idle" | "pending" | "failed">("idle");

const canAddGoal = computed(() => goals.value.length < MAX_GOALS);
const trimmedGoals = computed(() =>
  goals.value
    .map((goal) => ({ goalKey: goal.goalKey, body: goal.body.trim() }))
    .filter((goal) => goal.body.length > 0),
);
const canSave = computed(
  () =>
    editedIdealState.value.trim().length > 0 &&
    trimmedGoals.value.length >= 1 &&
    status.value !== "pending",
);

onMounted(async () => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-51以降と同じ判断)
    router.replace("/s-50");
    return;
  }
  try {
    const plan = await getAreaPlan(area);
    editedIdealState.value = plan.ideal_state;
    goals.value = plan.goals.map((goal) => ({ goalKey: goal.goal_key, body: goal.body }));
    loaded.value = true;
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function addGoal(): void {
  if (!canAddGoal.value) return;
  goals.value.push({ goalKey: null, body: "" });
}

function removeGoal(index: number): void {
  goals.value.splice(index, 1);
}

function goBack(): void {
  if (!area) return;
  router.push(`/s-57/${AREA_META[area].slug}`);
}

async function save(): Promise<void> {
  if (!area || !canSave.value) return;
  status.value = "pending";
  errorMessage.value = "";
  try {
    const goalsPayload: AreaPlanGoalUpdateIn[] = trimmedGoals.value.map((goal, index) => ({
      ...(goal.goalKey ? { goal_key: goal.goalKey } : {}),
      body: goal.body,
      sort_order: index + 1,
    }));
    await updateAreaPlan(area, {
      ideal_state: editedIdealState.value.trim(),
      goals: goalsPayload,
    });
    router.push(`/s-57/${AREA_META[area].slug}`);
  } catch (error) {
    status.value = "failed";
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}
</script>

<template>
  <div
    v-if="meta"
    class="s58"
  >
    <AppHeaderSingle
      :title="`${meta.en}を編集`"
      @back="goBack"
    />

    <div
      v-if="loaded"
      class="s58__body"
    >
      <div class="s58__field">
        <label
          class="s58__label"
          for="s58-ideal-state"
        >理想の状態</label>
        <textarea
          id="s58-ideal-state"
          v-model="editedIdealState"
          class="s58__textarea"
          rows="5"
        />
      </div>

      <div class="s58__goals">
        <p class="s58__label">
          今年の目標
        </p>
        <div
          v-for="(goal, index) in goals"
          :key="index"
          class="s58__goal-row"
        >
          <input
            v-model="goal.body"
            type="text"
            class="s58__input"
            :aria-label="`${index + 1}つ目の目標`"
          >
          <button
            type="button"
            class="s58__remove"
            :aria-label="`${index + 1}つ目の目標を削除`"
            @click="removeGoal(index)"
          >
            削除
          </button>
        </div>
      </div>

      <button
        v-if="canAddGoal"
        type="button"
        class="s58__ghost-button"
        @click="addGoal"
      >
        ＋ 目標を追加
      </button>

      <p
        v-if="status === 'failed'"
        class="s58__error"
      >
        {{ errorMessage }}
      </p>
    </div>

    <p
      v-else-if="errorMessage"
      class="s58__error s58__error--standalone"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="loaded"
      class="s58__cta"
    >
      <AppButton
        :disabled="!canSave"
        @click="save"
      >
        {{ status === "pending" ? "保存しています…" : "保存する" }}
      </AppButton>
      <p
        v-if="!canSave"
        class="s58__hint"
      >
        理想の状態と目標を1つ書くと、保存できます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s58 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s58__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s58__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s58__label {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s58__textarea {
  width: 100%;
  min-height: 120px;
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

.s58__textarea:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s58__goals {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s58__goal-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.s58__input {
  flex: 1 1 auto;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
}

.s58__input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s58__remove {
  flex: 0 0 auto;
  min-height: var(--tap-target-min);
  min-width: var(--tap-target-min);
  padding: var(--space-2) var(--space-2);
  border: none;
  background: transparent;
  color: var(--text-sub);
  font-family: inherit;
  font-size: var(--font-size-caption);
  font-weight: 500;
  cursor: pointer;
}

.s58__remove:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s58__ghost-button {
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

.s58__ghost-button:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s58__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s58__error--standalone {
  margin: var(--space-4) var(--layout-gutter);
}

.s58__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s58__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
