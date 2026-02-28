<template>
  <UFormField :label="label" :required="required">
    <div class="space-y-2">
      <UButton
        type="button"
        block
        variant="outline"
        :disabled="disabled"
        @click="openModal"
      >
        {{ buttonText }}
      </UButton>

      <p v-if="previewText" class="text-xs text-gray-500 line-clamp-2">
        {{ previewText }}
      </p>
    </div>
  </UFormField>

  <UModal
    v-model:open="isOpen"
    :ui="{
      content: 'sm:max-w-[72rem] w-[96vw]',
    }"
  >
    <template #content>
      <UCard class="w-full max-h-[90vh] flex flex-col">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <h3 class="text-lg font-semibold">{{ modalTitle }}</h3>
            <UBadge color="primary" variant="subtle">
              Обрано: {{ selectedItems.length }}
            </UBadge>
          </div>
        </template>

        <div class="space-y-4 overflow-y-auto flex-1 min-h-0">
          <UInput
            v-model="search"
            icon="i-heroicons-magnifying-glass"
            placeholder="Пошук CPV за кодом або назвою"
          />

          <div
            class="border rounded-md p-2 h-[34vh] sm:h-[38vh] overflow-y-auto overflow-x-auto"
          >
            <div
              v-if="searchMode ? loadingSearch : loadingRoot"
              class="py-8 text-center text-gray-500"
            >
              <UIcon
                name="i-heroicons-arrow-path"
                class="animate-spin size-5 mx-auto"
              />
            </div>

            <div
              v-else-if="searchMode ? searchResults.length === 0 : rootNodes.length === 0"
              class="py-8 text-center text-gray-500 text-sm"
            >
              Нічого не знайдено.
            </div>

            <div v-else-if="searchMode" class="space-y-1 min-w-max">
              <CpvTenderTreeNode
                v-for="node in searchTree"
                :key="node.id"
                :node="node"
                :depth="0"
                :expanded="searchExpanded"
                :loading-children="emptyLoadingChildren"
                :selected-ids="loadedSelectedIds"
                @toggle-expand="() => {}"
                @toggle-select="toggleSelectById"
              />
            </div>

            <div v-else class="space-y-1 min-w-max">
              <CpvTenderTreeNode
                v-for="node in rootNodes"
                :key="node.id"
                :node="node"
                :depth="0"
                :expanded="expanded"
                :loading-children="loadingChildren"
                :selected-ids="loadedSelectedIds"
                @toggle-expand="toggleExpandById"
                @toggle-select="toggleSelectById"
              />
            </div>
          </div>

          <div class="border rounded-md p-3 space-y-2">
            <div class="text-sm font-medium">Обрані категорії</div>

            <div
              v-if="selectedItems.length === 0"
              class="text-sm text-gray-500"
            >
              Немає обраних категорій.
            </div>

            <div v-else class="max-h-14 overflow-y-auto overflow-x-hidden flex flex-wrap gap-2">
              <UBadge
                v-for="item in selectedItems"
                :key="item.id"
                color="neutral"
                variant="soft"
                class="max-w-full"
              >
                <span class="truncate max-w-[520px]">{{ item.label }}</span>
              </UBadge>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center justify-end gap-2">
            <UButton type="button" variant="outline" @click="closeModal">
              Скасувати
            </UButton>
            <UButton type="button" color="primary" @click="applySelection">
              Обрати
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
type CpvNode = {
  id: number;
  cpv_level_code: string;
  label: string;
  hierarchy_label?: string;
  hierarchy_path?: Array<{
    id: number;
    cpv_level_code: string;
    label: string;
    has_children: boolean;
  }>;
  has_children: boolean;
  children_loaded?: boolean;
  children?: CpvNode[];
};

const props = withDefaults(
  defineProps<{
    label: string;
    placeholder?: string;
    disabled?: boolean;
    required?: boolean;
    selectedIds?: number[];
    selectedLabels?: string[];
    modalTitle?: string;
  }>(),
  {
    placeholder: "Обрати CPV",
    disabled: false,
    required: false,
    selectedIds: () => [],
    selectedLabels: () => [],
    modalTitle: "Обрання категорій CPV",
  },
);

