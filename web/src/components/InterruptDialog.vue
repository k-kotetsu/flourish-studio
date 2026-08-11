<script setup lang="ts">
/**
 * 07_デザイン原則 7.2。「× 中断」を押したときに必ず挟むダイアログ。
 * 文言は固定（未確定の入力は保存されない、という共通の事情のため）。
 * 「つづける」を主ボタンにする。誤操作で入力を失う側を既定にしない。
 */
import { nextTick, useTemplateRef, watch } from "vue";
import AppButton from "./AppButton.vue";

const props = defineProps<{
  open: boolean;
}>();

defineEmits<{
  continue: [];
  leave: [];
}>();

const continueButton = useTemplateRef<InstanceType<typeof AppButton>>("continueButton");

// キーボード操作の起点を「つづける」に置く。誤操作で「やめる」に飛びやすくしない
watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    await nextTick();
    continueButton.value?.$el?.focus();
  },
);
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="interrupt-dialog__scrim"
    >
      <div
        class="interrupt-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="interrupt-dialog-title"
        aria-describedby="interrupt-dialog-body"
      >
        <h2
          id="interrupt-dialog-title"
          class="interrupt-dialog__title"
        >
          ここでやめますか？
        </h2>
        <p
          id="interrupt-dialog-body"
          class="interrupt-dialog__body"
        >
          いま中断すると、ここまで選んでいただいた内容は残りません。またいつでも、最初から始められます。
        </p>
        <AppButton
          ref="continueButton"
          variant="primary"
          @click="$emit('continue')"
        >
          つづける
        </AppButton>
        <AppButton
          variant="text"
          @click="$emit('leave')"
        >
          やめる
        </AppButton>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.interrupt-dialog__scrim {
  position: fixed;
  inset: 0;
  background: var(--scrim);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--layout-gutter);
  z-index: 100;
}

.interrupt-dialog {
  width: 100%;
  max-width: var(--layout-width-max);
  background: var(--surface);
  border-radius: var(--radius-card);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.interrupt-dialog__title {
  margin: 0;
  font-size: var(--font-size-heading);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

.interrupt-dialog__body {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-caption);
  color: var(--text-sub);
  line-height: var(--line-height-caption);
}
</style>
