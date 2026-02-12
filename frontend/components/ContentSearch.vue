<template>
  <UFormField :label="label" :help="help">
    <UInput
      v-if="!showTree"
      v-model="localSearchTerm"
      :placeholder="placeholder"
      @input="$emit('update:searchTerm', localSearchTerm)"
    />
    <UPopover v-else v-model:open="isOpen">
      <UButton block variant="outline" :disabled="disabled">
        <span v-if="selectedLabels.length">
          {{ selectedLabels.join(", ") }}
        </span>
        <span v-else>{{ placeholder }}</span>
      </UButton>
      <template #content>
        <div class="p-2 w-80 max-h-80 overflow-y-auto space-y-2">
          <UInput
            v-model="localSearchTerm"
            size="sm"
            :placeholder="searchPlaceholder"
            @input="$emit('update:searchTerm', localSearchTerm)"
            @focus="isOpen = true"
          />
          <div class="mt-2 space-y-1">
            <FilterTreeItem
              v-for="node in filteredTree"
              :key="node.id"
              :item="node"
              :selected-ids="selectedIds"
              @toggle="$emit('toggle', $event)"
            />
          </div>
        </div>
      </template>
    </UPopover>
  </UFormField>
</template>

<script setup lang="ts">
const props = defineProps<{
  label: string;
  help?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  tree?: any[];
  selectedIds?: number[];
  searchTerm?: string;
}>();

const emit = defineEmits<{
  toggle: [id: number];
  "update:searchTerm": [value: string];
}>();

const isOpen = ref(false);
const localSearchTerm = ref(props.searchTerm || "");

const showTree = computed(() => Array.isArray(props.tree));

watch(
  () => props.searchTerm,
  (newVal) => {
    localSearchTerm.value = newVal || "";
  },
);

// Функція для фільтрації дерева
function filterTree(list: any[], predicate: (node: any) => boolean): any[] {
  const result: any[] = [];
  for (const node of list) {
    const children = node.children ? filterTree(node.children, predicate) : [];
    if (predicate(node) || children.length) {
      result.push({ ...node, children });
    }
  }
  return result;
}

// Функція для сплощення дерева
function flattenTree(items: any[]): any[] {
  const out: any[] = [];
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      out.push(n);
      if (n.children?.length) walk(n.children);
    }
  };
  walk(items);
  return out;
}

const filteredTree = computed(() => {
  if (!showTree.value) return [];
  const term = localSearchTerm.value.trim().toLowerCase();
  if (!term) return props.tree || [];
  const filterFn = (node: any) =>
    (node.name || node.label || "").toLowerCase().includes(term);
  return filterTree(props.tree || [], filterFn);
});

const selectedLabels = computed(() => {
  if (!showTree.value || !props.selectedIds || props.selectedIds.length === 0)
    return [];
  const flat = flattenTree(props.tree || []);
  return props.selectedIds
    .map((id) => {
      const node = flat.find((n) => n.id === id);
      return node?.name || node?.label;
    })
    .filter(Boolean) as string[];
});
</script>
