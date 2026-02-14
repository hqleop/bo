<template>
  <UFormField :label="label">
    <UPopover v-model:open="isOpen">
      <UButton block variant="outline" :disabled="disabled">
        <span v-if="displayText">{{ displayText }}</span>
        <span v-else>{{ placeholder }}</span>
      </UButton>

      <template #content>
        <div class="p-2 w-96 max-h-96 overflow-y-auto space-y-2">
          <UInput
            v-model="search"
            size="sm"
            placeholder="Пошук серед завантажених вузлів"
          />

          <div v-if="loadingRoot" class="py-6 text-center text-gray-500">
            <UIcon name="i-heroicons-arrow-path" class="animate-spin size-5 mx-auto" />
          </div>

          <div v-else class="space-y-1">
            <template v-if="searchMode">
              <div
                v-for="node in searchedNodes"
                :key="node.id"
                class="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50 cursor-pointer"
                @click="toggleNode(node)"
              >
                <UCheckbox
                  :model-value="selectedIdsSet.has(node.id)"
                  class="shrink-0"
                  @click.stop
                  @update:model-value="toggleNode(node)"
                />
                <span
                  class="flex-1 truncate text-sm"
                  :class="{ 'font-semibold text-primary': selectedIdsSet.has(node.id) }"
                >
                  {{ node.label }}
                </span>
              </div>
            </template>
            <template v-else>
              <CpvLazyNode
                v-for="node in rootNodes"
                :key="node.id"
                :node="node"
                :depth="0"
                :selected-ids="props.selectedIds"
                :expanded="expanded"
                :loading-children="loadingChildren"
                @toggle-expand="toggleExpand"
                @select="toggleNode"
              />
            </template>
          </div>
        </div>
      </template>
    </UPopover>
  </UFormField>
</template>

<script setup lang="ts">
type CpvNode = {
  id: number;
  cpv_level_code: string;
  label: string;
  has_children: boolean;
  children?: CpvNode[];
};

const props = withDefaults(
  defineProps<{
    label: string;
    placeholder?: string;
    disabled?: boolean;
    selectedIds?: number[];
    selectedLabels?: string[];
  }>(),
  {
    placeholder: "Оберіть CPV",
    disabled: false,
    selectedIds: () => [],
    selectedLabels: () => [],
  },
);

const emit = defineEmits<{
  "update:selectedIds": [value: number[]];
  "update:selectedLabels": [value: string[]];
}>();

const { fetch } = useApi();
const { getAuthHeaders } = useAuth();

const isOpen = ref(false);
const search = ref("");
const rootNodes = ref<CpvNode[]>([]);
const loadingRoot = ref(false);
const loadingChildren = ref<Set<number>>(new Set());
const expanded = ref<Set<number>>(new Set());
const labelsById = ref<Record<number, string>>({});

const selectedIdsSet = computed(() => new Set(props.selectedIds || []));

const displayText = computed(() => {
  const ids = props.selectedIds || [];
  if (!ids.length) return "";
  const labels = ids.map(
    (id, i) =>
      labelsById.value[id] ?? props.selectedLabels?.[i] ?? `#${id}`,
  );
  return labels.join(", ");
});

function filterBySearch(nodes: CpvNode[]) {
  const term = search.value.trim().toLowerCase();
  if (!term) return nodes;
  return nodes.filter((n) => n.label.toLowerCase().includes(term));
}

const searchMode = computed(() => !!search.value.trim());

function flattenLoaded(nodes: CpvNode[]): CpvNode[] {
  const out: CpvNode[] = [];
  for (const node of nodes) {
    out.push(node);
    if (node.children?.length) {
      out.push(...flattenLoaded(node.children));
    }
  }
  return out;
}

const searchedNodes = computed(() => {
  return filterBySearch(flattenLoaded(rootNodes.value));
});

function setNodeChildren(
  targetId: number,
  nodes: CpvNode[],
  children: CpvNode[],
): boolean {
  for (const n of nodes) {
    if (n.id === targetId) {
      n.children = children;
      return true;
    }
    if (n.children?.length && setNodeChildren(targetId, n.children, children)) {
      return true;
    }
  }
  return false;
}

async function loadRoot() {
  loadingRoot.value = true;
  const { data } = await fetch("/cpv/children/", { headers: getAuthHeaders() });
  rootNodes.value = (data as CpvNode[]) || [];
  loadingRoot.value = false;
}

async function loadChildren(node: CpvNode) {
  if (!node.has_children) return;
  if (node.children && node.children.length) return;

  loadingChildren.value = new Set([...loadingChildren.value, node.id]);
  const { data } = await fetch(
    `/cpv/children/?parent_level_code=${encodeURIComponent(node.cpv_level_code)}`,
    { headers: getAuthHeaders() },
  );
  const children = (data as CpvNode[]) || [];
  setNodeChildren(node.id, rootNodes.value, children);
  const newSet = new Set(loadingChildren.value);
  newSet.delete(node.id);
  loadingChildren.value = newSet;
}

async function toggleExpand(node: CpvNode) {
  if (expanded.value.has(node.id)) {
    const newSet = new Set(expanded.value);
    newSet.delete(node.id);
    expanded.value = newSet;
    return;
  }
  await loadChildren(node);
  expanded.value = new Set([...expanded.value, node.id]);
}

function toggleNode(node: CpvNode) {
  const ids = [...(props.selectedIds || [])];
  const idx = ids.indexOf(node.id);
  if (idx > -1) {
    ids.splice(idx, 1);
    const next = { ...labelsById.value };
    delete next[node.id];
    labelsById.value = next;
  } else {
    ids.push(node.id);
    labelsById.value = { ...labelsById.value, [node.id]: node.label };
  }
  const labels = ids.map(
    (id) => labelsById.value[id] ?? props.selectedLabels?.[props.selectedIds?.indexOf(id) ?? -1] ?? "",
  );
  emit("update:selectedIds", ids);
  emit("update:selectedLabels", labels);
}

watch(
  () => isOpen.value,
  async (open) => {
    if (open && !rootNodes.value.length) {
      await loadRoot();
    }
  },
);

watch(
  () => props.selectedIds,
  (ids) => {
    if (!ids?.length) return;
    ids.forEach((id, i) => {
      const label = props.selectedLabels?.[i];
      if (label && !labelsById.value[id]) {
        labelsById.value = { ...labelsById.value, [id]: label };
      }
    });
  },
  { immediate: true },
);
</script>
