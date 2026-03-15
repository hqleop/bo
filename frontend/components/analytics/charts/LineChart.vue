<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    data?: Record<string, any>[];
    categories?: Record<string, { name?: string; color?: string }>;
    height?: number;
    xFormatter?: (index: number) => string;
    hideLegend?: boolean;
  }>(),
  {
    data: () => [],
    categories: () => ({}),
    height: 320,
    xFormatter: undefined,
    hideLegend: false,
  },
);

const chartHeight = computed(() => props.height);
const chartWidth = 640;
const padding = { top: 16, right: 16, bottom: 32, left: 16 };

const categoryEntries = computed(() => Object.entries(props.categories || {}));

const maxValue = computed(() => {
  const values = (props.data || []).flatMap((row) =>
    categoryEntries.value.map(([key]) => Number(row?.[key] || 0)),
  );
  return Math.max(...values, 0);
});

function getX(index: number) {
  const count = Math.max((props.data || []).length - 1, 1);
  const innerWidth = chartWidth - padding.left - padding.right;
  return padding.left + (innerWidth * index) / count;
}

function getY(value: number) {
  const innerHeight = chartHeight.value - padding.top - padding.bottom;
  const safeMax = Math.max(maxValue.value, 1);
  return padding.top + innerHeight - (value / safeMax) * innerHeight;
}

function buildPoints(key: string) {
  return (props.data || [])
    .map((row, index) => `${getX(index)},${getY(Number(row?.[key] || 0))}`)
    .join(" ");
}
</script>

<template>
  <div class="w-full">
    <div
      v-if="!hideLegend"
      class="mb-3 flex flex-wrap gap-3 text-xs text-gray-600"
    >
      <div
        v-for="[key, meta] in categoryEntries"
        :key="key"
        class="flex items-center gap-2"
      >
        <span
          class="inline-block h-2.5 w-2.5 rounded-full"
          :style="{ backgroundColor: meta.color || '#2563eb' }"
        />
        <span>{{ meta.name || key }}</span>
      </div>
    </div>

    <svg
      :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
      class="h-auto w-full"
      role="img"
      aria-label="Line chart"
    >
      <line
        :x1="padding.left"
        :y1="chartHeight - padding.bottom"
        :x2="chartWidth - padding.right"
        :y2="chartHeight - padding.bottom"
        stroke="#e5e7eb"
      />
      <line
        :x1="padding.left"
        :y1="padding.top"
        :x2="padding.left"
        :y2="chartHeight - padding.bottom"
        stroke="#e5e7eb"
      />

      <g v-for="(row, index) in props.data" :key="index">
        <text
          :x="getX(index)"
          :y="chartHeight - 8"
          text-anchor="middle"
          font-size="11"
          fill="#6b7280"
        >
          {{ props.xFormatter ? props.xFormatter(index) : row?.month_label || row?.month || index + 1 }}
        </text>
      </g>

      <g v-for="[key, meta] in categoryEntries" :key="key">
        <polyline
          fill="none"
          :points="buildPoints(key)"
          :stroke="meta.color || '#2563eb'"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle
          v-for="(row, index) in props.data"
          :key="`${key}-${index}`"
          :cx="getX(index)"
          :cy="getY(Number(row?.[key] || 0))"
          r="3"
          :fill="meta.color || '#2563eb'"
        />
      </g>
    </svg>
  </div>
</template>