const emit = defineEmits<{
  "update:selectedIds": [value: number[]];
  "update:selectedLabels": [value: string[]];
}>();

const tendersUC = useTendersUseCases();

const isOpen = ref(false);
const search = ref("");
const searchMode = computed(() => Boolean(search.value.trim()));

const loadingRoot = ref(false);
const rootNodes = ref<CpvNode[]>([]);
const expanded = ref<Set<number>>(new Set());
const loadingChildren = ref<Set<number>>(new Set());

const loadingSearch = ref(false);
const searchResults = ref<CpvNode[]>([]);
const emptyLoadingChildren = ref<Set<number>>(new Set());
let searchTimer: ReturnType<typeof setTimeout> | null = null;
let searchRequestId = 0;

const draftSelectedMap = ref<Record<number, { label: string }>>({});

const committedLabelsById = computed<Record<number, string>>(() => {
  const map: Record<number, string> = {};
  const ids = props.selectedIds || [];
  const labels = props.selectedLabels || [];
  ids.forEach((id, i) => {
    const label = labels[i];
    if (label) map[id] = label;
  });
  return map;
});

const buttonText = computed(() => {
  const count = props.selectedIds?.length ?? 0;
  if (!count) return props.placeholder;
  return `Обрати CPV (${count})`;
});

const previewText = computed(() => {
  const ids = props.selectedIds || [];
  if (!ids.length) return "";
  return ids.map((id) => committedLabelsById.value[id] || `#${id}`).join(", ");
});

const selectedItems = computed(() => {
  return Object.entries(draftSelectedMap.value)
    .map(([id, item]) => ({ id: Number(id), label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label));
});

const loadedSelectedIds = computed(() => {
  return new Set<number>(Object.keys(draftSelectedMap.value).map(Number));
});

const searchTree = computed<CpvNode[]>(() => {
  const roots: CpvNode[] = [];
  const nodesById = new Map<number, CpvNode>();

  for (const match of searchResults.value) {
    const path =
      Array.isArray(match.hierarchy_path) && match.hierarchy_path.length
        ? match.hierarchy_path
        : [
            {
              id: match.id,
              cpv_level_code: match.cpv_level_code,
              label: match.label,
              has_children: match.has_children,
            },
          ];

    let parent: CpvNode | null = null;
    for (const step of path) {
      let node = nodesById.get(step.id);
      if (!node) {
        node = {
          id: step.id,
          cpv_level_code: step.cpv_level_code,
          label: step.label,
          has_children: step.has_children,
          children_loaded: false,
          children: [],
        };
        nodesById.set(step.id, node);
      }

      if (parent) {
        if (!parent.children?.some((c) => c.id === node!.id)) {
          parent.children = [...(parent.children || []), node];
        }
      } else if (!roots.some((r) => r.id === node.id)) {
        roots.push(node);
      }
      parent = node;
    }
  }

  return roots;
});

function collectTreeIds(nodes: CpvNode[], out: Set<number>) {
  for (const node of nodes) {
    out.add(node.id);
    if (node.children?.length) {
      collectTreeIds(node.children, out);
    }
  }
}

const searchExpanded = computed(() => {
  const ids = new Set<number>();
  collectTreeIds(searchTree.value, ids);
  return ids;
});

function findNodeById(nodes: CpvNode[], id: number): CpvNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children?.length) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

function setNodeChildren(
  targetId: number,
  nodes: CpvNode[],
  children: CpvNode[],
): boolean {
  for (const node of nodes) {
    if (node.id === targetId) {
      node.children = children;
      node.children_loaded = true;
      return true;
    }
    if (node.children?.length && setNodeChildren(targetId, node.children, children)) {
      return true;
    }
  }
  return false;
}

async function loadRoot() {
  loadingRoot.value = true;
  const { data } = await tendersUC.getCpvChildren();
  rootNodes.value = ((data as CpvNode[]) || []).map((node) => ({
    ...node,
    children_loaded: false,
  }));
  loadingRoot.value = false;
}

