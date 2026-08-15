<script setup lang="ts">
/**
 * S-11 現在地レポート開始。04_画面設計、06_ワイヤーフレーム(mockup.html s11())、09_API設計5.1。
 * 画面到達時にゲストセッションを発行する（ボタン操作ではなく mount 時）。
 * 失敗時の見た目は仕様に明記がないため、生成中画面(GeneratingScreen)と同じ
 * 「手動でのみ再試行する」方針をここでも踏襲した（自動リトライはしない）。
 */
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { createGuestSession } from "../api/guestSessions";

const router = useRouter();
const status = ref<"pending" | "ready" | "failed">("pending");

async function issueGuestSession(): Promise<void> {
  status.value = "pending";
  try {
    await createGuestSession();
    status.value = "ready";
  } catch {
    status.value = "failed";
  }
}

onMounted(issueGuestSession);

function start(): void {
  router.push("/s-12/career");
}
</script>

<template>
  <div class="s11">
    <AppHeaderFlow
      title="現在地レポート"
      :percent="0"
      left-action="cancel"
    />
    <div class="s11__body">
      <h1 class="s11__heading">
        いまの自分を、<br>眺めてみましょう
      </h1>
      <p class="s11__text">
        仕事、お金、からだ、人との関係。4つの領域について、いくつか質問します。5分ほどで終わります。
      </p>
      <div class="s11__card">
        <p class="s11__text">
          すぐには言葉にならない質問も、あるかもしれません。少し立ち止まって考えることになりますが、<b>そこで浮かんだことが、このあと作っていく「ありたい姿」の土台になります。</b>
        </p>
        <p class="s11__text">
          急がなくて大丈夫です。うまく答えようとしなくても、いまの気持ちに近いところを選んでいけば進みます。
        </p>
      </div>
      <p class="s11__sub">
        点数をつけたり、優劣を決めたりするものではありません。いまの状態を、自分の言葉にしていくための時間です。
      </p>
      <p
        v-if="status === 'failed'"
        class="s11__error"
      >
        うまく始められませんでした。もう一度試してみてください。
      </p>
    </div>
    <div class="s11__cta">
      <AppButton
        v-if="status !== 'failed'"
        :disabled="status === 'pending'"
        @click="start"
      >
        はじめる
      </AppButton>
      <AppButton
        v-else
        @click="issueGuestSession"
      >
        もう一度試す
      </AppButton>
    </div>
  </div>
</template>

<style scoped>
.s11 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s11__body {
  flex: 1 1 auto;
  padding: var(--space-5) var(--layout-gutter);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s11__heading {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.s11__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s11__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s11__sub {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s11__error {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s11__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}
</style>
