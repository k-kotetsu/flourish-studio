<script setup lang="ts">
/**
 * P1-16 完了条件：Storybook相当の一覧で全状態を確認できること。
 * 実装だけの内部確認用画面のため、文言は仮のサンプル値を使う（本番文言は各フロー実装で決める）。
 */
import { ref } from "vue";
import AppButton from "../components/AppButton.vue";
import AppProgressBar from "../components/AppProgressBar.vue";
import AppHeaderHub from "../components/AppHeaderHub.vue";
import AppHeaderFlow from "../components/AppHeaderFlow.vue";
import AppHeaderSingle from "../components/AppHeaderSingle.vue";
import AppLogo from "../components/AppLogo.vue";
import AreaIcon from "../components/AreaIcon.vue";
import InterruptDialog from "../components/InterruptDialog.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";
import GrowthStageDisplay from "../components/GrowthStageDisplay.vue";
import ChipMultiSelect from "../components/ChipMultiSelect.vue";
import CheckboxChoiceSelector from "../components/CheckboxChoiceSelector.vue";
import { AREAS, AREA_META } from "../domain/questions";
import { GROWTH_STAGES, GROWTH_STAGE_ICONS, GROWTH_STAGE_LABELS } from "../domain/growthStage";
import { VALUES_OPTIONS, VALUES_MAX_SELECTION, FULFILLING_MOMENT_OPTIONS } from "../domain/purposeChoices";

const dialogOpen = ref(false);
const generatingFailed = ref(false);
const gallerySelectedValues = ref<string[]>(["GROWTH", "FREEDOM"]);
const gallerySelectedMoments = ref<string[]>(["HELPED_SOMEONE"]);
</script>

