<script setup lang="ts">
/**
 * S-54 領域：3案提示・選択。04_画面設計(screen-list.md S-54)、10_AIプロンプト設計4.6、
 * 06_ワイヤーフレーム(wireframe-spec.md 1.1「深める→変える→広げるの順で固定。回答による
 * 並べ替えはしない」、mockup.html s54())。
 *
 * S-53が生成した3案を固定順(DEEPEN→CHANGE→EXPAND)で並べ、1案を選ぶまで「この案で進む」を
 * 無効化する(S-34と同じ「1つ選ぶと、次に進めます」型の無効化理由)。順序はサーバー側でも
 * 検証済み(`validate_output`)だが、S-34がAI出力の順序に依存しない表示にした前例を踏襲し、
 * 表示側でも固定順に並べ替える。
 */
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { AreaDirection } from "../api/areaProposals";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";
import { useAreaProposalsStore } from "../stores/areaProposals";

const DIRECTION_ORDER: AreaDirection[] = ["DEEPEN", "CHANGE", "EXPAND"];

const route = useRoute();
const router = useRouter();
const proposalsStore = useAreaProposalsStore();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const hasProposals = computed(() => proposalsStore.proposals.length === 3);

const orderedProposals = computed(() =>
  DIRECTION_ORDER.map(
    (direction) => proposalsStore.proposals.find((proposal) => proposal.direction === direction)!,
  ),
);

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-52/S-53と同じ判断)
    router.replace("/s-50");
    return;
  }
  // S-53を経ずに直接開かれた場合など、3案揃っていなければその領域のS-51からやり直す
  // (S-34がS-31からやり直させる判断と同じ考え方)
  if (!hasProposals.value) {
    router.replace(`/s-51/${AREA_META[area].slug}`);
  }
});

function goBack(): void {
  if (!area) return;
  // S-53(生成中の一時画面)は経由させず、直前の実質的な入力画面であるS-52へ戻す
  // (S-34の「戻る」がS-33を飛ばしてS-32へ戻る判断と同じ考え方。仕様に明記なし)。
  router.push(`/s-52/${AREA_META[area].slug}`);
}

function regenerate(): void {
  if (!area) return;
  router.push(`/s-53/${AREA_META[area].slug}`);
}

function goNext(): void {
  if (!area) return;
  router.push(`/s-55/${AREA_META[area].slug}`);
}
</script>

<template>
  <div
    v-if="meta && hasProposals"
    class="s54"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="60"
      step="3 / 5"
      left-action="back"
      @back="goBack"
    />
    <div class="s54__body">
      <div class="s54__card s54__intro">
        <p class="s54__intro-text">
          1年後、{{ meta.en }}がどんな状態だとうれしいでしょうか。近いものを選んでください。
        </p>
      </div>

      <div
        class="s54__proposals"
        role="radiogroup"
        aria-label="理想の状態の案"
      >
        <label
          v-for="proposal in orderedProposals"
          :key="proposal.direction"
          class="s54__proposal"
          :class="{
            's54__proposal--selected': proposalsStore.selectedDirection === proposal.direction,
          }"
        >
          <input
            type="radio"
            name="area-proposal"
            class="s54__proposal-input"
            :checked="proposalsStore.selectedDirection === proposal.direction"
            @change="proposalsStore.select(proposal.direction)"
          >
          <span class="s54__proposal-label">{{ proposal.label }}</span>
          <span class="s54__proposal-statement">{{ proposal.ideal_state }}</span>
        </label>
      </div>

      <button
        type="button"
        class="s54__retry"
        @click="regenerate"
      >
        3つとも作り直す
      </button>
    </div>

    <div class="s54__cta">
      <AppButton
        :disabled="!proposalsStore.selectedDirection"
        @click="goNext"
      >
        この案で進む
      </AppButton>
      <p
        v-if="!proposalsStore.selectedDirection"
        class="s54__hint"
      >
        1つ選ぶと、次に進めます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s54 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s54__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s54__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s54__intro-text {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s54__proposals {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s54__proposal {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-card);
  background: var(--surface);
  cursor: pointer;
}

.s54__proposal--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.s54__proposal-input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.s54__proposal:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s54__proposal-label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s54__proposal-statement {
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.s54__retry {
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

.s54__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s54__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s54__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
