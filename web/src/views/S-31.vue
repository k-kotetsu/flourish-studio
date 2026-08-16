<script setup lang="ts">
/**
 * S-31 ありたい姿：選択式3問。04_画面設計(screen-list.md S-31)、05_質問・コンテンツ設計6章、
 * 06_ワイヤーフレーム(wireframe-spec.md 1.1/1.4、mockup.html s31())。
 *
 * 領域を選ばせる設問は置かない(6章「ありたい姿は領域横断の概念」)。
 * 保存はしない(クライアント保持。screen-list.md S-31「保存: しない」)。
 *
 * 【判断】全問回答必須にした。05_質問・コンテンツ設計6章・screen-list.mdのどちらにも
 * 「未回答でも進めるか」の明記がなく、S-12(全問必須)とS-14(空欄可)で前例が分かれている。
 * 着手前にユーザーへ確認するほどの分岐ではあるが、バックグラウンド実行のため確認が取れず、
 * より保守的なS-12側(必須)に合わせた。Q1は1つ以上(3つまで)、Q2は1つ以上、Q3は1つ選ぶまで「次へ」を無効にする。
 *
 * ヘッダーは戻る/中断のどちらも置かない(left-action="none")。戻り先がS-21(登録)であり、
 * 登録後は完了画面を挟まずここへ来る一方通行の導線のため(wireframe-spec.md「戻る先が登録画面のため
 * ヘッダーに戻るを置かない」)。
 */
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import ChipMultiSelect from "../components/ChipMultiSelect.vue";
import CheckboxChoiceSelector from "../components/CheckboxChoiceSelector.vue";
import StackedChoiceSelector from "../components/StackedChoiceSelector.vue";
import {
  FULFILLING_MOMENT_OPTIONS,
  IDEAL_DAILY_LIFE_OPTIONS,
  VALUES_MAX_SELECTION,
  VALUES_OPTIONS,
} from "../domain/purposeChoices";
import { usePurposeChoicesStore } from "../stores/purposeChoices";

const router = useRouter();
const store = usePurposeChoicesStore();

const dailyLifeChoices = IDEAL_DAILY_LIFE_OPTIONS.map((option, index) => ({
  score: index,
  label: option.label,
}));

const selectedValues = ref<string[]>([]);
const selectedMoments = ref<string[]>([]);
const selectedDailyLifeIndex = ref<number | null>(null);

const isComplete = computed(
  () => selectedValues.value.length >= 1 && selectedMoments.value.length >= 1 && selectedDailyLifeIndex.value !== null,
);

function goNext(): void {
  if (!isComplete.value || selectedDailyLifeIndex.value === null) return;

  store.setAnswers({
    values: selectedValues.value,
    fulfillingMoments: selectedMoments.value,
    idealDailyLife: IDEAL_DAILY_LIFE_OPTIONS[selectedDailyLifeIndex.value].code,
  });

  router.push("/s-32");
}
</script>

<template>
  <div class="s31">
    <AppHeaderFlow
      title="ありたい姿"
      :percent="25"
      step="1 / 4"
      left-action="none"
    />
    <div class="s31__body">
      <div class="s31__card">
        <p class="s31__intro">
          3〜5年後のあなたについて、いくつか教えてください。まだ決まっていなくて大丈夫です。
        </p>
      </div>

      <div class="s31__question">
        <p
          id="s31-q-values"
          class="s31__question-text"
        >
          これからの3〜5年で、大切にしたいことは？<span class="s31__question-sub">（3つまで）</span>
        </p>
        <ChipMultiSelect
          v-model="selectedValues"
          :choices="VALUES_OPTIONS"
          :max="VALUES_MAX_SELECTION"
          labelled-by="s31-q-values"
        />
      </div>

      <div class="s31__rule" />

      <div class="s31__question">
        <p
          id="s31-q-moments"
          class="s31__question-text"
        >
          満たされていると感じるのは、どんなときですか？
        </p>
        <CheckboxChoiceSelector
          v-model="selectedMoments"
          :choices="FULFILLING_MOMENT_OPTIONS"
          labelled-by="s31-q-moments"
          name="fulfilling-moments"
        />
      </div>

      <div class="s31__rule" />

      <div class="s31__question">
        <p
          id="s31-q-daily-life"
          class="s31__question-text"
        >
          3〜5年後、どんな毎日を送っていたいですか？
        </p>
        <StackedChoiceSelector
          v-model="selectedDailyLifeIndex"
          :choices="dailyLifeChoices"
          labelled-by="s31-q-daily-life"
          name="ideal-daily-life"
        />
      </div>
    </div>

    <div class="s31__cta">
      <AppButton
        :disabled="!isComplete"
        @click="goNext"
      >
        次へ
      </AppButton>
      <p
        v-if="!isComplete"
        class="s31__hint"
      >
        すべて選ぶと、次に進めます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s31 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s31__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s31__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s31__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s31__question {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s31__question-text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s31__question-sub {
  margin-left: var(--space-1);
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s31__rule {
  height: 1px;
  background: var(--border);
}

.s31__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.s31__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  text-align: center;
}
</style>
