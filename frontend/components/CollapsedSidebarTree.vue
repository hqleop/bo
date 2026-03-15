<script setup lang="ts">
type SidebarTreeItem = {
  id?: string | number;
  label?: string;
  icon?: string;
  to?: string;
  active?: boolean;
  children?: SidebarTreeItem[];
};

const props = withDefaults(
  defineProps<{
    items?: SidebarTreeItem[];
    depth?: number;
  }>(),
  {
    items: () => [],
    depth: 0,
  },
);

function hasChildren(item: SidebarTreeItem) {
  return Array.isArray(item.children) && item.children.length > 0;
}

function getItemKey(item: SidebarTreeItem, index: number) {
  return String(item.id || item.to || `${props.depth}-${item.label || index}`);
}
</script>

<template>
  <div class="space-y-1">
    <div v-for="(item, index) in props.items" :key="getItemKey(item, index)">
      <div v-if="hasChildren(item)" class="space-y-1">
        <div
          :class="[
            'px-2 text-xs font-semibold uppercase tracking-wide text-gray-500',
            props.depth === 0 ? 'pt-2 pb-1' : 'pt-1 pb-0.5',
          ]"
        >
          {{ item.label }}
        </div>
        <CollapsedSidebarTree
          :items="item.children"
          :depth="props.depth + 1"
        />
      </div>

      <UButton
        v-else
        :to="item.to"
        color="neutral"
        size="sm"
        :variant="item.active ? 'soft' : 'ghost'"
        :icon="item.icon"
        class="w-full justify-start"
      >
        {{ item.label }}
      </UButton>
    </div>
  </div>
</template>
