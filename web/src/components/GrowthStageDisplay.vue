<script setup lang="ts">
/**
 * 07_デザイン原則 7.7。言語化度・コミット度が共有する成長段階(種・芽・苗・木)の表示。
 * 4段階すべてを並べ、該当する現在地だけを`--primary`で塗る(7.7、4章のPrimary使用可否表
 * 「成長段階の現在位置」)。数値は出さない。
 * 点灯アニメーションは種側から現在地へ光が到達する動きにし、現在地で止まる(10.2)。
 * `prefers-reduced-motion`ではアニメーションを付けず、現在地が点灯済みの最終状態を即座に表示する。
 */
import { computed, onMounted, ref } from "vue";
import {
  GROWTH_STAGES,
  GROWTH_STAGE_ICONS,
  GROWTH_STAGE_LABELS,
  type GrowthStage,
} from "../domain/growthStage";

const props = defineProps<{
  axisName: string;
  axisDescription: string;
  stage: GrowthStage;
}>();

const animate = ref(false);

onMounted(() => {
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    animate.value = true;
  }
});

const currentIndex = computed(() => GROWTH_STAGES.indexOf(props.stage));

// 現在地(currentIndex)だけが最終的に点灯する。それより手前の段階は、光が種側から
// 現在地へ通り過ぎていく演出として一瞬灯ってから元に戻る(`--pass`)。現在地は
// 灯ったまま止まる(`--arrive`)。
function isPassing(index: number): boolean {
  return index < currentIndex.value;
}

function isArrival(index: number): boolean {
  return index === currentIndex.value;
}
</script>

<template>
  <div class="growth-stage-display">
    <p class="growth-stage-display__axis-name">
      {{ axisName }}
    </p>
    <p class="growth-stage-display__axis-desc">
      {{ axisDescription }}
    </p>
    <div
      class="growth-stage-display__stages"
      role="img"
      :aria-label="`${axisName}: ${GROWTH_STAGE_LABELS[stage]}`"
    >
      <div
        v-for="(s, index) in GROWTH_STAGES"
        :key="s"
        class="growth-stage-display__stage"
        :class="{
          'growth-stage-display__stage--lit': isArrival(index),
          'growth-stage-display__stage--pass': animate && isPassing(index),
          'growth-stage-display__stage--arrive': animate && isArrival(index),
        }"
        :style="
          animate && (isPassing(index) || isArrival(index))
            ? { animationDelay: `${index * 120}ms` }
            : undefined
        "
      >
        <svg
          class="growth-stage-display__icon"
          :viewBox="GROWTH_STAGE_ICONS[s].viewBox"
          aria-hidden="true"
        >
          <path
            v-for="(d, i) in GROWTH_STAGE_ICONS[s].paths"
            :key="i"
            :d="d"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span class="growth-stage-display__label">{{ GROWTH_STAGE_LABELS[s] }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.growth-stage-display__axis-name {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: var(--letter-spacing-label);
  color: var(--text-sub);
}

.growth-stage-display__axis-desc {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.growth-stage-display__stages {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.growth-stage-display__stage {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  color: var(--control-border);
}

.growth-stage-display__icon {
  width: 28px;
  height: 28px;
}

.growth-stage-display__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.growth-stage-display__stage--lit {
  color: var(--primary);
}

.growth-stage-display__stage--lit .growth-stage-display__label {
  color: var(--text);
  font-weight: 700;
}

.growth-stage-display__stage--pass {
  animation: growth-stage-display-pass 260ms ease-in-out;
}

@keyframes growth-stage-display-pass {
  0%,
  100% {
    color: var(--control-border);
  }
  50% {
    color: var(--primary);
  }
}

.growth-stage-display__stage--arrive {
  animation: growth-stage-display-arrive 320ms cubic-bezier(0.34, 1.56, 0.5, 1) both;
}

@keyframes growth-stage-display-arrive {
  from {
    color: var(--control-border);
    transform: scale(0.75);
  }
  to {
    color: var(--primary);
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .growth-stage-display__stage--pass,
  .growth-stage-display__stage--arrive {
    animation: none;
  }
}
</style>
