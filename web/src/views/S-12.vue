<script setup lang="ts">
/**
 * S-12 選択式24問。05_質問・コンテンツ設計2章、06_ワイヤーフレーム(wireframe-spec.md 2章 / mockup.html s12())。
 * 4領域共通の1画面とし、ルートパラメータ(:area)で切り替える(同じコンポーネントを4回通る)。
 * App.vueのrouter-viewに `:key="$route.fullPath"` を付けているため、領域が変わるたびに
 * このコンポーネントは新規に作り直される。そのため領域が変わったときの回答リセットは
 * 考えなくてよく、setup実行時の値をそのまま使う。
 * 保存はしない(クライアント保持)。Socialまで終えたらS-13(P2-6、未実装)へ。
 */
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import InterruptDialog from "../components/InterruptDialog.vue";
import ScaleSelector from "../components/ScaleSelector.vue";
import StackedChoiceSelector from "../components/StackedChoiceSelector.vue";
import {
  AREAS,
  AREA_META,
  COMMITMENT,
  CURRENT_QUESTION_SET_VERSION,
  SATISFACTION,
  areaFromSlug,
  getQuestionSet,
  itemsForArea,
} from "../domain/questions";
import { useAssessmentAnswersStore, type ScaleAnswer } from "../stores/assessmentAnswers";

const route = useRoute();
const router = useRouter();
const answersStore = useAssessmentAnswersStore();
const questionSet = getQuestionSet(CURRENT_QUESTION_SET_VERSION);

const area = areaFromSlug(String(route.params.area));
const items = area ? itemsForArea(questionSet, area) : [];
const meta = area ? AREA_META[area] : null;
const stepIndex = area ? AREAS.indexOf(area) + 1 : 0;
const percent = Math.round((stepIndex / 6) * 100);

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合の唯一の入口(S-11)へ戻す
    router.replace("/s-11");
  }
});

const initialSatisfaction: Record<string, number | null> = {};
for (const item of items) {
  initialSatisfaction[item.code] = null;
}
const answers = reactive<{ satisfaction: Record<string, number | null>; commitment: number | null }>({
  satisfaction: initialSatisfaction,
  commitment: null,
});

const isComplete = computed(
  () => items.every((item) => answers.satisfaction[item.code] !== null) && answers.commitment !== null,
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
  answersStore.reset();
  router.push("/");
}

function goNext(): void {
  if (!area || !isComplete.value) return;

  const scaleAnswers: ScaleAnswer[] = items.map((item) => ({
    area,
    question_kind: SATISFACTION,
    item_code: item.code,
    score: answers.satisfaction[item.code] as number,
  }));
  scaleAnswers.push({
    area,
    question_kind: COMMITMENT,
    score: answers.commitment as number,
  });
  answersStore.recordArea(area, scaleAnswers);

  const nextIndex = AREAS.indexOf(area) + 1;
  if (nextIndex < AREAS.length) {
    router.push(`/s-12/${AREA_META[AREAS[nextIndex]].slug}`);
  } else {
    // S-13(P2-6)は未実装。実装され次第このパスへの遷移が有効になる
    router.push("/s-13");
  }
}
</script>

<template>
  <div
    v-if="meta"
    class="s12"
  >
    <AppHeaderFlow
      title="現在地レポート"
      :percent="percent"
      left-action="cancel"
      :step="`${stepIndex} / 6`"
      @cancel="openDialog"
    />
    <div class="s12__body">
      <div class="s12__heading">
        <span class="s12__en">{{ meta.en }}</span>
        <span class="s12__jp">{{ meta.jp }}</span>
      </div>
      <div class="s12__card">
        <p class="s12__intro">
          {{ meta.introLabel }}について、いまの気持ちに近いところを選んでみてください。深く考えこまなくて大丈夫です。右にいくほど、満たされている状態です。
        </p>
      </div>

      <div
        v-for="item in items"
        :key="item.code"
        class="s12__question"
      >
        <p
          :id="`s12-q-${item.code}`"
          class="s12__question-text"
        >
          {{ item.label }}
        </p>
        <ScaleSelector
          v-model="answers.satisfaction[item.code]"
          :choices="questionSet.satisfactionChoices"
          :labelled-by="`s12-q-${item.code}`"
          :name="`satisfaction-${item.code}`"
        />
      </div>

      <div class="s12__rule" />

      <div class="s12__question">
        <p
          id="s12-q-commitment"
          class="s12__question-text"
        >
          {{ meta.en }} をより良くするために、いま動けていますか？
        </p>
        <StackedChoiceSelector
          v-model="answers.commitment"
          :choices="questionSet.commitmentChoices"
          labelled-by="s12-q-commitment"
          name="commitment"
        />
      </div>
    </div>

    <div class="s12__cta">
      <AppButton
        :disabled="!isComplete"
        @click="goNext"
      >
        次へ
      </AppButton>
      <p
        v-if="!isComplete"
        class="s12__hint"
      >
        すべて選ぶと、次に進めます
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
.s12 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s12__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s12__heading {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.s12__en {
  font-size: var(--font-size-section);
  font-weight: 600;
  font-family: var(--font-latin);
}

.s12__jp {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s12__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s12__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s12__question {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s12__question-text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s12__rule {
  height: 1px;
  background: var(--border);
}

.s12__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.s12__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  text-align: center;
}
</style>
