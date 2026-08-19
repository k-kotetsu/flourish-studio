<script setup lang="ts">
/**
 * S-41 ホーム。04_画面設計(screen-list.md S-41)、09_API設計5.9、
 * 06_ワイヤーフレーム(wireframe-spec.md 5章「S-41 ホーム」)、07_デザイン原則 原則2。
 *
 * `GET /home`で、ありたい姿・4領域の状態・振り返り導線の可否・テーマ設定を1回で取得する。
 * 「未完成」「空欄」という語は使わず、未作成の領域は破線カード＋「これから育てる」表現で示す
 * (原則2、wireframe-spec.md「未完成・空欄という語は使わない」)。
 *
 * 【判断】テーマ切替トグル（P4-9）は`AppHeaderHub`の`right`スロットに差し込む。
 * `GET /home`が返す`theme_preference`をマウント時に`themeStore.syncFromServer`へ渡し、
 * アカウントに保存された選択を端末をまたいで一致させる(07_デザイン原則3.1)。
 * 【判断】記事・ツールカードの遷移先画面はscreen-list.mdが「作らない」と明記しているため、
 * クリックハンドラを持たせず`<div>`のまま「準備中」ラベルのみを表示する。
 * 【判断】`ideal_state_summary`はサーバー側で切り詰めていない(`app/domain/home.py`の判断)。
 * カード内の見た目の省略は`line-clamp`で行い、元の文字列自体は保持する
 * (破ってはいけない規則2「ユーザーの言葉を消さない」)。
 * 【判断】`purpose`が`null`(通常の導線では到達しない。S-35を経ないとS-41に来られないため)の場合、
 * ありたい姿カード自体を表示しない防御的な扱いとした。
 */
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { messageForCode } from "../api/errorMessages";
import { getHome, type HomeResponse } from "../api/home";
import AppButton from "../components/AppButton.vue";
import AppHeaderHub from "../components/AppHeaderHub.vue";
import ThemeToggle from "../components/ThemeToggle.vue";
import { AREA_META, type Area } from "../domain/questions";
import { useThemeStore } from "../stores/theme";

const router = useRouter();
const themeStore = useThemeStore();
const home = ref<HomeResponse | null>(null);
const errorMessage = ref("");

onMounted(async () => {
  try {
    home.value = await getHome();
    themeStore.syncFromServer(home.value.theme_preference);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? messageForCode(error.code) : messageForCode("NETWORK_ERROR");
  }
});

function goToPurpose(): void {
  router.push("/s-36");
}

function goToArea(area: Area, status: "EMPTY" | "CREATED"): void {
  const slug = AREA_META[area].slug;
  router.push(status === "CREATED" ? `/s-57/${slug}` : `/s-51/${slug}`);
}

function goToReflection(): void {
  router.push("/s-61");
}
</script>

<template>
  <div class="s41">
    <AppHeaderHub title="Flourish Studio">
      <template #right>
        <ThemeToggle />
      </template>
    </AppHeaderHub>

    <div
      v-if="home"
      class="s41__body"
    >
      <button
        v-if="home.purpose"
        type="button"
        class="s41__purpose-card"
        @click="goToPurpose"
      >
        <p class="s41__label">
          ありたい姿
        </p>
        <p class="s41__purpose-statement">
          {{ home.purpose.statement }}
        </p>
      </button>

      <div class="s41__areas">
        <button
          v-for="area in home.areas"
          :key="area.area"
          type="button"
          class="s41__area-card"
          :class="{ 's41__area-card--empty': area.status === 'EMPTY' }"
          @click="goToArea(area.area, area.status)"
        >
          <span class="s41__area-en">{{ AREA_META[area.area].en }}</span>
          <span class="s41__area-jp">{{ AREA_META[area.area].jp }}</span>
          <p
            v-if="area.status === 'CREATED'"
            class="s41__area-summary"
          >
            {{ area.ideal_state_summary }}
          </p>
          <p
            v-else
            class="s41__area-summary s41__area-summary--empty"
          >
            これから育てる領域
          </p>
          <span
            v-if="area.status === 'CREATED'"
            class="s41__area-goal-count"
          >目標 {{ area.goal_count }}個</span>
        </button>
      </div>

      <div class="s41__reflection">
        <AppButton
          :disabled="!home.reflection_available"
          @click="goToReflection"
        >
          振り返りをする
        </AppButton>
        <p
          v-if="!home.reflection_available"
          class="s41__reflection-hint"
        >
          目標を1つ作ると振り返れるようになります
        </p>
      </div>

      <div class="s41__promo-row">
        <div class="s41__promo-card">
          <span class="s41__promo-badge">準備中</span>
          <span class="s41__promo-label">記事</span>
        </div>
        <div class="s41__promo-card">
          <span class="s41__promo-badge">準備中</span>
          <span class="s41__promo-label">ツール</span>
        </div>
      </div>
    </div>

    <p
      v-else-if="errorMessage"
      class="s41__error"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped>
.s41 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s41__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s41__label {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s41__purpose-card {
  text-align: left;
  background: var(--surface-sub);
  border: none;
  border-radius: var(--radius-card);
  padding: var(--space-3);
  cursor: pointer;
  font-family: inherit;
}

.s41__purpose-card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s41__purpose-statement {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
  text-wrap: balance;
}

.s41__areas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.s41__area-card {
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  min-height: var(--tap-target-min);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-family: inherit;
  cursor: pointer;
}

.s41__area-card--empty {
  border-style: dashed;
}

.s41__area-card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s41__area-en {
  font-size: var(--font-size-body);
  font-weight: 600;
  font-family: var(--font-latin);
}

.s41__area-jp {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s41__area-summary {
  margin: 0;
  font-size: var(--font-size-caption);
  line-height: var(--line-height-caption);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.s41__area-summary--empty {
  color: var(--text-sub);
}

.s41__area-goal-count {
  margin-top: auto;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s41__reflection {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s41__reflection-hint {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s41__promo-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.s41__promo-card {
  background: var(--surface-sub);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  min-height: var(--tap-target-min);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  color: var(--text-faint);
}

.s41__promo-badge {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s41__promo-label {
  font-size: var(--font-size-body);
  font-weight: 600;
}

.s41__error {
  margin: var(--space-4) var(--layout-gutter);
  font-size: var(--font-size-caption);
  color: var(--danger);
  line-height: var(--line-height-caption);
}
</style>
