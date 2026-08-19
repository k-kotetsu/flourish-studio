<script setup lang="ts">
/**
 * 4領域(Career/Financial/Physical/Social)の線画アイコン(P7-3、`07_デザイン原則`7.6)。
 * `AREA_ICONS`の形状データを描画するだけの表示専用コンポーネント。
 * 領域名(en/jp)のラベルと一緒に使う想定で、それ自体は情報を持たないため`aria-hidden`にする
 * (2.6「4領域の色分けはしない」ため`currentColor`のみで、領域固有の色は持たせない)。
 */
import { AREA_ICONS } from "../domain/areaIcons";
import type { Area } from "../domain/questions";

const props = withDefaults(
  defineProps<{
    area: Area;
    size?: number;
  }>(),
  {
    size: 20,
  },
);
</script>

<template>
  <svg
    class="area-icon"
    :viewBox="AREA_ICONS[props.area].viewBox"
    :width="props.size"
    :height="props.size"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template
      v-for="(el, i) in AREA_ICONS[props.area].elements"
      :key="i"
    >
      <path
        v-if="el.tag === 'path'"
        :d="el.d"
      />
      <circle
        v-else-if="el.tag === 'circle'"
        :cx="el.cx"
        :cy="el.cy"
        :r="el.r"
      />
      <rect
        v-else
        :x="el.x"
        :y="el.y"
        :width="el.width"
        :height="el.height"
        :rx="el.rx"
      />
    </template>
  </svg>
</template>

<style scoped>
.area-icon {
  flex-shrink: 0;
}
</style>
