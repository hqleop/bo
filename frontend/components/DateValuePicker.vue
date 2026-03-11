<template>
  <UPopover
    v-model:open="isOpen"
    :disabled="disabled"
    :content="{ align: 'start' }"
  >
    <UButton
      :disabled="disabled"
      :size="size"
      variant="subtle"
      color="neutral"
      icon="i-lucide-calendar"
      :class="buttonClasses"
    >
      {{ displayValue }}
    </UButton>

    <template #content>
      <div class="p-2 space-y-2">
        <UCalendar v-model="draftCalendarValue" class="p-2" />
        <div class="grid grid-cols-3 items-center gap-2">
          <div class="justify-self-start">
            <UButton
              size="xs"
              variant="ghost"
              color="neutral"
              :disabled="disabled || !canClear"
              @click="clearValue"
            >
              Очистити
            </UButton>
          </div>
          <div class="justify-self-center">
            <UButton
              size="xs"
              variant="ghost"
              color="neutral"
              :disabled="disabled"
              @click="selectToday"
            >
              Сьогодні
            </UButton>
          </div>
          <div class="justify-self-end">
            <UButton
              size="xs"
              color="primary"
              :disabled="disabled || !draftCalendarValue"
              @click="saveValue"
            >
              Зберегти
            </UButton>
          </div>
        </div>
      </div>
    </template>
  </UPopover>
</template>

<script setup lang="ts">
import {
  getLocalTimeZone,
  parseDate,
  today,
  type DateValue,
} from "@internationalized/date";

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
    placeholder: "Дата",
    disabled: false,
    size: "sm",
    buttonClass: "",
  },
);

const emit = defineEmits<{
  "update:model-value": [value: string];
}>();

const isOpen = ref(false);

const buttonClasses = computed(() => [
  "w-full justify-start text-left font-normal",
  !String(props.modelValue || "").trim() ? "text-gray-500" : "",
  props.buttonClass,
]);

function parseModelDateValue(rawValue?: string | null): DateValue | undefined {
  const raw = String(rawValue || "").trim();
  if (!raw) return undefined;
  try {
    return parseDate(raw);
  } catch {
    return undefined;
  }
}

const draftCalendarValue = ref<DateValue | undefined>(
  parseModelDateValue(props.modelValue),
);

watch(
  () => isOpen.value,
  (open) => {
    if (open) {
      draftCalendarValue.value = parseModelDateValue(props.modelValue);
    }
  },
);

watch(
  () => props.modelValue,
  (nextValue) => {
    if (!isOpen.value) {
      draftCalendarValue.value = parseModelDateValue(nextValue);
    }
  },
);

const canClear = computed(
  () => !!draftCalendarValue.value || !!String(props.modelValue || "").trim(),
);

const displayValue = computed(() => {
  const raw = String(props.modelValue || "").trim();
  if (!raw) return props.placeholder;
  try {
    const parsed = parseDate(raw);
    return new Intl.DateTimeFormat("uk-UA", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(parsed.toDate(getLocalTimeZone()));
  } catch {
    return raw;
  }
});

function clearValue() {
  emit("update:model-value", "");
  draftCalendarValue.value = undefined;
}

function selectToday() {
  draftCalendarValue.value = today(getLocalTimeZone());
}

function saveValue() {
  if (!draftCalendarValue.value) return;
  emit("update:model-value", draftCalendarValue.value.toString());
  isOpen.value = false;
}
</script>
