<script setup lang="ts">
/**
 * S-50 最初の領域を選ぶ。04_画面設計(screen-list.md S-50)、05_質問・コンテンツ設計9.1、
 * 06_ワイヤーフレーム(wireframe-spec.md 1.1、mockup.html s50())。
 * オンボーディングでありたい姿の確定直後に一度だけ表示するハブ画面(S-35から`/s-50`遷移)。
 *
 * 完了条件「推奨や優先度を出さない」: 4領域をAREASの並び順のまま同列に表示し、
 * 順序の並べ替え・バッジ・Primaryによる強調のいずれも行わない
 * (05_質問・コンテンツ設計9.1「4領域を体験上も同列に扱うため」、flourish-ui「4領域に固有色を割り当てない」)。
 *
 * ヘッダーは戻る/中断のどちらも置かない(wireframe-spec.md 1.1「S-50 領域を選ぶ | − | Flourish Map | − | −」)。
 * P1-16時点ではS-41ホーム専用として作られたAppHeaderHubだが、「左アクションなし・中央タイトル・
 * 右スロットのみ」という骨格がS-50の見た目とそのまま一致するため、titleを差し替えて再利用した。
 */
import { useRouter } from "vue-router";
import AppHeaderHub from "../components/AppHeaderHub.vue";
import AreaIcon from "../components/AreaIcon.vue";
import { AREAS, AREA_META } from "../domain/questions";

const router = useRouter();

function selectArea(slug: string): void {
  router.push(`/s-51/${slug}`);
}

function skip(): void {
  router.push("/s-41");
}
</script>

<template>
  <div class="s50">
    <AppHeaderHub title="Flourish Map" />
    <div class="s50__body">
      <h1 class="s50__heading">
        どこから<br>育てはじめますか
      </h1>
      <p class="s50__text">
        ひとつだけ選んでください。あとから他の領域も作れます。
      </p>
      <div class="s50__grid">
        <button
          v-for="area in AREAS"
          :key="area"
          type="button"
          class="s50__card"
          @click="selectArea(AREA_META[area].slug)"
        >
          <AreaIcon
            :area="area"
            :size="24"
          />
          <span class="s50__card-en">{{ AREA_META[area].en }}</span>
          <span class="s50__card-jp">{{ AREA_META[area].jp }}</span>
        </button>
      </div>
      <button
        type="button"
        class="s50__skip"
        @click="skip"
      >
        あとで
      </button>
    </div>
  </div>
</template>

<style scoped>
.s50 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s50__body {
  flex: 1 1 auto;
  padding: var(--space-5) var(--layout-gutter);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s50__heading {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
  text-wrap: balance;
}

.s50__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  color: var(--text-sub);
}

.s50__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.s50__card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-4) var(--space-3);
  min-height: var(--tap-target-min);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  font-family: inherit;
  cursor: pointer;
}

.s50__card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.s50__card-en {
  font-size: var(--font-size-section);
  font-weight: 600;
  font-family: var(--font-latin);
}

.s50__card-jp {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s50__skip {
  align-self: center;
  background: transparent;
  border: none;
  padding: var(--space-2) var(--space-3);
  min-height: var(--tap-target-min);
  font-family: inherit;
  font-size: var(--font-size-body);
  font-weight: 500;
  color: var(--text-sub);
  cursor: pointer;
}

.s50__skip:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
