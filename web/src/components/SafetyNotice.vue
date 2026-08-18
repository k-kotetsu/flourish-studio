<script setup lang="ts">
/**
 * `safety_flag`が立ったときの固定文面(10_AIプロンプト設計3.7「AIは相談窓口を出力しない。
 * クライアントが`safety_flag`を見て固定の文面を表示する」)。
 * 文面はP7-1の成果物(`docs/14_法務文書/safety-consultation.md`)をそのまま踏襲する。
 * S-16(P2-12)で最初に実装し、S-63(P5-2)でも同じ文面を使うため共通コンポーネントに切り出した。
 * CTA・ナビゲーションは置かない(呼び出し側の画面が持つ)。
 */
</script>

<template>
  <div
    class="safety-notice"
    data-testid="safety-notice"
  >
    <p class="safety-notice__lead">
      書いてくださった言葉の中に、<br>
      ひとりで抱えるには重いことのように見えました。
    </p>
    <p class="safety-notice__text">
      今回は現在地レポートの代わりに、<br>
      話を聞いてくれる場所をお伝えします。
    </p>

    <div class="safety-notice__contact">
      <p class="safety-notice__contact-name">
        よりそいホットライン
      </p>
      <p class="safety-notice__contact-detail">
        0120-279-338（通話無料・24時間）
      </p>
    </div>

    <div class="safety-notice__contact">
      <p class="safety-notice__contact-name">
        いのちの電話
      </p>
      <p class="safety-notice__contact-detail">
        0570-783-556（10時〜22時）<br>
        0120-783-556（毎月10日 8時〜翌日8時・通話無料）
      </p>
    </div>

    <div class="safety-notice__contact">
      <p class="safety-notice__contact-name">
        まもろうよ こころ（厚生労働省）
      </p>
      <p class="safety-notice__contact-detail">
        電話が難しいときは、SNSでの相談窓口も探せます<br>
        <a
          href="https://www.mhlw.go.jp/mamorouyokokoro/"
          target="_blank"
          rel="noopener noreferrer"
        >https://www.mhlw.go.jp/mamorouyokokoro/</a>
      </p>
    </div>

    <p class="safety-notice__note">
      書いていただいた内容はそのまま残っています。<br>
      落ち着いたときに、あらためて見ることもできます。
    </p>
  </div>
</template>

<style scoped>
.safety-notice {
  flex: 1 1 auto;
  padding: var(--space-5) var(--layout-gutter) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.safety-notice__lead,
.safety-notice__text {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.safety-notice__contact {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.safety-notice__contact-name {
  margin: 0;
  font-size: var(--font-size-section);
  font-weight: 600;
}

.safety-notice__contact-detail {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
}

.safety-notice__contact-detail a {
  color: var(--primary);
}

.safety-notice__note {
  margin: 0;
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  color: var(--text-sub);
}
</style>
