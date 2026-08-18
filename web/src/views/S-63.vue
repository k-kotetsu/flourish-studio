<script setup lang="ts">
/**
 * S-63 Weekly Reflection：結果。04_画面設計(screen-list.md S-63)、
 * 06_ワイヤーフレーム(wireframe-spec.md 7.6 / mockup.html s63())。
 * S-62が取得した結果をストアから読み、振り返り・気づき・次の一歩の3要素を表示する。
 * 「次の一歩」だけPrimaryで囲み、持ち帰るものを1つに絞る(wireframe-spec.md)。
 * 「今週の」と限定表記せず、`answered_at`の日付を添えて記録する(08_データモデル5.5)。
 * AI生成が成功した場合のみ到達する画面のため、状態バリエーションを持たない
 * (失敗はS-62側で使い切る、06_ワイヤーフレーム4.1と同じ考え方)。
 *
 * `safety_flag`が立った場合はS-16(P2-12)と同じ固定文面(SafetyNotice)を表示する
 * (ユーザー確認済み。依存にP7-1を明記していないP5-2だが、結果を表示する画面という
 * 点でS-16と同じ扱いにする判断とした)。
 */
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import SafetyNotice from "../components/SafetyNotice.vue";
import { useReflectionResultStore } from "../stores/reflectionResult";

const router = useRouter();
const resultStore = useReflectionResultStore();

onMounted(() => {
  // S-62を経ずに直接開かれた場合、結果を持っていないのでS-61からやり直す
  if (!resultStore.result) {
    router.replace("/s-61");
  }
});

function formatAnsweredAt(iso: string): string {
  const date = new Date(iso);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

function goHome(): void {
  router.push("/s-41");
}
</script>

<template>
  <div
    v-if="resultStore.result"
    class="s63"
  >
    <AppHeaderSingle
      title="今回の振り返り"
      left-action="none"
    />

    <div
      v-if="!resultStore.result.safety_flag"
      class="s63__body"
    >
      <div class="s63__card">
        <p class="s63__label">
          振り返り
        </p>
        <p class="s63__text">
          {{ resultStore.result.looking_back }}
        </p>
      </div>

      <div class="s63__card">
        <p class="s63__label">
          気づき
        </p>
        <p class="s63__text">
          {{ resultStore.result.insight }}
        </p>
      </div>

      <div class="s63__card s63__card--primary">
        <p class="s63__label">
          次の一歩
        </p>
        <p class="s63__text">
          {{ resultStore.result.next_step }}
        </p>
      </div>

      <p class="s63__recorded-at">
        {{ formatAnsweredAt(resultStore.result.answered_at) }} の記録として保存しました
      </p>
    </div>

    <SafetyNotice v-else />

    <div class="s63__cta">
      <AppButton @click="goHome">
        ホームへ
      </AppButton>
    </div>
  </div>
</template>

<style scoped>
.s63 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s63__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s63__card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s63__card--primary {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.s63__label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s63__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s63__recorded-at {
  margin: var(--space-2) 0 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s63__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}
</style>
