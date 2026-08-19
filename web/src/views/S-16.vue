<script setup lang="ts">
/**
 * S-16 現在地レポート結果。04_画面設計(screen-list.md S-16)、05_質問・コンテンツ設計5章、
 * 06_ワイヤーフレーム(wireframe-spec.md 3章 / mockup.html s16())。
 * S-15が取得した結果をストアから読み、上から下へ「軽い→真面目」の構成で表示する:
 * あだ名(エンタメ) → 4領域の整理 → 言語化度・コミット度 → 締め。
 * 未登録のまま全文を表示する(認証不要)。AI生成が成功した場合のみ到達する画面のため、
 * 状態バリエーションを持たない(失敗はS-15側で使い切る、06_ワイヤーフレーム3章)。
 *
 * `safety_flag`が立った場合は評価(あだ名・4領域の整理・言語化度)を表示せず、
 * 代わりに相談窓口の固定文面を表示する(10_AIプロンプト設計3.7「フラグが立った
 * 領域については、評価・課題の指摘・目標の提案を行わない」「相談窓口の案内は
 * 画面側が行う」、P2-12、文面はP7-1 `docs/14_法務文書/safety-consultation.md`)。
 * CTA・ナビゲーションは置かない。ホーム(S-41)がP4-8まで未実装で適切な戻り先を
 * 示せないため。
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppButton from "../components/AppButton.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import AreaIcon from "../components/AreaIcon.vue";
import GrowthStageDisplay from "../components/GrowthStageDisplay.vue";
import SafetyNotice from "../components/SafetyNotice.vue";
import { AREAS, AREA_META } from "../domain/questions";
import { useAssessmentResultStore } from "../stores/assessmentResult";

const router = useRouter();
const resultStore = useAssessmentResultStore();

// あだ名の登場アニメーションは`prefers-reduced-motion: reduce`のときは付けない。
// デフォルト(クラスなし)は常に最終状態(不透明)で描画されるため、これが遅れても表示は崩れない。
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

const isSafetyFlagged = computed(() => resultStore.result?.safety_flag ?? false);

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
    <div
      v-if="!isSafetyFlagged"
      class="s16__body"
    >
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
          <AreaIcon :area="area.area" />
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
        <GrowthStageDisplay
          axis-name="言語化度"
          axis-description="自分の考えが、どのくらい自分の言葉になっているか"
          :stage="resultStore.result.articulation_stage"
        />

        <div class="s16__stage-gap" />

        <GrowthStageDisplay
          axis-name="コミット度"
          axis-description="考えていることを、どのくらい行動につなげられているか"
          :stage="resultStore.result.commitment_stage"
        />
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

    <!--
      safety_flagが立った場合の表示。10_AIプロンプト設計3.7「相談窓口の案内は画面側が行う」。
      文面はP7-1の成果物(docs/14_法務文書/safety-consultation.md)をそのまま踏襲した
      (SafetyNoticeコンポーネント、P5-2でS-63との共用のため切り出し)。
    -->
    <SafetyNotice v-else />

    <div
      v-if="!isSafetyFlagged"
      class="s16__cta"
    >
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
  align-items: center;
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
  .s16__nickname--enter {
    animation: none;
  }
}
</style>
