<script setup lang="ts">
/**
 * S-37 ありたい姿：編集。04_画面設計(screen-list.md S-37)、09_API設計5.8.1、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.4「一文を直接書き換えるだけ。文字数カウンタを出す
 * （上限60文字）。「領域は残る」と明記し、全部やり直しになると誤解させない」、mockup.html s37()）。
 *
 * `GET /purposes/current`で現在の一文を取得して編集欄の初期値にし、「保存する」で
 * `PUT /purposes/current`を呼ぶ(上書きではなく新しいバージョンを作る)。S-36を経由せず
 * 直接開かれた場合も動くよう、S-35のようなストア経由ではなく毎回取得し直す設計にした。
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getCurrentPurpose, updateCurrentPurpose } from "../api/purposes";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";

const STATEMENT_MAX_LENGTH = 60;

const router = useRouter();
const loaded = ref(false);
const editedStatement = ref("");
const status = ref<"idle" | "pending" | "failed">("idle");
const errorMessage = ref("");

const canSave = computed(
  () =>
    editedStatement.value.trim().length > 0 &&
    editedStatement.value.length <= STATEMENT_MAX_LENGTH &&
    status.value !== "pending",
);

onMounted(async () => {
  try {
    const current = await getCurrentPurpose();
    editedStatement.value = current.statement;
    loaded.value = true;
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function goBack(): void {
  router.push("/s-36");
}

async function save(): Promise<void> {
  if (!canSave.value) return;
  status.value = "pending";
  try {
    await updateCurrentPurpose(editedStatement.value.trim());
    router.push("/s-36");
  } catch (error) {
    status.value = "failed";
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}
</script>

<template>
  <div class="s37">
    <AppHeaderSingle
      title="ありたい姿を編集"
      @back="goBack"
    />

    <div
      v-if="loaded"
      class="s37__body"
    >
      <div class="s37__card">
        <p class="s37__intro">
          自分の言葉に書き換えてみてください。いつでも変えられます。
        </p>
      </div>

      <div class="s37__field">
        <label
          class="s37__label"
          for="s37-statement"
        >ありたい姿</label>
        <textarea
          id="s37-statement"
          v-model="editedStatement"
          class="s37__textarea"
          rows="4"
          :maxlength="STATEMENT_MAX_LENGTH"
        />
        <span class="s37__counter">{{ editedStatement.length }} / {{ STATEMENT_MAX_LENGTH }}</span>
      </div>

      <div class="s37__card">
        <p class="s37__intro">
          書き換えても、4つの領域で作った理想の状態と目標はそのまま残ります。作り直すかは、領域ごとに決められます。
        </p>
      </div>

      <p
        v-if="status === 'failed'"
        class="s37__error"
      >
        {{ errorMessage }}
      </p>
    </div>

    <p
      v-else-if="errorMessage"
      class="s37__error s37__error--standalone"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="loaded"
      class="s37__cta"
    >
      <AppButton
        :disabled="!canSave"
        @click="save"
      >
        {{ status === "pending" ? "保存しています…" : "保存する" }}
      </AppButton>
      <p
        v-if="editedStatement.trim().length === 0"
        class="s37__hint"
      >
        一文を書くと、保存できます
      </p>
    </div>
  </div>
</template>

<style scoped>
.s37 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s37__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s37__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s37__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s37__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s37__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s37__textarea {
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

.s37__textarea:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s37__counter {
  align-self: flex-end;
  font-size: var(--font-size-label);
  color: var(--text-faint);
}

.s37__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s37__error--standalone {
  margin: var(--space-4) var(--layout-gutter);
}

.s37__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s37__hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}
</style>
