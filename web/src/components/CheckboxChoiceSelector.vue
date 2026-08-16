<script setup lang="ts">
/**
 * 05_質問・コンテンツ設計6章Q2、06_ワイヤーフレーム(mockup.html checks())。
 * 上限のない縦積みの複数選択(チェックボックス)。見た目はStackedChoiceSelector(単一選択・radio)と
 * 揃え、印だけを丸(radio)から四角(checkbox)に変える。
 */
import type { PurposeChoiceOption } from "../domain/purposeChoices";

const props = defineProps<{
  modelValue: readonly string[];
  choices: readonly PurposeChoiceOption[];
  labelledBy: string;
  name: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

function isSelected(code: string): boolean {
  return props.modelValue.includes(code);
}

function toggle(code: string): void {
  if (isSelected(code)) {
    emit(
      "update:modelValue",
      props.modelValue.filter((c) => c !== code),
    );
    return;
  }
  emit("update:modelValue", [...props.modelValue, code]);
}
</script>

<template>
  <div
    class="checkbox-choice-selector"
    role="group"
    :aria-labelledby="labelledBy"
  >
    <label
      v-for="choice in props.choices"
      :key="choice.code"
      class="checkbox-choice-selector__option"
      :class="{ 'checkbox-choice-selector__option--selected': isSelected(choice.code) }"
    >
      <input
        type="checkbox"
        :name="name"
        class="checkbox-choice-selector__input"
        :checked="isSelected(choice.code)"
        @change="toggle(choice.code)"
      >
      <span
        class="checkbox-choice-selector__box"
        aria-hidden="true"
      />
      <span class="checkbox-choice-selector__label">{{ choice.label }}</span>
    </label>
  </div>
</template>

<style scoped>
.checkbox-choice-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.checkbox-choice-selector__option {
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

.checkbox-choice-selector__option--selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.checkbox-choice-selector__box {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  border: 1px solid var(--control-border);
  border-radius: 4px;
}

.checkbox-choice-selector__option--selected .checkbox-choice-selector__box {
  border-color: var(--primary);
  background: var(--primary);
  box-shadow: inset 0 0 0 3px var(--primary-soft);
}

.checkbox-choice-selector__input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.checkbox-choice-selector__option:focus-within {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
</style>
