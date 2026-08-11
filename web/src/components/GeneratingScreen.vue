<script setup lang="ts">
/**
 * 07_デザイン原則 7.4。S-13/S-15/S-33/S-53/S-62 の生成中画面本体（ヘッダーを除く本文）。
 * 失敗時はこのコンポーネントの中身が入れ替わるだけで、画面遷移はしない。
 * 再試行は手動のみ。errorMessageは呼び出し側が具体的に渡す（定型文で埋めない）。
 */
import AppButton from "./AppButton.vue";

withDefaults(
  defineProps<{
    message: string;
    failed?: boolean;
    errorTitle?: string;
    errorMessage?: string;
    retryLabel?: string;
    backLabel?: string | null;
  }>(),
  {
    failed: false,
    errorTitle: "うまく作れませんでした",
    errorMessage: "",
    retryLabel: "もう一度生成する",
    backLabel: null,
  },
);

defineEmits<{
  retry: [];
  back: [];
}>();
</script>

<template>
  <div class="generating-screen">
    <template v-if="!failed">
      <div
        class="generating-screen__spinner"
        aria-hidden="true"
      />
      <p
        class="generating-screen__message"
        role="status"
      >
        {{ message }}
      </p>
    </template>
    <template v-else>
      <div
        class="generating-screen__error-mark"
        aria-hidden="true"
      >
        !
      </div>
      <p class="generating-screen__error-title">
        {{ errorTitle }}
      </p>
      <p class="generating-screen__error-message">
        {{ errorMessage }}
      </p>
      <div class="generating-screen__actions">
        <AppButton
          variant="primary"
          @click="$emit('retry')"
        >
          {{ retryLabel }}
        </AppButton>
        <AppButton
          v-if="backLabel"
          variant="text"
          @click="$emit('back')"
        >
          {{ backLabel }}
        </AppButton>
      </div>
    </template>
  </div>
</template>

<style scoped>
.generating-screen {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-5) var(--layout-gutter);
  text-align: center;
}

.generating-screen__spinner {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 3px solid var(--surface-sub);
  border-top-color: var(--primary);
  animation: generating-screen-spin 1s linear infinite;
}

@keyframes generating-screen-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .generating-screen__spinner {
    animation-duration: 4s;
  }
}

.generating-screen__message {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
  text-wrap: balance;
}

.generating-screen__error-mark {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 3px solid var(--control-border);
  display: grid;
  place-items: center;
  color: var(--text-sub);
  font-size: 21px;
}

.generating-screen__error-title {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.generating-screen__error-message {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.generating-screen__actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-top: var(--space-1);
}
</style>
