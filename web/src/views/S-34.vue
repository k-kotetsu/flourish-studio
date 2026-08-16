<script setup lang="ts">
/**
 * S-34 ありたい姿：3案提示・選択。04_画面設計(screen-list.md S-34)、
 * 05_質問・コンテンツ設計8.4、06_ワイヤーフレーム(wireframe-spec.md「自分→他者→社会の順で固定」、
 * mockup.html s34())。
 *
 * S-33が生成した3案を固定順(SELF→OTHERS→SOCIETY)で並べ、1案を選ぶまで「この案で進む」を
 * 無効化する(S-12と同じ「すべて選ぶと、次に進めます」型の無効化理由)。
 */
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import type { PurposeDirection } from "../api/purposeProposals";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const DIRECTION_ORDER: PurposeDirection[] = ["SELF", "OTHERS", "SOCIETY"];

const router = useRouter();
const proposalsStore = usePurposeProposalsStore();

const hasProposals = computed(() => proposalsStore.proposals.length === 3);

// AI出力の順序に依存せず、常にSELF→OTHERS→SOCIETYで並べる(S-16のAREAS並べ替えと同じ考え方)。
const orderedProposals = computed(() =>
  DIRECTION_ORDER.map(
    (direction) => proposalsStore.proposals.find((proposal) => proposal.direction === direction)!,
  ),
);

onMounted(() => {
  // S-33を経ずに直接開かれた場合など、3案揃っていなければS-31からやり直す
  if (!hasProposals.value) {
    router.replace("/s-31");
  }
});

function goBack(): void {
  // S-33(生成中の一時画面)は経由させず、直前の実質的な入力画面であるS-32へ戻す
  // (S-14の「戻る」がS-13を飛ばしてS-12へ戻る判断と同じ考え方。仕様に明記なし)。
  router.push("/s-32");
}

function regenerate(): void {
  router.push("/s-33");
}

function goNext(): void {
  // S-35(編集・確定)はP3-8が担当。ルートが無いためこの遷移は今は画面に反映されない
  // (S-11/S-12/S-32がP2-3/P2-6/P3-7未実装時にとった手法を踏襲)。
  router.push("/s-35");
}
</script>

<template>
  <div
    v-if="hasProposals"
    class="s34"
  >
    <AppHeaderFlow
      title="ありたい姿"
      :percent="75"
      step="3 / 4"
      left-action="back"
      @back="goBack"
    />
    <div class="s34__body">
      <div class="s34__card s34__intro">
        <p class="s34__intro-text">
          どれが正解ということはありません。いちばん自分に近いと感じたものを選んでください。あとから自由に書き換えられます。
        </p>
      </div>

      <div
        class="s34__proposals"
        role="radiogroup"
        aria-label="ありたい姿の案"
      >
        <label
          v-for="proposal in orderedProposals"
          :key="proposal.direction"
          class="s34__proposal"
          :class="{
            's34__proposal--selected': proposalsStore.selectedDirection === proposal.direction,
          }"
        >
          <input
            type="radio"
            name="purpose-proposal"
            class="s34__proposal-input"
            :checked="proposalsStore.selectedDirection === proposal.direction"
            @change="proposalsStore.select(proposal.direction)"
          >
          <span class="s34__proposal-label">{{ proposal.label }}</span>
          <span class="s34__proposal-statement">{{ proposal.statement }}</span>
        </label>
      </div>

      <button
        type="button"
        class="s34__retry"
        @click="regenerate"
      >
        3つとも作り直す
      </button>
    </div>

    <div class="s34__cta">
      <AppButton
        :disabled="!proposalsStore.selectedDirection"
        @click="goNext"
      >
        この案で進む
      </AppButton>
      <p
        v-if="!proposalsStore.selectedDirection"
        class="s34__hint"
      >
        1つ選ぶと、次に進めます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s34 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s34__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s34__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s34__intro-text {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s34__proposals {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s34__proposal {
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

.s34__proposal--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.s34__proposal-input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.s34__proposal:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s34__proposal-label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s34__proposal-statement {
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.s34__retry {
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

.s34__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s34__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s34__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