async function loadChildren(node: CpvNode) {
  if (!node.has_children) return;
  if (node.children_loaded) return;

  loadingChildren.value = new Set([...loadingChildren.value, node.id]);
  const { data } = await tendersUC.getCpvChildren(node.cpv_level_code);
  const children = ((data as CpvNode[]) || []).map((child) => ({
    ...child,
    children_loaded: false,
  }));
  node.children = children;
  node.children_loaded = true;
  setNodeChildren(node.id, rootNodes.value, children);

  const next = new Set(loadingChildren.value);
  next.delete(node.id);
  loadingChildren.value = next;
}

async function addNodeAndDescendantsToSelection(node: CpvNode): Promise<void> {
  const nextMap = { ...draftSelectedMap.value };
  const stack: CpvNode[] = [node];

  while (stack.length) {
    const current = stack.pop()!;
    nextMap[current.id] = { label: current.label };

    if (!current.has_children) continue;
    await loadChildren(current);
    for (const child of current.children || []) {
      stack.push(child);
    }
  }

  draftSelectedMap.value = nextMap;
}

async function removeNodeAndDescendantsFromSelection(node: CpvNode): Promise<void> {
  const nextMap = { ...draftSelectedMap.value };
  const stack: CpvNode[] = [node];

  while (stack.length) {
    const current = stack.pop()!;
    delete nextMap[current.id];

    if (!current.has_children) continue;
    await loadChildren(current);
    for (const child of current.children || []) {
      stack.push(child);
    }
  }

  draftSelectedMap.value = nextMap;
}

async function toggleSelectNode(node: CpvNode) {
  const currentlySelected = Boolean(draftSelectedMap.value[node.id]);
  if (currentlySelected) {
    await removeNodeAndDescendantsFromSelection(node);
    return;
  }
  await addNodeAndDescendantsToSelection(node);
}

async function toggleSelectById(id: number) {
  const node = findNodeById(rootNodes.value, id) ?? findNodeById(searchTree.value, id);
  if (!node) return;
  await toggleSelectNode(node);
}

async function toggleExpandById(id: number) {
  const node = findNodeById(rootNodes.value, id);
  if (!node) return;

  if (expanded.value.has(id)) {
    const next = new Set(expanded.value);
    next.delete(id);
    expanded.value = next;
    return;
  }

  await loadChildren(node);
  expanded.value = new Set([...expanded.value, id]);
}

function bootstrapDraft() {
  const ids = props.selectedIds || [];
  const map: Record<number, { label: string }> = {};
  ids.forEach((id, i) => {
    map[id] = {
      label: props.selectedLabels?.[i] || committedLabelsById.value[id] || `#${id}`,
    };
  });
  draftSelectedMap.value = map;
}

async function openModal() {
  if (props.disabled) return;

  bootstrapDraft();
  search.value = "";
  searchResults.value = [];
  loadingSearch.value = false;
  searchRequestId += 1;

  isOpen.value = true;
  if (!rootNodes.value.length) {
    await loadRoot();
  }
}

function closeModal() {
  isOpen.value = false;
}

async function loadSearchResults(term: string) {
  const requestId = ++searchRequestId;
  loadingSearch.value = true;
  const { data } = await tendersUC.getCpvChildren(undefined, term);

  if (requestId !== searchRequestId) return;
  searchResults.value = (data as CpvNode[]) || [];
  loadingSearch.value = false;
}

watch(
  () => search.value,
  (value) => {
    if (searchTimer) {
      clearTimeout(searchTimer);
      searchTimer = null;
    }

    const term = value.trim();
    if (!term) {
      searchRequestId += 1;
      loadingSearch.value = false;
      searchResults.value = [];
      return;
    }

    searchTimer = setTimeout(() => {
      void loadSearchResults(term);
    }, 250);
  },
);

onBeforeUnmount(() => {
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
});

function applySelection() {
  const ids = selectedItems.value.map((item) => item.id);
  const labels = selectedItems.value.map((item) => item.label);

  emit("update:selectedIds", ids);
  emit("update:selectedLabels", labels);
  closeModal();
}
</script>
