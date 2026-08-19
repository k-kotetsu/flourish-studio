<script setup lang="ts">
/**
 * S-14 自由記述8問。04_画面設計(screen-list.md S-14)、05_質問・コンテンツ設計3章。
 * S-13が生成した8問(領域ごとに満たされている項目→気になっている項目の2問)を表示する。
 * すべて任意入力、全問空欄でも「レポートを作る」で進める。保存はしない(クライアント保持)。
 */
import { computed, onMounted, reactive } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import AreaIcon from "../components/AreaIcon.vue";
import { AREAS, AREA_META } from "../domain/questions";
import { useAssessmentQuestionsStore } from "../stores/assessmentQuestions";
import { useFreeTextAnswersStore, type FreeTextAnswer } from "../stores/freeTextAnswers";

const MAX_LENGTH = 1000;

const router = useRouter();
const questionsStore = useAssessmentQuestionsStore();
const freeTextStore = useFreeTextAnswersStore();

onMounted(() => {
  // S-13を経ずに直接開かれた場合など、8問揃っていなければS-11からやり直す
  if (questionsStore.questions.length !== 8) {
    router.replace("/s-11");
  }
});

function bodyKey(area: string, slot: string): string {
  return `${area}-${slot}`;
}

// 領域(Career→Financial→Physical→Social)ごとに、満たされている項目→気になっている項目の順(3.1)
const sections = computed(() =>
  AREAS.map((area) => ({
    area,
    meta: AREA_META[area],
    questions: questionsStore.questions
      .filter((q) => q.area === area)
      .sort((a, b) => (a.slot === b.slot ? 0 : a.slot === "SATISFIED" ? -1 : 1)),
  })),
);

const bodies = reactive<Record<string, string>>({});
for (const q of questionsStore.questions) {
  bodies[bodyKey(q.area, q.slot)] = "";
}

function goNext(): void {
  const answers: FreeTextAnswer[] = questionsStore.questions.map((q) => ({
    area: q.area,
    slot: q.slot,
    target_item_code: q.target_item_code,
    generated_question: q.text,
    body: bodies[bodyKey(q.area, q.slot)] ?? "",
  }));
  freeTextStore.setAnswers(answers);
  router.push("/s-15");
}

function goBack(): void {
  // S-13(生成中)を経由せずS-12へ直接戻す(04_画面設計)。戻す先はS-13の「回答に戻る」と同じ判断でSocial
  router.push("/s-12/social");
}
</script>

<template>
  <div
    v-if="questionsStore.questions.length === 8"
    class="s14"
  >
    <AppHeaderFlow
      title="現在地レポート"
      :percent="83"
      step="5 / 6"
      left-action="back"
      @back="goBack"
    />
    <div class="s14__body">
      <div class="s14__card">
        <p class="s14__intro">
          あと少しです。うまく言葉にならなくても大丈夫。空欄のままでも進めます。
        </p>
      </div>

      <div
        v-for="section in sections"
        :key="section.area"
        class="s14__section"
      >
        <div class="s14__heading">
          <AreaIcon :area="section.area" />
          <span class="s14__en">{{ section.meta.en }}</span>
          <span class="s14__jp">{{ section.meta.jp }}</span>
        </div>

        <div
          v-for="question in section.questions"
          :key="`${question.area}-${question.slot}`"
          class="s14__question"
        >
          <label
            :for="`s14-${bodyKey(question.area, question.slot)}`"
            class="s14__question-text"
          >
            {{ question.text }}
          </label>
          <textarea
            :id="`s14-${bodyKey(question.area, question.slot)}`"
            v-model="bodies[bodyKey(question.area, question.slot)]"
            class="s14__textarea"
            placeholder="自由に書いてみてください"
            rows="3"
            :maxlength="MAX_LENGTH"
          />
          <span class="s14__counter">{{ bodies[bodyKey(question.area, question.slot)]?.length ?? 0 }} / {{ MAX_LENGTH }}</span>
        </div>

        <div class="s14__rule" />
      </div>
    </div>

    <div class="s14__cta">
      <AppButton @click="goNext">
        レポートを作る
      </AppButton>
    </div>
  </div>
</template>

<style scoped>
.s14 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s14__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s14__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s14__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s14__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s14__heading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.s14__en {
  font-size: var(--font-size-section);
  font-weight: 600;
  font-family: var(--font-latin);
}

.s14__jp {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s14__question {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s14__question-text {
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s14__textarea {
  width: 100%;
  min-height: 88px;
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

.s14__textarea::placeholder {
  color: var(--text-faint);
}

.s14__textarea:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s14__counter {
  align-self: flex-end;
  font-size: var(--font-size-label);
  color: var(--text-faint);
}

.s14__rule {
  height: 1px;
  background: var(--border);
}

.s14__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}
</style>
