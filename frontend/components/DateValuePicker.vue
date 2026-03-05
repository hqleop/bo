<template>
  <UPopover :disabled="disabled" :content="{ align: 'start' }">
    <UButton
      :disabled="disabled"
      :size="size"
      variant="outline"
      color="neutral"
      :class="buttonClasses"
    >
      {{ displayValue }}
    </UButton>

    <template #content>
      <div class="p-2 space-y-2">
        <UCalendar v-model="calendarValue" />
        <div class="flex justify-end">
          <UButton
            v-if="modelValue && !disabled"
            size="xs"
            variant="ghost"
            color="neutral"
            @click="clearValue"
          >
            Очистити
          </UButton>
        </div>
      </div>
    </template>
  </UPopover>
</template>

<script setup lang="ts">
import { parseDate, type DateValue } from "@internationalized/date";

const props = withDefaults(
  defineProps<{
    modelValue?: string | null;
    placeholder?: string;
    disabled?: boolean;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    buttonClass?: string;
  }>(),
  {
    modelValue: "",
    placeholder: "Оберіть дату",
    disabled: false,
    size: "sm",
    buttonClass: "",
  },
);

const emit = defineEmits<{
  "update:model-value": [value: string];
}>();

const buttonClasses = computed(() => [
  "w-full justify-start text-left font-normal",
  !String(props.modelValue || "").trim() ? "text-gray-500" : "",
  props.buttonClass,
]);

const calendarValue = computed<DateValue | undefined>({
  get() {
    const raw = String(props.modelValue || "").trim();
    if (!raw) return undefined;
    try {
      return parseDate(raw);
    } catch {
      return undefined;
    }
  },
  set(value) {
    emit("update:model-value", value ? value.toString() : "");
  },
});

const displayValue = computed(() => {
  const raw = String(props.modelValue || "").trim();
  return raw || props.placeholder;
});

function clearValue() {
  emit("update:model-value", "");
}
</script>
