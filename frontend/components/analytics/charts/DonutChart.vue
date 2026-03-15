<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    data?: number[];
    categories?: Record<string, { name?: string; color?: string }>;
    radius?: number;
    height?: number;
    hideLegend?: boolean;
  }>(),
  {
    data: () => [],
    categories: () => ({}),
    radius: 110,
    height: 320,
    hideLegend: false,
  },
);

const entries = computed(() =>
  Object.entries(props.categories || {}).map(([key, meta], index) => ({
    key,
    label: meta.name || key,
    color: meta.color || "#2563eb",
    value: Number(props.data[index] || 0),
  })),
);

const total = computed(() =>
  entries.value.reduce((sum, item) => sum + item.value, 0),
);

const circumference = computed(() => 2 * Math.PI * props.radius);

const segments = computed(() => {
  let offset = 0;
  return entries.value.map((item) => {
    const segmentLength =
      total.value > 0 ? (item.value / total.value) * circumference.value : 0;
    const segment = {
      ...item,
      length: segmentLength,
      offset,
    };
    offset += segmentLength;
    return segment;
  });
});
</script>

<template>
  <div class="flex h-full w-full flex-col gap-4">
    <div class="flex justify-center">
      <svg
        :viewBox="`0 0 ${props.height} ${props.height}`"
        :style="{ width: `${props.height}px`, height: `${props.height}px`, maxWidth: '100%' }"
        role="img"
        aria-label="Donut chart"
      >
        <g :transform="`translate(${props.height / 2}, ${props.height / 2}) rotate(-90)`">
          <circle
            cx="0"
            cy="0"
            :r="props.radius"
            fill="none"
            stroke="#e5e7eb"
            stroke-width="24"
          />
          <circle
            v-for="segment in segments"
            :key="segment.key"
            cx="0"
            cy="0"
            :r="props.radius"
            fill="none"
            :stroke="segment.color"
            stroke-width="24"
            stroke-linecap="butt"
            :stroke-dasharray="`${segment.length} ${circumference}`"
            :stroke-dashoffset="-segment.offset"
          />
        </g>
        <text
          x="50%"
          y="48%"
          text-anchor="middle"
          class="fill-gray-900 text-lg font-semibold"
        >
          {{ total.toLocaleString("uk-UA") }}
        </text>
        <text
          x="50%"
          y="56%"
          text-anchor="middle"
          class="fill-gray-500 text-xs"
        >
          Всього
        </text>
      </svg>
    </div>

    <div v-if="!hideLegend" class="grid gap-2 sm:grid-cols-2">
      <div
        v-for="segment in segments"
        :key="segment.key"
        class="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-sm"
      >
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="inline-block h-2.5 w-2.5 rounded-full"
            :style="{ backgroundColor: segment.color }"
          />
          <span class="truncate">{{ segment.label }}</span>
        </div>
        <span class="font-medium text-gray-700">
          {{ segment.value.toLocaleString("uk-UA") }}
        </span>
      </div>
    </div>
  </div>
</template>
