<script setup lang="ts">
/**
 * S-21 アカウント登録。04_画面設計(screen-list.md S-21)、09_API設計5.5、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.3 / mockup.html s21())。
 * 成功時は完了画面を挟まずS-31へ(screen-list.md「成功時」)。失敗時は同画面に
 * エラー表示、入力内容は消さない(破ってはいけない規則2)。
 * `fs_guest`があればサーバー側でゲストの現在地レポートをアカウントへ紐付け直す
 * (09_API設計5.5「クライアントからゲストIDを送る必要はない」)ため、
 * クライアント側はメールアドレス・パスワードだけを送る。
 * 同意文言のリンク先(利用規約・プライバシーポリシー)はP7-2で実装済み。
 */
import { ref } from "vue";
import { useRouter } from "vue-router";
import { register } from "../api/auth";
import { ApiError } from "../api/client";
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
    await register(email.value, password.value);
    router.push("/s-31");
  } catch (error) {
    status.value = "failed";
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}

function goBack(): void {
  router.push("/s-16");
}
</script>

<template>
  <div class="s21">
    <AppHeaderSingle
      title="アカウント登録"
      @back="goBack"
    />
    <form
      class="s21__form"
      @submit.prevent="submit"
    >
      <div class="s21__body">
        <h1 class="s21__heading">
          ここから先は、<br>書いたことが残ります
        </h1>
        <p class="s21__text">
          いま作ったレポートも一緒に保存されます。あとから見返したり、続きから育てたりできます。
        </p>
        <div class="s21__field">
          <label
            class="s21__label"
            for="s21-email"
          >メールアドレス</label>
          <input
            id="s21-email"
            v-model="email"
            class="s21__input"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            required
          >
        </div>
        <div class="s21__field">
          <label
            class="s21__label"
            for="s21-password"
          >パスワード</label>
          <input
            id="s21-password"
            v-model="password"
            class="s21__input"
            type="password"
            autocomplete="new-password"
            placeholder="8文字以上"
            minlength="8"
            required
          >
        </div>
        <p
          v-if="status === 'failed'"
          class="s21__error"
        >
          {{ errorMessage }}
        </p>
        <p class="s21__consent">
          登録すると、<a href="/terms-of-service">利用規約</a>と<a href="/privacy-policy">プライバシーポリシー</a>に同意したものとみなされます。
        </p>
      </div>
      <div class="s21__cta">
        <AppButton
          type="submit"
          :disabled="status === 'pending'"
        >
          登録してはじめる
        </AppButton>
      </div>
    </form>
  </div>
</template>

<style scoped>
.s21 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s21__form {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}

.s21__body {
  flex: 1 1 auto;
  padding: var(--space-5) var(--layout-gutter);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s21__heading {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.s21__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s21__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s21__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s21__input {
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

.s21__input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s21__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s21__consent {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s21__consent a {
  color: var(--primary);
}

.s21__consent a:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s21__cta {
  padding: var(--space-3) var(--layout-gutter) var(--space-5);
  border-top: 1px solid var(--border);
  background: var(--surface);
}
</style>
