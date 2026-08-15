<script setup lang="ts">
/**
 * 05_質問・コンテンツ設計2.4、07_デザイン原則7.5。5段階・縦積みの選択肢。
 * 選択肢の文が長いコミット度で使う。下がポジティブ。全文を表示する(目盛りと違い両端省略なし)。
 */
import type { Choice } from "../domain/questions";

const props = defineProps<{
  modelValue: number | null;
  choices: readonly Choice[];
  labelledBy: string;
  name: string;
}>();

defineEmits<{
  "update:modelValue": [value: number];
}>();
</script>

<template>
  <div
    class="stacked-choice-selector"
    role="radiogroup"
    :aria-labelledby="props.labelledBy"
  >
    <label
      v-for="choice in props.choices"
      :key="choice.score"
      class="stacked-choice-selector__option"
      :class="{ 'stacked-choice-selector__option--selected': modelValue === choice.score }"
    >
      <input
        type="radio"
        :name="name"
        class="stacked-choice-selector__input"
        :checked="modelValue === choice.score"
        @change="$emit('update:modelValue', choice.score)"
      >
      <span
        class="stacked-choice-selector__dot"
        aria-hidden="true"
      />
      <span class="stacked-choice-selector__label">{{ choice.label }}</span>
    </label>
  </div>
</template>

<style scoped>
.stacked-choice-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stacked-choice-selector__option {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--tap-target-min);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--control-border);
  border-radius: var(--radius-input);
  background: var(--surface);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  cursor: pointer;
}

.stacked-choice-selector__option--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.stacked-choice-selector__dot {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  border: 1px solid var(--control-border);
  border-radius: 50%;
}

.stacked-choice-selector__option--selected .stacked-choice-selector__dot {
  border-color: var(--primary);
  background: var(--primary);
  box-shadow: inset 0 0 0 3px var(--primary-soft);
}

.stacked-choice-selector__input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.stacked-choice-selector__option:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
