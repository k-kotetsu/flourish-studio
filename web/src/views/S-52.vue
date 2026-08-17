<script setup lang="ts">
/**
 * S-52 領域：AI対話。04_画面設計(screen-list.md S-52)、09_API設計6章、10_AIプロンプト設計4.5、
 * 05_質問・コンテンツ設計9.3、06_ワイヤーフレーム(wireframe-spec.md 1.1/4章、mockup.html s52())。
 * S-32(P3-6)と同じ型のチャットUIを、4領域共通の1画面としてルートパラメータ(:area)で切り替える
 * (S-51・P2-3が確立した設計)。
 *
 * 上部に確定済みの「ありたい姿」を常時表示する(9.2)。S-51と同じく`GET /purposes/current`を
 * 独自に取得する(表示専用。AI対話自体に渡す「ありたい姿」はサーバーが`PURPOSE#CURRENT`から
 * 読むため、クライアントからは送らない。`ai_area_dialogue.py`の判断)。
 *
 * 画面到達時(履歴が空のとき)にAI主導の1往復目を自動で開始する(4.5「P-03と同じルール」)。
 * 応答待ちは画面内のローディング(生成中画面を挟まない、S-32と同じ扱い)。失敗時は直近の
 * 発言位置にインラインでエラーと再送ボタンを出す。ユーザーの発言自体は消さない
 * (破ってはいけない規則2)。2往復完了後も入力欄は残し、対話を続けられる(S-32と同じ)。
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { streamAreaDialogue } from "../api/areaDialogue";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getCurrentPurpose, type PurposeResponse } from "../api/purposes";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { AREA_META, areaFromSlug } from "../domain/questions";
import { useAreaChoicesStore } from "../stores/areaChoices";
import { useAreaDialogueStore } from "../stores/areaDialogue";

const route = useRoute();
const router = useRouter();
const choicesStore = useAreaChoicesStore();
const dialogueStore = useAreaDialogueStore();

const area = areaFromSlug(String(route.params.area));
const meta = area ? AREA_META[area] : null;

const hasValidChoices = computed(
  () =>
    area !== null &&
    choicesStore.area === area &&
    choicesStore.changeItemCode !== null &&
    choicesStore.values.length >= 1 &&
    choicesStore.positions.length >= 1,
);

const purpose = ref<PurposeResponse | null>(null);
const purposeErrorMessage = ref("");

async function fetchPurpose(): Promise<void> {
  try {
    purpose.value = await getCurrentPurpose();
  } catch (error) {
    purposeErrorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
}

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
  if (!area) return;
  failed.value = false;
  waiting.value = true;
  streamingText.value = "";
  controller = new AbortController();

  try {
    const result = await streamAreaDialogue(
      area,
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
  if (!area) return;
  router.push(`/s-51/${AREA_META[area].slug}`);
}

function goToProposals(): void {
  if (!area) return;
  router.push(`/s-53/${AREA_META[area].slug}`);
}

onMounted(() => {
  if (!area) {
    // 未知の領域パラメータで直接開かれた場合、この画面フローの入口(S-50)へ戻す
    router.replace("/s-50");
    return;
  }
  if (!hasValidChoices.value) {
    // S-51を経ずに直接開かれた場合、その領域のS-51へ差し戻す(S-13/S-14と同じガードの型)
    router.replace(`/s-51/${AREA_META[area].slug}`);
    return;
  }
  fetchPurpose();
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
    v-if="meta"
    class="s52"
  >
    <AppHeaderFlow
      :title="meta.en"
      :percent="40"
      step="2 / 5"
      left-action="back"
      @back="goBack"
    />

    <div
      v-if="purpose"
      class="s52__body"
    >
      <div class="s52__card">
        <p class="s52__purpose-label">
          ありたい姿
        </p>
        <p class="s52__purpose-statement">
          {{ purpose.statement }}
        </p>
      </div>

      <div class="s52__messages">
        <div
          v-for="(message, index) in dialogueStore.messages"
          :key="index"
          class="s52__msg"
          :class="message.role === 'AI' ? 's52__msg--ai' : 's52__msg--user'"
        >
          <div class="s52__bubble">
            {{ message.body }}
          </div>
        </div>

        <div
          v-if="waiting"
          class="s52__msg s52__msg--ai"
        >
          <div
            class="s52__bubble"
            role="status"
          >
            <span v-if="streamingText">{{ streamingText }}</span>
            <span
              v-else
              class="s52__typing"
              aria-label="返信を考えています"
            >
              <i /><i /><i />
            </span>
          </div>
        </div>

        <div
          v-if="failed"
          class="s52__error"
        >
          <p class="s52__error-text">
            うまく届きませんでした。書いていただいた内容はそのまま残っています。
          </p>
          <button
            type="button"
            class="s52__retry"
            @click="requestAiTurn"
          >
            もう一度送る
          </button>
        </div>

        <div ref="messagesEnd" />
      </div>

      <template v-if="dialogueStore.canCreateIdealState">
        <div class="s52__rule" />
        <button
          type="button"
          class="s52__cta"
          @click="goToProposals"
        >
          理想の状態を作る
        </button>
      </template>
    </div>

    <p
      v-else-if="purposeErrorMessage"
      class="s52__error-standalone"
    >
      {{ purposeErrorMessage }}
    </p>

    <form
      v-if="purpose"
      class="s52__composer"
      @submit.prevent="sendMessage"
    >
      <input
        v-model="composerText"
        type="text"
        class="s52__composer-input"
        placeholder="メッセージを入力"
        aria-label="メッセージを入力"
        :disabled="waiting"
      >
      <button
        type="submit"
        class="s52__composer-send"
        aria-label="送信"
        :disabled="waiting || !composerText.trim()"
      >
        ↑
      </button>
    </form>
  </div>
</template>

<style scoped>
.s52 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s52__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s52__card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
}

.s52__purpose-label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s52__purpose-statement {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s52__messages {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s52__msg {
  display: flex;
}

.s52__msg--ai {
  justify-content: flex-start;
}

.s52__msg--user {
  justify-content: flex-end;
}

.s52__bubble {
  max-width: 85%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-card);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  white-space: pre-wrap;
}

.s52__msg--ai .s52__bubble {
  background: var(--surface-sub);
  color: var(--text);
}

.s52__msg--user .s52__bubble {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}

.s52__typing {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  min-height: 1em;
}

.s52__typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-faint);
  font-style: normal;
  animation: s52-typing-bounce 1.2s infinite ease-in-out;
}

.s52__typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.s52__typing i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes s52-typing-bounce {
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
  .s52__typing i {
    animation: none;
    opacity: 0.7;
  }
}

.s52__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
}

.s52__error-text {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s52__retry {
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

.s52__retry:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s52__rule {
  height: 1px;
  background: var(--border);
}

.s52__cta {
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

.s52__cta:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s52__error-standalone {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}

.s52__composer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.s52__composer-input {
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

.s52__composer-input::placeholder {
  color: var(--text-faint);
}

.s52__composer-input:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s52__composer-send {
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

.s52__composer-send:disabled {
  background: var(--surface-sub);
  color: var(--text-faint);
  cursor: default;
}

.s52__composer-send:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
