<script setup lang="ts">
/**
 * S-57 領域：閲覧。04_画面設計(screen-list.md S-57)、09_API設計5章の画面対応表、
 * 06_ワイヤーフレーム(wireframe-spec.md「S-57 閲覧 | ‹ 戻る | 領域名 | − | −」、
 * 「一覧 | 「編集する」（主）と「AIと話して見直す」（副）を並べる。軽い修正でAI対話を
 * 経由させない」、mockup.html s57())。S-36「ありたい姿：閲覧」と同じ型(wireframe-spec.md 7.4)。
 *
 * `GET /area-plans/{area}`で保存済みの理想の状態・今年の目標を取得して表示する。
 *
 * 【判断】ヘッダーはS-36と同じ`AppHeaderSingle`を使う(wireframe-spec.md「‹ 戻る | 領域名 |
 * − | −」がS-36の型と一致する)。
 * 【判断】未作成の領域への直接アクセス(404)は、S-36が`GET /purposes/current`の404で
 * とった判断と同じく、リダイレクトせず同画面にエラー表示する(通常はホームの作成済み
 * 領域カードから開くため到達しない経路だが、直接アクセスの保険)。
 */
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { type AreaPlanResponse, getAreaPlan } from "../api/areaPlans";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";

const route = useRoute();
const router = useRouter();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const plan = ref<AreaPlanResponse | null>(null);
const errorMessage = ref("");

onMounted(async () => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-51以降と同じ判断)
    router.replace("/s-50");
    return;
  }
  try {
    plan.value = await getAreaPlan(area);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function goBack(): void {
  // screen-list.md「遷移先: 「戻る」→ S-41」。S-41はP4-8が担当。ルートが無いため
  // この遷移は今は画面に反映されない(S-36が「S-41」未実装時にとった手法を踏襲)。
  router.push("/s-41");
}

function goToEdit(): void {
  if (!area) return;
  router.push(`/s-58/${AREA_META[area].slug}`);
}

function goToDialogue(): void {
  if (!area) return;
  router.push(`/s-51/${AREA_META[area].slug}`);
}
</script>

<template>
  <div
    v-if="meta"
    class="s57"
  >
    <AppHeaderSingle
      :title="meta.en"
      @back="goBack"
    />

    <div
      v-if="plan"
      class="s57__body"
    >
      <div class="s57__card">
        <p class="s57__label">
          理想の状態
        </p>
        <p class="s57__ideal-state">
          {{ plan.ideal_state }}
        </p>
      </div>

      <div class="s57__goals">
        <p class="s57__label">
          今年の目標
        </p>
        <div
          v-for="goal in plan.goals"
          :key="goal.goal_key"
          class="s57__goal"
        >
          {{ goal.body }}
        </div>
      </div>

      <div class="s57__rule" />

      <AppButton
        variant="secondary"
        @click="goToEdit"
      >
        編集する
      </AppButton>
      <button
        type="button"
        class="s57__retry"
        @click="goToDialogue"
      >
        AIと話して見直す
      </button>
    </div>

    <p
      v-else-if="errorMessage"
      class="s57__error"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped>
.s57 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s57__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s57__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s57__label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s57__ideal-state {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s57__goals {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s57__goal {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-card);
  background: var(--surface-sub);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s57__rule {
  height: 1px;
  background: var(--border);
}

.s57__retry {
  align-self: center;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  color: var(--text-sub);
  font-family: inherit;
  font-size: var(--font-size-caption);
  font-weight: 500;
  cursor: pointer;
}

.s57__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s57__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}
</style>
