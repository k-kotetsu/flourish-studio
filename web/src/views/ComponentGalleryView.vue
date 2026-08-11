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
import InterruptDialog from "../components/InterruptDialog.vue";
import GeneratingScreen from "../components/GeneratingScreen.vue";

const dialogOpen = ref(false);
const generatingFailed = ref(false);
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

.gallery__toggle-placeholder {
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  border: 1px solid var(--control-border);
  border-radius: 999px;
  padding: 4px 10px;
}
</style>
