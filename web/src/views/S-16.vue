<script setup lang="ts">
/**
 * S-16 現在地レポート結果。04_画面設計(screen-list.md S-16)、05_質問・コンテンツ設計5章、
 * 06_ワイヤーフレーム(wireframe-spec.md 3章 / mockup.html s16())。
 * S-15が取得した結果をストアから読み、上から下へ「軽い→真面目」の構成で表示する:
 * あだ名(エンタメ) → 4領域の整理 → 言語化度・コミット度 → 締め。
 * 未登録のまま全文を表示する(認証不要)。AI生成が成功した場合のみ到達する画面のため、
 * 状態バリエーションを持たない(失敗はS-15側で使い切る、06_ワイヤーフレーム3章)。
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import { GROWTH_STAGES, GROWTH_STAGE_LABELS } from "../domain/growthStage";
import { AREAS, AREA_META } from "../domain/questions";
import { useAssessmentResultStore } from "../stores/assessmentResult";

const router = useRouter();
const resultStore = useAssessmentResultStore();

// モーション(登場・点灯)は`prefers-reduced-motion: reduce`のときは付けない。
// デフォルト(クラスなし)は常に最終状態(不透明・点灯済み)で描画されるため、これが遅れても表示は崩れない。
const animate = ref(false);

onMounted(() => {
  // S-15を経ずに直接開かれた場合、結果を持っていないのでS-11からやり直す
  if (!resultStore.result) {
    router.replace("/s-11");
    return;
  }
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    animate.value = true;
  }
});

const orderedAreas = computed(() => {
  const result = resultStore.result;
  if (!result) return [];
  return AREAS.map((area) => result.areas.find((a) => a.area === area)).filter(
    (a): a is NonNullable<typeof a> => a != null,
  );
});

function goNext(): void {
  router.push("/s-21");
}
</script>

<template>
  <div
    v-if="resultStore.result"
    class="s16"
  >
    <AppHeaderFlow
      title="あなたの現在地"
      :percent="100"
      step="6 / 6"
      left-action="none"
    />
    <div class="s16__body">
      <div
        class="s16__nickname"
        :class="{ 's16__nickname--enter': animate }"
      >
        <p class="s16__nickname-lead">
          今の状態のあなたを、あえて一言で表すと
        </p>
        <p class="s16__nickname-main">
          {{ resultStore.result.nickname }}
        </p>
        <p class="s16__nickname-lead">
          でしょうか。
        </p>
        <p class="s16__nickname-disclaimer">
          ※ あくまで参考です。これがあなたを表すものではありません。
        </p>
      </div>

      <div class="s16__rule" />

      <div
        v-for="area in orderedAreas"
        :key="area.area"
        class="s16__card"
      >
        <div class="s16__area-heading">
          <span class="s16__area-en">{{ AREA_META[area.area].en }}</span>
          <span class="s16__area-jp">{{ AREA_META[area.area].jp }}</span>
        </div>
        <div class="s16__area-block">
          <p class="s16__label">
            満たされている点
          </p>
          <p class="s16__text">
            {{ area.satisfied_text }}
          </p>
        </div>
        <div class="s16__area-block">
          <p class="s16__label">
            気になっている点
          </p>
          <p class="s16__text">
            {{ area.concern_text }}
          </p>
        </div>
        <div class="s16__area-block">
          <p class="s16__label">
            これからできそうなこと
          </p>
          <p class="s16__text">
            {{ area.advice_text }}
          </p>
        </div>
      </div>

      <div class="s16__card s16__card--sunk">
        <p class="s16__label">
          言語化度
        </p>
        <p class="s16__stage-desc">
          自分の考えが、どのくらい自分の言葉になっているか
        </p>
        <div
          class="s16__stages"
          role="img"
          :aria-label="`言語化度: ${GROWTH_STAGE_LABELS[resultStore.result.articulation_stage]}`"
        >
          <div
            v-for="stage in GROWTH_STAGES"
            :key="stage"
            class="s16__stage"
            :class="{
              's16__stage--on': stage === resultStore.result.articulation_stage,
              's16__stage--enter': animate,
            }"
          >
            <span
              class="s16__stage-dot"
              aria-hidden="true"
            />
            <span class="s16__stage-name">{{ GROWTH_STAGE_LABELS[stage] }}</span>
          </div>
        </div>

        <div class="s16__stage-gap" />

        <p class="s16__label">
          コミット度
        </p>
        <p class="s16__stage-desc">
          考えていることを、どのくらい行動につなげられているか
        </p>
        <div
          class="s16__stages"
          role="img"
          :aria-label="`コミット度: ${GROWTH_STAGE_LABELS[resultStore.result.commitment_stage]}`"
        >
          <div
            v-for="stage in GROWTH_STAGES"
            :key="stage"
            class="s16__stage"
            :class="{
              's16__stage--on': stage === resultStore.result.commitment_stage,
              's16__stage--enter': animate,
            }"
          >
            <span
              class="s16__stage-dot"
              aria-hidden="true"
            />
            <span class="s16__stage-name">{{ GROWTH_STAGE_LABELS[stage] }}</span>
          </div>
        </div>
      </div>

      <p class="s16__closing">
        ここまでは、いまの自分をそっと眺めてみた時間でした。
        <br><br>
        気になっていることは、そのままにしておくと、来年も同じ場所で待っていることが多いものです。動きはじめられるのは、それが「自分にとってなぜ大事なのか」とつながったときかもしれません。
        <br><br>
        Flourish Mapでは、仕事も、お金も、からだも、人とのつながりも、バラバラの悩みとしてではなく、ひとつの「ありたい姿」につなげて考えていきます。4つがつながったとき、進み方が変わっていきます。
        <br><br>
        次は、あなたが3〜5年後にどうありたいか。一緒に言葉にしていきましょう。
      </p>
    </div>

    <div class="s16__cta">
      <AppButton @click="goNext">
        ありたい姿を作る
      </AppButton>
    </div>
  </div>
</template>

<style scoped>
.s16 {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.s16__body {
  flex: 1 1 auto;
  padding: var(--space-4) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.s16__nickname {
  padding: var(--space-2) 0;
  text-align: center;
  opacity: 1;
  transform: none;
}

.s16__nickname--enter {
  animation: s16-nickname-in 520ms cubic-bezier(0.2, 0.85, 0.25, 1) both;
}

@keyframes s16-nickname-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.s16__nickname-lead {
  margin: 0;
  font-size: var(--font-size-body);
  color: var(--text-sub);
  line-height: var(--line-height-body);
}

.s16__nickname-main {
  margin: var(--space-2) 0;
  font-size: var(--font-size-nickname);
  font-weight: 700;
  line-height: var(--line-height-nickname);
  text-wrap: balance;
}

.s16__nickname-disclaimer {
  margin: var(--space-3) 0 0;
  font-size: var(--font-size-label);
  color: var(--text-faint);
}

.s16__rule {
  height: 1px;
  background: var(--border);
}

.s16__card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.s16__card--sunk {
  background: var(--surface-sub);
  border: none;
}

.s16__area-heading {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.s16__area-en {
  font-size: var(--font-size-section);
  font-weight: 600;
  font-family: var(--font-latin);
}

.s16__area-jp {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s16__area-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.s16__label {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-sub);
}

.s16__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s16__stage-desc {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}

.s16__stages {
  display: flex;
  gap: var(--space-2);
}

.s16__stage {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.s16__stage-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1.6px solid var(--control-border);
}

.s16__stage-name {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
}

.s16__stage--on .s16__stage-dot {
  background: var(--primary);
  border-color: var(--primary);
}

.s16__stage--on .s16__stage-name {
  color: var(--text);
  font-weight: 700;
}

.s16__stage--on.s16__stage--enter .s16__stage-dot {
  animation: s16-stage-glow 480ms cubic-bezier(0.34, 1.56, 0.5, 1) both;
}

@keyframes s16-stage-glow {
  from {
    transform: scale(0.75);
    opacity: 0.6;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.s16__stage-gap {
  height: var(--space-2);
}

.s16__closing {
  margin: 0;
  padding: var(--space-1) 2px;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.s16__cta {
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--border);
  background: var(--surface);
}

@media (prefers-reduced-motion: reduce) {
  .s16__nickname--enter,
  .s16__stage--on.s16__stage--enter .s16__stage-dot {
    animation: none;
  }
}
</style>
