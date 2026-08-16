<script setup lang="ts">
/**
 * 05_質問・コンテンツ設計6章Q1、06_ワイヤーフレーム(wireframe-spec.md「価値観12個はチップ形式、3つまで」、mockup.html chips())。
 * チップ形式・上限つきの複数選択。上限に達したら未選択のチップを選べなくする
 * (仕様に上限超過時の挙動の明記がないための実装判断。トグルで外せば再度選べる)。
 * 選択済みは色に加えて枠線も変える(flourish-ui「色だけで意味を伝えない」)。
 */
import type { PurposeChoiceOption } from "../domain/purposeChoices";

const props = defineProps<{
  modelValue: readonly string[];
  choices: readonly PurposeChoiceOption[];
  max: number;
  labelledBy: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

function isSelected(code: string): boolean {
  return props.modelValue.includes(code);
}

function isDisabled(code: string): boolean {
  return !isSelected(code) && props.modelValue.length >= props.max;
}

function toggle(code: string): void {
  if (isSelected(code)) {
    emit(
      "update:modelValue",
      props.modelValue.filter((c) => c !== code),
    );
    return;
  }
  if (props.modelValue.length >= props.max) return;
  emit("update:modelValue", [...props.modelValue, code]);
}
</script>

<template>
  <div
    class="chip-multi-select"
    role="group"
    :aria-labelledby="labelledBy"
  >
    <button
      v-for="choice in choices"
      :key="choice.code"
      type="button"
      class="chip-multi-select__chip"
      :class="{
        'chip-multi-select__chip--selected': isSelected(choice.code),
        'chip-multi-select__chip--disabled': isDisabled(choice.code),
      }"
      :aria-pressed="isSelected(choice.code)"
      :disabled="isDisabled(choice.code)"
      @click="toggle(choice.code)"
    >
      {{ choice.label }}
    </button>
  </div>
</template>

<style scoped>
.chip-multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip-multi-select__chip {
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: var(--font-size-body);
  cursor: pointer;
}

.chip-multi-select__chip--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.chip-multi-select__chip--disabled {
  color: var(--text-faint);
  cursor: default;
}

.chip-multi-select__chip:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
