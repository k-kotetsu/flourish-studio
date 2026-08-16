<script setup lang="ts">
/**
 * S-51 領域：選択式質問。04_画面設計(screen-list.md S-51)、05_質問・コンテンツ設計9.2、
 * 06_ワイヤーフレーム(wireframe-spec.md 1.1/1.4、mockup.html s51())。
 * 4領域共通の1画面とし、ルートパラメータ(:area)で切り替える(S-12・P4-1完了メモが確立した設計)。
 * 保存はしない(クライアント保持。screen-list.md S-51「保存: しない」)。
 *
 * 上部に確定済みの「ありたい姿」を常時表示する(9.2)。`GET /purposes/current`で取得する
 * (S-36が確立したパターン)。登録済みユーザーのみが到達する画面(screen-list.md「認証状態: 登録済」)
 * だが、フロント側にルートレベルの認証ガードはまだ無い(S-36完了時点から変わっていない)ため、
 * 取得失敗(401含む)はエラー表示に留める。
 *
 * Q1(いちばん変えたい項目)はS-12と同じ5項目をそのまま使う(9.2「現在地レポートで使った
 * 5項目をそのまま提示する」)。Q2・Q3は領域ごとに文言・選択肢が異なる(9.2)。
 *
 * 【判断】Q1〜Q3すべて回答必須にした。9.2・screen-list.mdのどちらにも「未回答でも進めるか」の
 * 明記がなく、S-31(P3-5)がまったく同じ構成(単一選択1問＋複数選択2問)で下した判断
 * (より保守的なS-12側＝全問必須に揃える)をそのまま踏襲した。Q2・Q3は上限を設けない
 * (9.2に上限の記載がないため、S-31のQ2＝FULFILLING_MOMENT_OPTIONSと同じ「上限なし」の扱い)。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getCurrentPurpose, type PurposeResponse } from "../api/purposes";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import CheckboxChoiceSelector from "../components/CheckboxChoiceSelector.vue";
import InterruptDialog from "../components/InterruptDialog.vue";
import StackedChoiceSelector from "../components/StackedChoiceSelector.vue";
import { AREA_POSITION_OPTIONS, AREA_POSITION_PROMPT, AREA_VALUES_OPTIONS, AREA_VALUES_PROMPT } from "../domain/areaChoices";
import { AREA_META, CURRENT_QUESTION_SET_VERSION, areaFromSlug, getQuestionSet, itemsForArea } from "../domain/questions";
import { useAreaChoicesStore } from "../stores/areaChoices";

const route = useRoute();
const router = useRouter();
const areaChoicesStore = useAreaChoicesStore();
const questionSet = getQuestionSet(CURRENT_QUESTION_SET_VERSION);

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;
const items = area ? itemsForArea(questionSet, area) : [];
const changeItemChoices = items.map((item, index) => ({ score: index, label: item.label }));
const valuesOptions = area ? AREA_VALUES_OPTIONS[area] : [];
const positionOptions = area ? AREA_POSITION_OPTIONS[area] : [];
const valuesPrompt = area ? AREA_VALUES_PROMPT[area] : "";
const positionPrompt = area ? AREA_POSITION_PROMPT[area] : "";

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す
    router.replace("/s-50");
    return;
  }
  fetchPurpose();
});

const purpose = ref<PurposeResponse | null>(null);
const errorMessage = ref("");

async function fetchPurpose(): Promise<void> {
  try {
    purpose.value = await getCurrentPurpose();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}

const selectedChangeIndex = ref<number | null>(null);
const selectedValues = ref<string[]>([]);
const selectedPositions = ref<string[]>([]);

const isComplete = computed(
  () => selectedChangeIndex.value !== null && selectedValues.value.length >= 1 && selectedPositions.value.length >= 1,
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
  areaChoicesStore.reset();
  router.push("/s-41");
}

function goNext(): void {
  if (!area || !isComplete.value || selectedChangeIndex.value === null) return;

  areaChoicesStore.setAnswers({
    area,
    changeItemCode: items[selectedChangeIndex.value].code,
    values: selectedValues.value,
    positions: selectedPositions.value,
  });

  router.push(`/s-52/${AREA_META[area].slug}`);
}
</script>

<template>
  <div
    v-if="meta"
    class="s51"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="20"
      step="1 / 5"
      left-action="cancel"
      @cancel="openDialog"
    />

    <div
      v-if="purpose"
      class="s51__body"
    >
      <div class="s51__card">
        <p class="s51__purpose-label">
          ありたい姿
        </p>
        <p class="s51__purpose-statement">
          {{ purpose.statement }}
        </p>
      </div>

      <div class="s51__question">
        <p
          id="s51-q-change"
          class="s51__question-text"
        >
          {{ meta.en }}の中で、3〜5年後にいちばん変わっていてほしいのはどれですか？
        </p>
        <StackedChoiceSelector
          v-model="selectedChangeIndex"
          :choices="changeItemChoices"
          labelled-by="s51-q-change"
          name="change-item"
        />
      </div>

      <div class="s51__rule" />

      <div class="s51__question">
        <p
          id="s51-q-values"
          class="s51__question-text"
        >
          {{ valuesPrompt }}<span class="s51__question-sub">（あてはまるものをすべて）</span>
        </p>
        <CheckboxChoiceSelector
          v-model="selectedValues"
          :choices="valuesOptions"
          labelled-by="s51-q-values"
          name="area-values"
        />
      </div>

      <div class="s51__rule" />

      <div class="s51__question">
        <p
          id="s51-q-position"
          class="s51__question-text"
        >
          {{ positionPrompt }}<span class="s51__question-sub">（あてはまるものをすべて）</span>
        </p>
        <CheckboxChoiceSelector
          v-model="selectedPositions"
          :choices="positionOptions"
          labelled-by="s51-q-position"
          name="area-position"
        />
      </div>
    </div>

    <p
      v-else-if="errorMessage"
      class="s51__error"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="purpose"
      class="s51__cta"
    >
      <AppButton
        :disabled="!isComplete"
        @click="goNext"
      >
        次へ
      </AppButton>
      <p
        v-if="!isComplete"
        class="s51__hint"
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
.s51 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s51__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s51__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s51__purpose-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s51__purpose-statement {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s51__question {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.s51__question-text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s51__question-sub {
  margin-left: var(--space-1);
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s51__rule {
  height: 1px;
  background: var(--border);
}

.s51__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.s51__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  text-align: center;
}

.s51__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}
</style>
