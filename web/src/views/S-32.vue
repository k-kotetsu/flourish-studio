<script setup lang="ts">
/**
 * S-32 ありたい姿：AI対話。04_画面設計(screen-list.md S-32)、09_API設計3.2・5.6、
 * 10_AIプロンプト設計4.3、06_ワイヤーフレーム(wireframe-spec.md 4章 / mockup.html s32())。
 *
 * 画面到達時(履歴が空のとき)にAI主導の1往復目を自動で開始する(4.3「1往復目は空」)。
 * 応答待ちは画面内のローディング(生成中画面を挟まない、screen-list.md S-32「応答待ち」)。
 * 失敗時は直近の発言位置にインラインでエラーと再送ボタンを出す。ユーザーの発言自体は
 * 消さない(破ってはいけない規則2)。3往復完了後も入力欄は残し、対話を続けられる
 * (wireframe-spec.md「ユーザーが続けたい場合を止めない」)。対話履歴はサーバーに残さず、
 * クライアントが保持して次のリクエストで全部送る(09_API設計3.2)。確定時(P3-8)に
 * まとめて保存する想定。
 *
 * 【判断】`done`イベントの`safety_flag`は現時点でUIに反映しない。S-16(P2-12)は
 * `safety_flag`が立ったときに相談窓口の固定文面(P7-1)へ切り替えるが、S-32については
 * そのような固定文面・画面仕様がこのタスクの参照範囲(4.3・5.6・flourish-api)に無く、
 * 対話中に何を表示するかは法務レビュー(P7-1相当)を要する別判断だと考えたため、
 * ここでは値を受け取るだけに留めた。
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { streamPurposeDialogue } from "../api/purposeDialogue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { usePurposeChoicesStore } from "../stores/purposeChoices";
import { usePurposeDialogueStore } from "../stores/purposeDialogue";

const router = useRouter();
const choicesStore = usePurposeChoicesStore();
const dialogueStore = usePurposeDialogueStore();

const hasValidChoices = computed(
  () =>
    choicesStore.values.length >= 1 &&
    choicesStore.fulfillingMoments.length >= 1 &&
    choicesStore.idealDailyLife !== null,
);

const composerText = ref("");
const waiting = ref(false);
const failed = ref(false);
const streamingText = ref("");
const messagesEnd = ref<HTMLElement | null>(null);
let controller: AbortController | null = null;

async function scrollToEnd(): Promise<void> {
  await nextTick();
  messagesEnd.value?.scrollIntoView({ block: "end" });
}

async function requestAiTurn(): Promise<void> {
  failed.value = false;
  waiting.value = true;
  streamingText.value = "";
  controller = new AbortController();

  try {
    const result = await streamPurposeDialogue(
      choicesStore.asChoices,
      dialogueStore.messages,
      {
        onDelta: (text) => {
          streamingText.value += text;
          scrollToEnd();
        },
      },
      controller.signal,
    );
    dialogueStore.addMessage({ role: "AI", body: streamingText.value });
    dialogueStore.setRemaining(result.remaining);
    waiting.value = false;
    scrollToEnd();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    failed.value = true;
    waiting.value = false;
    scrollToEnd();
  }
}

function sendMessage(): void {
  const body = composerText.value.trim();
  if (!body || waiting.value) return;
  dialogueStore.addMessage({ role: "USER", body });
  composerText.value = "";
  scrollToEnd();
  requestAiTurn();
}

function goBack(): void {
  router.push("/s-31");
}

function goToProposals(): void {
  router.push("/s-33");
}

onMounted(() => {
  if (!hasValidChoices.value) {
    router.replace("/s-31");
    return;
  }
  if (dialogueStore.messages.length === 0) {
    requestAiTurn();
  }
});

onUnmounted(() => {
  controller?.abort();
});
</script>

<template>
  <div
    v-if="hasValidChoices"
    class="s32"
  >
    <AppHeaderFlow
      title="ありたい姿"
      :percent="50"
      step="2 / 4"
      left-action="back"
      @back="goBack"
    />
    <div class="s32__body">
      <div class="s32__card">
        <p class="s32__intro">
          選んでいただいた内容をもとに、3回ほどやりとりします。うまく言葉にならなくても大丈夫です。
        </p>
      </div>

      <div class="s32__messages">
        <div
          v-for="(message, index) in dialogueStore.messages"
          :key="index"
          class="s32__msg"
          :class="message.role === 'AI' ? 's32__msg--ai' : 's32__msg--user'"
        >
          <div class="s32__bubble">
            {{ message.body }}
          </div>
        </div>

        <div
          v-if="waiting"
          class="s32__msg s32__msg--ai"
        >
          <div
            class="s32__bubble"
            role="status"
          >
            <span v-if="streamingText">{{ streamingText }}</span>
            <span
              v-else
              class="s32__typing"
              aria-label="返信を考えています"
            >
              <i /><i /><i />
            </span>
          </div>
        </div>

        <div
          v-if="failed"
          class="s32__error"
        >
          <p class="s32__error-text">
            うまく届きませんでした。書いていただいた内容はそのまま残っています。
          </p>
          <button
            type="button"
            class="s32__retry"
            @click="requestAiTurn"
          >
            もう一度送る
          </button>
        </div>

        <div ref="messagesEnd" />
      </div>

      <template v-if="dialogueStore.canCreateProposals">
        <div class="s32__rule" />
        <p class="s32__cta-note">
          ここまでで、だいぶ見えてきました！
        </p>
        <button
          type="button"
          class="s32__cta"
          @click="goToProposals"
        >
          候補を作る
        </button>
      </template>
    </div>

    <form
      class="s32__composer"
      @submit.prevent="sendMessage"
    >
      <input
        v-model="composerText"
        type="text"
        class="s32__composer-input"
        placeholder="メッセージを入力"
        aria-label="メッセージを入力"
        :disabled="waiting"
      >
      <button
        type="submit"
        class="s32__composer-send"
        aria-label="送信"
        :disabled="waiting || !composerText.trim()"
      >
        ↑
      </button>
    </form>
  </div>
</template>

<style scoped>
.s32 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s32__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s32__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s32__intro {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s32__messages {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s32__msg {
  display: flex;
}

.s32__msg--ai {
  justify-content: flex-start;
}

.s32__msg--user {
  justify-content: flex-end;
}

.s32__bubble {
  max-width: 85%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-card);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  white-space: pre-wrap;
}

.s32__msg--ai .s32__bubble {
  background: var(--surface-sub);
  color: var(--text);
}

.s32__msg--user .s32__bubble {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}

.s32__typing {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  min-height: 1em;
}

.s32__typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-faint);
  font-style: normal;
  animation: s32-typing-bounce 1.2s infinite ease-in-out;
}

.s32__typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.s32__typing i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes s32-typing-bounce {
  0%,
  60%,
  100% {
    opacity: 0.35;
  }
  30% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .s32__typing i {
    animation: none;
    opacity: 0.7;
  }
}

.s32__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
}

.s32__error-text {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s32__retry {
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-button);
  background: transparent;
  border: 1px solid var(--control-border);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-caption);
  font-weight: 500;
  cursor: pointer;
}

.s32__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s32__rule {
  height: 1px;
  background: var(--border);
}

.s32__cta-note {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s32__cta {
  width: 100%;
  min-height: var(--tap-target-min);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-button);
  border: none;
  background: var(--primary);
  color: var(--primary-ink);
  font-family: inherit;
  font-size: var(--font-size-body);
  font-weight: 600;
  cursor: pointer;
}

.s32__cta:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s32__composer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.s32__composer-input {
  flex: 1 1 auto;
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
}

.s32__composer-input::placeholder {
  color: var(--text-faint);
}

.s32__composer-input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s32__composer-send {
  flex: 0 0 auto;
  width: var(--tap-target-min);
  height: var(--tap-target-min);
  border-radius: 50%;
  border: none;
  background: var(--primary);
  color: var(--primary-ink);
  font-size: var(--font-size-body);
  cursor: pointer;
}

.s32__composer-send:disabled {
  background: var(--surface-sub);
  color: var(--text-faint);
  cursor: default;
}

.s32__composer-send:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
