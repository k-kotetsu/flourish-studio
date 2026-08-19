<script setup lang="ts">
/**
 * S-02 ログイン。04_画面設計(screen-list.md S-02)、09_API設計5.5.1。
 * 再訪ユーザー専用、プログレスバーなし(06_ワイヤーフレーム wireframe-spec.md)。
 * 成功 → S-41(ホーム)。失敗 → 同画面にエラー表示、入力内容は消さない(破ってはいけない規則2)。
 */
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { login } from "../api/auth";
import { messageForCode } from "../api/errorMessages";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";

const router = useRouter();
const email = ref("");
const password = ref("");
const status = ref<"idle" | "pending" | "failed">("idle");
const errorMessage = ref("");

async function submit(): Promise<void> {
  status.value = "pending";
  try {
    await login(email.value, password.value);
    router.push("/s-41");
  } catch (error) {
    status.value = "failed";
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}

function goToTop(): void {
  router.push("/");
}
</script>

<template>
  <div class="s02">
    <AppHeaderSingle
      title="ログイン"
      @back="goToTop"
    />
    <form
      class="s02__body"
      @submit.prevent="submit"
    >
      <div class="s02__field">
        <label
          class="s02__label"
          for="s02-email"
        >メールアドレス</label>
        <input
          id="s02-email"
          v-model="email"
          class="s02__input"
          type="email"
          autocomplete="email"
          required
        >
      </div>
      <div class="s02__field">
        <label
          class="s02__label"
          for="s02-password"
        >パスワード</label>
        <input
          id="s02-password"
          v-model="password"
          class="s02__input"
          type="password"
          autocomplete="current-password"
          required
        >
      </div>
      <p
        v-if="status === 'failed'"
        class="s02__error"
      >
        {{ errorMessage }}
      </p>
      <AppButton
        type="submit"
        :disabled="status === 'pending'"
      >
        ログイン
      </AppButton>
    </form>
    <div class="s02__footer">
      <AppButton
        variant="text"
        @click="goToTop"
      >
        トップに戻る
      </AppButton>
      <p class="s02__legal">
        <a href="/terms-of-service">利用規約</a>
        ／
        <a href="/privacy-policy">プライバシーポリシー</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.s02 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s02__body {
  flex: 1 1 auto;
  padding: var(--space-5) var(--layout-gutter);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s02__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s02__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s02__input {
  width: 100%;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
}

.s02__input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s02__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s02__footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--layout-gutter) var(--space-5);
}

.s02__legal {
  margin: 0;
  font-size: var(--font-size-caption);
  line-height: var(--line-height-caption);
  color: var(--text-sub);
}

.s02__legal a {
  color: var(--primary);
}

.s02__legal a:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
