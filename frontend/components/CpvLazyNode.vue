<template>
  <div>
    <div class="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50" :style="{ paddingLeft: `${depth * 14 + 8}px` }">
      <UCheckbox
        v-if="selectedIds?.length !== undefined"
        :model-value="isSelected"
        class="shrink-0"
        @update:model-value="emit('select', node)"
      />
      <UButton
        v-if="node.has_children"
        size="xs"
        color="gray"
        variant="ghost"
        :icon="isExpanded ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-right'"
        class="shrink-0"
        @click="emit('toggle-expand', node)"
      />
      <span v-else class="w-6 shrink-0" />

      <UButton
        size="xs"
        variant="ghost"
        class="justify-start flex-1 truncate min-w-0"
        :class="{ 'font-semibold text-primary': isSelected }"
        @click="emit('select', node)"
      >
        {{ node.label }}
      </UButton>
    </div>

    <div v-if="isExpanded">
      <div v-if="isLoading" class="text-xs text-gray-500 py-1" :style="{ paddingLeft: `${depth * 14 + 36}px` }">
        Завантаження...
      </div>
      <template v-else>
        <CpvLazyNode
          v-for="child in node.children || []"
          :key="child.id"
          :node="child"
          :depth="depth + 1"
          :selected-id="selectedId"
          :selected-ids="selectedIds"
          :expanded="expanded"
          :loading-children="loadingChildren"
          @toggle-expand="emit('toggle-expand', $event)"
          @select="emit('select', $event)"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
type CpvNode = {
  id: number;
  label: string;
  has_children: boolean;
  children?: CpvNode[];
};

const props = defineProps<{
  node: CpvNode;
  depth: number;
  selectedId?: number;
  selectedIds?: number[];
  expanded: Set<number>;
  loadingChildren: Set<number>;
}>();

const emit = defineEmits<{
  "toggle-expand": [node: CpvNode];
  select: [node: CpvNode];
}>();

const isExpanded = computed(() => props.expanded.has(props.node.id));
const isLoading = computed(() => props.loadingChildren.has(props.node.id));
const isSelected = computed(
  () =>
    props.selectedId === props.node.id ||
    (props.selectedIds && props.selectedIds.includes(props.node.id)),
);
</script>
