<template>
  <div>
    <div
      class="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 min-w-max"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
    >
      <UButton
        v-if="node.has_children"
        type="button"
        size="xs"
        color="gray"
        variant="ghost"
        :icon="
          expanded.has(node.id)
            ? 'i-heroicons-chevron-down'
            : 'i-heroicons-chevron-right'
        "
        class="shrink-0"
        @click="emit('toggle-expand', node.id)"
      />
      <span v-else class="w-6 shrink-0" />

      <UCheckbox
        :model-value="selectedIds.has(node.id)"
        class="shrink-0"
        @update:model-value="emit('toggle-select', node.id)"
      />

      <button
        type="button"
        class="text-left flex-1 text-sm whitespace-nowrap"
        :class="selectedIds.has(node.id) ? 'font-semibold text-primary' : ''"
        @click="emit('toggle-select', node.id)"
      >
        {{ node.label }}
      </button>
    </div>

    <div v-if="expanded.has(node.id)">
      <div
        v-if="loadingChildren.has(node.id)"
        class="text-xs text-gray-500 py-1"
        :style="{ paddingLeft: `${depth * 16 + 36}px` }"
      >
        Завантаження...
      </div>

      <template v-else>
        <CpvTenderTreeNode
          v-for="child in node.children || []"
          :key="child.id"
          :node="child"
          :depth="depth + 1"
          :expanded="expanded"
          :loading-children="loadingChildren"
          :selected-ids="selectedIds"
          @toggle-expand="emit('toggle-expand', $event)"
          @toggle-select="emit('toggle-select', $event)"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
type CpvNode = {
  id: number;
  cpv_level_code: string;
  label: string;
  has_children: boolean;
  children?: CpvNode[];
};

defineProps<{
  node: CpvNode;
  depth: number;
  expanded: Set<number>;
  loadingChildren: Set<number>;
  selectedIds: Set<number>;
}>();

const emit = defineEmits<{
  "toggle-expand": [id: number];
  "toggle-select": [id: number];
}>();
</script>