<template>
  <div class="gallery">
    <h1 class="gallery__title">
      共通コンポーネント一覧
    </h1>
    <p class="gallery__lede">
      P1-16。スキル flourish-ui / デザイン原則 6〜7章に対応する状態をすべて並べる。
    </p>

    <section class="gallery__group">
      <h2>ボタン（4種）</h2>
      <div class="gallery__row">
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            主要
          </p>
          <AppButton variant="primary">
            次へ
          </AppButton>
        </div>
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            副次
          </p>
          <AppButton variant="secondary">
            対話に戻る
          </AppButton>
        </div>
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            テキスト
          </p>
          <AppButton variant="text">
            やめる
          </AppButton>
        </div>
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            無効（理由を直下に添える）
          </p>
          <AppButton
            variant="primary"
            disabled
          >
            次へ
          </AppButton>
          <p class="gallery__hint">
            すべて選ぶと、次に進めます
          </p>
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>プログレスバー</h2>
      <div class="gallery__row">
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            17%
          </p>
          <AppProgressBar :percent="17" />
        </div>
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            67%（生成中はここで止める）
          </p>
          <AppProgressBar :percent="67" />
        </div>
        <div class="gallery__frame gallery__frame--narrow">
          <p class="gallery__label">
            100%
          </p>
          <AppProgressBar :percent="100" />
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>ヘッダー（3型）</h2>
      <div class="gallery__row">
        <div class="gallery__device">
          <p class="gallery__label">
            ハブ（S-41）
          </p>
          <AppHeaderHub>
            <template #right>
              <span class="gallery__toggle-placeholder">◐ 自動</span>
            </template>
          </AppHeaderHub>
        </div>

        <div class="gallery__device">
          <p class="gallery__label">
            フロー内（戻る＋ステップ）
          </p>
          <AppHeaderFlow
            title="現在地レポート"
            :percent="17"
            left-action="back"
            step="1 / 6"
          />
        </div>

        <div class="gallery__device">
          <p class="gallery__label">
            フローの入口（中断）
          </p>
          <AppHeaderFlow
            title="現在地レポート"
            :percent="0"
            left-action="cancel"
          />
        </div>

        <div class="gallery__device">
          <p class="gallery__label">
            生成中（戻る・ステップなし）
          </p>
          <AppHeaderFlow
            title="現在地レポート"
            :percent="67"
            left-action="none"
          />
        </div>

        <div class="gallery__device">
          <p class="gallery__label">
            単独の画面（プログレスバーなし）
          </p>
          <AppHeaderSingle title="Career" />
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>中断ダイアログ</h2>
      <AppButton
        variant="secondary"
        @click="dialogOpen = true"
      >
        × 中断 を試す
      </AppButton>
      <InterruptDialog
        :open="dialogOpen"
        @continue="dialogOpen = false"
        @leave="dialogOpen = false"
      />
    </section>

    <section class="gallery__group">
      <h2>成長段階アイコン（P2-10。種・芽・苗・木）</h2>
      <p class="gallery__lede">
        線画・24pxグリッド・線幅1.6px・塗りつぶしなし。4つ並べたときに成長の連続が読み取れることを確認する（`07_デザイン原則`7.6）。表示コンポーネント（該当段階のみ`--primary`で点灯、点灯アニメーション）はP2-11で下のセクションに実装した。
      </p>
      <div class="gallery__row">
        <div
          v-for="stage in GROWTH_STAGES"
          :key="`icon-${stage}`"
          class="gallery__icon"
        >
          <svg
            class="gallery__icon-svg"
            :viewBox="GROWTH_STAGE_ICONS[stage].viewBox"
          >
            <path
              v-for="(d, i) in GROWTH_STAGE_ICONS[stage].paths"
              :key="i"
              :d="d"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <span class="gallery__label">{{ GROWTH_STAGE_LABELS[stage] }}</span>
        </div>
      </div>
      <p class="gallery__lede">
        実際の表示サイズ（28px）・点灯色
      </p>
      <div class="gallery__row">
        <div
          v-for="stage in GROWTH_STAGES"
          :key="`icon-small-${stage}`"
          class="gallery__icon gallery__icon--small gallery__icon--primary"
        >
          <svg
            class="gallery__icon-svg gallery__icon-svg--small"
            :viewBox="GROWTH_STAGE_ICONS[stage].viewBox"
          >
            <path
              v-for="(d, i) in GROWTH_STAGE_ICONS[stage].paths"
              :key="i"
              :d="d"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <span class="gallery__label">{{ GROWTH_STAGE_LABELS[stage] }}</span>
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>4領域アイコン（P7-3。`07_デザイン原則`7.6）</h2>
      <p class="gallery__lede">
        線画・24pxグリッド・線幅1.6px・塗りつぶしなし・`currentColor`。既製セット（`mockup.html`のICON）から選定した。2.6「4領域の色分けはしない」ため、4つとも同じ色（`currentColor`）で表示される。
      </p>
      <div class="gallery__row">
        <div
          v-for="area in AREAS"
          :key="`area-icon-${area}`"
          class="gallery__icon"
        >
          <AreaIcon
            :area="area"
            :size="32"
          />
          <span class="gallery__label">{{ AREA_META[area].en }}</span>
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>ロゴロックアップ（P7-3。定義書19章 未決#4）</h2>
      <p class="gallery__lede">
        ロゴマーク（`ICON_FLOURISH`由来の双葉のモチーフ）とサービス名を組みで表示する。ロゴマーク単体では使わない。`AppHeaderHub`はtitle省略時（S-41ホーム）にこれを出す。
      </p>
      <div class="gallery__row">
        <div class="gallery__frame gallery__frame--narrow">
          <AppLogo />
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>成長段階の表示（P2-11。`07_デザイン原則`7.7）</h2>
      <p class="gallery__lede">
        4段階すべてを並べ、該当する現在地だけを`--primary`で点灯する。数値は出さない。点灯は種側から現在地へ光が通り過ぎ、現在地で止まる（10.2）。
      </p>
      <div class="gallery__row">
        <div
          v-for="stage in GROWTH_STAGES"
          :key="`display-${stage}`"
          class="gallery__frame gallery__frame--narrow"
        >
          <p class="gallery__label">
            現在地: {{ GROWTH_STAGE_LABELS[stage] }}
          </p>
          <GrowthStageDisplay
            axis-name="言語化度"
            axis-description="自分の考えが、どのくらい自分の言葉になっているか"
            :stage="stage"
          />
        </div>
      </div>
    </section>

    <section class="gallery__group">
      <h2>チップ選択（P3-5。上限つき複数選択）</h2>
      <p class="gallery__lede">
        上限(3つ)に達すると未選択のチップが選べなくなる。選択済みは色に加えて枠線も変える。
      </p>
      <div class="gallery__frame gallery__frame--narrow">
        <p
          id="gallery-chip-values"
          class="gallery__label"
        >
          大切にしたいこと（{{ gallerySelectedValues.length }} / {{ VALUES_MAX_SELECTION }}）
        </p>
        <ChipMultiSelect
          v-model="gallerySelectedValues"
          :choices="VALUES_OPTIONS"
          :max="VALUES_MAX_SELECTION"
          labelled-by="gallery-chip-values"
        />
      </div>
    </section>

    <section class="gallery__group">
      <h2>チェックボックス選択（P3-5。上限なし複数選択）</h2>
      <div class="gallery__frame gallery__frame--narrow">
        <p
          id="gallery-checkbox-moments"
          class="gallery__label"
        >
          満たされていると感じるとき
        </p>
        <CheckboxChoiceSelector
          v-model="gallerySelectedMoments"
          :choices="FULFILLING_MOMENT_OPTIONS"
          labelled-by="gallery-checkbox-moments"
          name="gallery-fulfilling-moments"
        />
      </div>
    </section>

    <section class="gallery__group">
      <h2>生成中画面</h2>
      <AppButton
        variant="secondary"
        @click="generatingFailed = !generatingFailed"
      >
        {{ generatingFailed ? "待ち状態に戻す" : "失敗状態にする" }}
      </AppButton>
      <div class="gallery__device gallery__device--tall">
        <AppHeaderFlow
          title="現在地レポート"
          :percent="67"
          left-action="none"
        />
        <GeneratingScreen
          message="あなたに合わせた質問を用意しています"
          :failed="generatingFailed"
          error-title="うまく作れませんでした"
          error-message="時間がかかりすぎたようです。もう一度お試しください。"
          back-label="質問に戻る"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.gallery {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-5) var(--layout-gutter) 80px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.gallery__title {
  font-size: var(--font-size-heading);
  font-weight: 700;
  margin: 0;
}

.gallery__lede {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  margin: 0;
}

.gallery__group h2 {
  font-size: var(--font-size-section);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-2);
  margin: 0 0 var(--space-3);
}

.gallery__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: flex-start;
}

.gallery__label {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  margin: 0 0 var(--space-1);
}

.gallery__hint {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  text-align: center;
  margin: var(--space-1) 0 0;
}

.gallery__frame--narrow {
  width: 220px;
}

.gallery__device {
  width: var(--layout-width-base);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  background: var(--surface);
}

.gallery__device--tall {
  display: flex;
  flex-direction: column;
  height: 420px;
}

.gallery__device--tall :deep(.generating-screen) {
  background: var(--bg);
}

.gallery__icon {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.gallery__icon-svg {
  width: 64px;
  height: 64px;
}

.gallery__icon-svg--small {
  width: 28px;
  height: 28px;
}

.gallery__icon--small {
  gap: var(--space-2);
}

.gallery__icon--primary {
  color: var(--primary);
}

.gallery__toggle-placeholder {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  border: 1px solid var(--control-border);
  border-radius: 999px;
  padding: 4px 10px;
}
</style>
