<script setup lang="ts">
/**
 * S-35 ありたい姿：編集・確定。04_画面設計(screen-list.md S-35)、09_API設計5.8、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.4「完了画面を挟まないため、この画面が成果物の
 * 提示を兼ねる。確定後に一文を大きく見せてから S-50 へ」、mockup.html s35())。
 *
 * S-34で選んだ案(direction/label/statement)を自由に編集し、「これで確定する」で
 * `POST /purposes`を呼ぶ。ここではじめて保存される(それまでは選択式回答・対話履歴とも
 * クライアント保持のみ)。確定に成功したら同じ画面のまま提示状態に切り替え、S-50へ進む
 * ボタンを出す(完了画面を挟まない設計のため、画面遷移ではなく状態切り替えで表現する)。
 *
 * 【判断】「一文を大きく見せる」の具体的なサイズはワイヤーフレームに指定が無い。
 * S-16(あだ名)専用の`--font-size-nickname`(28px/700/1.35)は「大きな一文を見せる」という
 * 役割が共通するため、新しいトークンを増やさずここに流用した。
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { createPurpose } from "../api/purposes";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";
import { usePurposeProposalsStore } from "../stores/purposeProposals";

const STATEMENT_MAX_LENGTH = 60;

const router = useRouter();
const choicesStore = usePurposeChoicesStore();
const dialogueStore = usePurposeDialogueStore();
const proposalsStore = usePurposeProposalsStore();

const hasSelectedProposal = computed(() => proposalsStore.selectedProposal !== null);

const editedStatement = ref(proposalsStore.selectedProposal?.statement ?? "");
const status = ref<"idle" | "pending" | "failed" | "confirmed">("idle");
const errorMessage = ref("");
const confirmedStatement = ref("");

const canConfirm = computed(
  () =>
    editedStatement.value.trim().length > 0 &&
    editedStatement.value.length <= STATEMENT_MAX_LENGTH &&
    status.value !== "pending",
);

onMounted(() => {
  // S-34を経ずに直接開かれた場合など、選ばれた案が無ければS-31からやり直す(S-34と同じ判断)
  if (!hasSelectedProposal.value) {
    router.replace("/s-31");
  }
});

function goToProposalSelection(): void {
  router.push("/s-34");
}

function goToAreaSelection(): void {
  // S-50(領域を選ぶ)はP4-1が担当。ルートが無いためこの遷移は今は画面に反映されない
  // (S-34の「この案で進む」がP3-8未実装時にとった手法を踏襲)。
  router.push("/s-50");
}

async function confirm(): Promise<void> {
  const proposal = proposalsStore.selectedProposal;
  if (!proposal || !canConfirm.value) return;

  status.value = "pending";
  try {
    const result = await createPurpose({
      choices: choicesStore.asChoices,
      messages: dialogueStore.messages,
      selected_direction: proposal.direction,
      selected_label: proposal.label,
      original_statement: proposal.statement,
      statement: editedStatement.value.trim(),
    });
    confirmedStatement.value = result.statement;
    status.value = "confirmed";
  } catch (error) {
    status.value = "failed";
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}
</script>

<template>
  <div
    v-if="hasSelectedProposal"
    class="s35"
  >
    <AppHeaderFlow
      title="ありたい姿"
      :percent="100"
      step="4 / 4"
      :left-action="status === 'confirmed' ? 'none' : 'back'"
      @back="goToProposalSelection"
    />

    <template v-if="status !== 'confirmed'">
      <div class="s35__body">
        <div class="s35__card">
          <p class="s35__intro">
            自分の言葉に書き換えてみてください。あとからいつでも変えられます。
          </p>
        </div>

        <div class="s35__field">
          <label
            class="s35__label"
            for="s35-statement"
          >あなたのありたい姿</label>
          <textarea
            id="s35-statement"
            v-model="editedStatement"
            class="s35__textarea"
            rows="4"
            :maxlength="STATEMENT_MAX_LENGTH"
          />
          <span class="s35__counter">{{ editedStatement.length }} / {{ STATEMENT_MAX_LENGTH }}</span>
        </div>

        <p
          v-if="status === 'failed'"
          class="s35__error"
        >
          {{ errorMessage }}
        </p>

        <button
          type="button"
          class="s35__retry"
          @click="goToProposalSelection"
        >
          案を選び直す
        </button>
      </div>

      <div class="s35__cta">
        <AppButton
          :disabled="!canConfirm"
          @click="confirm"
        >
          {{ status === "pending" ? "確定しています…" : "これで確定する" }}
        </AppButton>
        <p
          v-if="editedStatement.trim().length === 0"
          class="s35__hint"
        >
          一文を書くと、確定できます
        </p>
      </div>
    </template>

    <template v-else>
      <div class="s35__confirmed">
        <p class="s35__confirmed-statement">
          {{ confirmedStatement }}
        </p>
      </div>
      <div class="s35__cta">
        <AppButton @click="goToAreaSelection">
          進む
        </AppButton>
      </div>
    </template>
  </div>
</template>

<style scoped>
.s35 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s35__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s35__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s35__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s35__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s35__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s35__textarea {
  width: 100%;
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

.s35__textarea:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s35__counter {
  align-self: flex-end;
  font-size: var(--font-size-label);
  color: var(--text-faint);
}

.s35__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s35__retry {
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

.s35__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s35__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s35__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s35__confirmed {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  padding: var(--space-5) var(--layout-gutter);
}

.s35__confirmed-statement {
  margin: 0;
  font-size: var(--font-size-nickname);
  font-weight: 700;
  line-height: var(--line-height-nickname);
  text-wrap: balance;
}
</style>
