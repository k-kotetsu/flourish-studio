<script setup lang="ts">
/**
 * S-36 ありたい姿：閲覧。04_画面設計(screen-list.md S-36)、09_API設計5.8.1、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.4「ホームのありたい姿カードから開く。
 * 領域のS-57と同じ型」、mockup.html s36())。
 *
 * `GET /purposes/current`で確定済みのありたい姿を取得して表示する。
 *
 * 【判断】screen-list.mdの主要素は「確定済みのありたい姿／作成した日付／4領域との
 * つながりの要約」の3つだが、このタスク(P3-9)の参照範囲(`09_API設計`5.8.1)・依存(P3-8)は
 * 4領域(AREA_PLAN、P4系)を含まず、`AREA_PLAN`のAPI自体がまだ存在しない。そのため
 * 「4領域とのつながりの要約」はP4系のタスクで別途追加する前提とし、本タスクでは
 * ありたい姿の一文と作成日付のみを表示する。
 */
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getCurrentPurpose, type PurposeResponse } from "../api/purposes";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";

const router = useRouter();
const purpose = ref<PurposeResponse | null>(null);
const errorMessage = ref("");

function formatCreatedAt(iso: string): string {
  const date = new Date(iso);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日に作成`;
}

onMounted(async () => {
  try {
    purpose.value = await getCurrentPurpose();
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function goBack(): void {
  router.push("/s-41");
}

function goToEdit(): void {
  router.push("/s-37");
}

function goToDialogue(): void {
  router.push("/s-31");
}
</script>

<template>
  <div class="s36">
    <AppHeaderSingle
      title="ありたい姿"
      @back="goBack"
    />

    <div
      v-if="purpose"
      class="s36__body"
    >
      <div class="s36__card">
        <p class="s36__label">
          ありたい姿
        </p>
        <p class="s36__statement">
          {{ purpose.statement }}
        </p>
      </div>
      <p class="s36__date">
        {{ formatCreatedAt(purpose.created_at) }}
      </p>

      <div class="s36__rule" />

      <AppButton
        variant="secondary"
        @click="goToEdit"
      >
        編集する
      </AppButton>
      <button
        type="button"
        class="s36__retry"
        @click="goToDialogue"
      >
        AIと話して作り直す
      </button>
    </div>

    <p
      v-else-if="errorMessage"
      class="s36__error"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped>
.s36 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s36__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s36__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s36__label {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s36__statement {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
  text-wrap: balance;
}

.s36__date {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s36__rule {
  height: 1px;
  background: var(--border);
  margin: var(--space-1) 0;
}

.s36__retry {
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

.s36__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s36__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}
</style>
