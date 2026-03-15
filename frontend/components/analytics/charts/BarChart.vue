<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    data?: Record<string, any>[];
    categories?: Record<string, { name?: string; color?: string }>;
    xAxis?: string;
    yAxis?: string[];
    height?: number;
  }>(),
  {
    data: () => [],
    categories: () => ({}),
    xAxis: "label",
    yAxis: () => ["value"],
    height: 280,
  },
);

const valueKey = computed(() => props.yAxis[0] || "value");
const color = computed(() => {
  const firstCategory = Object.values(props.categories || {})[0];
  return firstCategory?.color || "#2563eb";
});

const items = computed(() =>
  (props.data || []).map((item) => ({
    label: String(item?.[props.xAxis] ?? ""),
    value: Number(item?.[valueKey.value] || 0),
  })),
);

const maxValue = computed(() =>
  Math.max(...items.value.map((item) => item.value), 0),
);
</script>

<template>
  <div class="h-full w-full">
    <div
      class="grid h-full items-end gap-3"
      :style="{
        height: `${props.height}px`,
        gridTemplateColumns: `repeat(${Math.max(items.length, 1)}, minmax(0, 1fr))`,
      }"
    >
      <div
        v-for="(item, index) in items"
        :key="`${item.label}-${index}`"
        class="flex min-w-0 flex-col justify-end"
      >
        <div class="mb-2 text-center text-xs font-medium text-gray-500">
          {{ item.value.toLocaleString("uk-UA") }}
        </div>
        <div
          class="min-h-[8px] rounded-t-md transition-all"
          :style="{
            height: `${maxValue > 0 ? Math.max((item.value / maxValue) * (props.height - 56), 8) : 8}px`,
            backgroundColor: color,
          }"
        />
        <div class="mt-2 truncate text-center text-xs text-gray-600">
          {{ item.label }}
        </div>
      </div>
    </div>
  </div>
</template>
