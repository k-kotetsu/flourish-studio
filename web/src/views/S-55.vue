<script setup lang="ts">
/**
 * S-55 領域：理想状態の編集・確定。04_画面設計(screen-list.md S-55)、05_質問・コンテンツ設計9.5、
 * 06_ワイヤーフレーム(wireframe-spec.md「S-55 編集・確定 | ‹ 戻る | 領域名 | 4 / 5 | 80%」、
 * 「ここではまだ保存しない。S-56の確定でまとめて保存する」、mockup.html s55())。
 *
 * S-54で選んだ案(ideal_state)を自由に編集できる。上部に確定済みの「ありたい姿」を常時表示し
 * 続け、つながりが切れないようにする(9.5)。ここでは保存せず、`areaProposals`ストアへ編集後の
 * 文を記録してS-56(P4-6、未実装)へ進む(screen-list.md「保存: この時点では保存しない」)。
 *
 * 【判断】ありたい姿の表示はS-51と同じ`GET /purposes/current`のパターンを踏襲した。
 * 【判断】編集の文字数上限は仕様に明記が無い。ありたい姿(S-35)の60文字上限は「ありたい姿」
 * 固有の制約(定義書9.4)であり、領域の理想状態に及ぶ記載はどこにも無いため、上限を設けず
 * 自由記述のまま実装した。
 */
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getCurrentPurpose, type PurposeResponse } from "../api/purposes";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";
import { useAreaProposalsStore } from "../stores/areaProposals";

const route = useRoute();
const router = useRouter();
const proposalsStore = useAreaProposalsStore();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const hasSelectedProposal = computed(() => proposalsStore.selectedProposal !== null);

const editedIdealState = ref(
  proposalsStore.editedIdealState ?? proposalsStore.selectedProposal?.ideal_state ?? "",
);

const canProceed = computed(() => editedIdealState.value.trim().length > 0);

const purpose = ref<PurposeResponse | null>(null);
const purposeErrorMessage = ref("");

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す(S-51/S-54と同じ判断)
    router.replace("/s-50");
    return;
  }
  // S-54を経ずに直接開かれた場合など、選ばれた案が無ければ同じ領域のS-54からやり直す
  if (!hasSelectedProposal.value) {
    router.replace(`/s-54/${AREA_META[area].slug}`);
    return;
  }
  fetchPurpose();
});

async function fetchPurpose(): Promise<void> {
  try {
    purpose.value = await getCurrentPurpose();
  } catch (error) {
    purposeErrorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}

function goToProposalSelection(): void {
  if (!area) return;
  router.push(`/s-54/${AREA_META[area].slug}`);
}

function goNext(): void {
  if (!area || !canProceed.value) return;
  proposalsStore.setEditedIdealState(editedIdealState.value.trim());
  router.push(`/s-56/${AREA_META[area].slug}`);
}
</script>

<template>
  <div
    v-if="meta && hasSelectedProposal"
    class="s55"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="80"
      step="4 / 5"
      left-action="back"
      @back="goToProposalSelection"
    />

    <div
      v-if="purpose"
      class="s55__body"
    >
      <div class="s55__purpose-card">
        <p class="s55__purpose-label">
          ありたい姿
        </p>
        <p class="s55__purpose-statement">
          {{ purpose.statement }}
        </p>
      </div>

      <div class="s55__field">
        <label
          class="s55__label"
          for="s55-ideal-state"
        >{{ meta.en }}の理想の状態</label>
        <textarea
          id="s55-ideal-state"
          v-model="editedIdealState"
          class="s55__textarea"
          rows="5"
        />
      </div>

      <button
        type="button"
        class="s55__retry"
        @click="goToProposalSelection"
      >
        案を選び直す
      </button>
    </div>

    <p
      v-else-if="purposeErrorMessage"
      class="s55__error"
    >
      {{ purposeErrorMessage }}
    </p>

    <div
      v-if="purpose"
      class="s55__cta"
    >
      <AppButton
        :disabled="!canProceed"
        @click="goNext"
      >
        次へ
      </AppButton>
      <p
        v-if="!canProceed"
        class="s55__hint"
      >
        理想の状態を書くと、次に進めます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s55 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s55__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s55__purpose-card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s55__purpose-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s55__purpose-statement {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s55__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s55__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s55__textarea {
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

.s55__textarea:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s55__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s55__retry {
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

.s55__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s55__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s55__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
