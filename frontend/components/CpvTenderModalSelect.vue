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
      <UCard class="w-full max-h-[90vh] flex-1 flex-col">
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
            class="border rounded-md p-2 h-[48vh] overflow-y-auto overflow-x-auto"
          >
            <div v-if="loadingRoot" class="py-8 text-center text-gray-500">
              <UIcon
                name="i-heroicons-arrow-path"
                class="animate-spin size-5 mx-auto"
              />
            </div>

            <div
              v-else-if="visibleNodes.length === 0"
              class="py-8 text-center text-gray-500 text-sm"
            >
              Нічого не знайдено.
            </div>

            <div v-else class="space-y-1 min-w-max">
              <CpvTenderTreeNode
                v-for="node in visibleNodes"
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

            <div v-else class="max-h-32 overflow-auto flex flex-wrap gap-2">
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
  has_children: boolean;
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
const loadingRoot = ref(false);
const rootNodes = ref<CpvNode[]>([]);
const expanded = ref<Set<number>>(new Set());
const loadingChildren = ref<Set<number>>(new Set());

const draftSelectedMap = ref<Record<number, { label: string; code?: string }>>(
  {},
);
const draftSelectedCodes = ref<Set<string>>(new Set());

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
  const entries = Object.entries(draftSelectedMap.value)
    .map(([id, item]) => ({ id: Number(id), label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label));
  return entries;
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
      return true;
    }
    if (
      node.children?.length &&
      setNodeChildren(targetId, node.children, children)
    ) {
      return true;
    }
  }
  return false;
}

async function loadRoot() {
  loadingRoot.value = true;
  const { data } = await tendersUC.getCpvChildren();
  rootNodes.value = (data as CpvNode[]) || [];
  hydrateCodesFromLoadedNodes();
  loadingRoot.value = false;
}

async function loadChildren(node: CpvNode) {
  if (!node.has_children) return;
  if (node.children?.length) return;

  loadingChildren.value = new Set([...loadingChildren.value, node.id]);
  const { data } = await tendersUC.getCpvChildren(node.cpv_level_code);
  const children = (data as CpvNode[]) || [];
  setNodeChildren(node.id, rootNodes.value, children);
  hydrateCodesFromLoadedNodes();

  const next = new Set(loadingChildren.value);
  next.delete(node.id);
  loadingChildren.value = next;
}

function traverse(nodes: CpvNode[], visitor: (node: CpvNode) => void) {
  for (const node of nodes) {
    visitor(node);
    if (node.children?.length) {
      traverse(node.children, visitor);
    }
  }
}

function isCodeSelected(code?: string): boolean {
  if (!code) return false;
  for (const selectedCode of draftSelectedCodes.value) {
    if (code === selectedCode || code.startsWith(selectedCode)) {
      return true;
    }
  }
  return false;
}

function hydrateCodesFromLoadedNodes() {
  const nextMap = { ...draftSelectedMap.value };
  const nextCodes = new Set(draftSelectedCodes.value);
  traverse(rootNodes.value, (node) => {
    const selected = nextMap[node.id];
    if (selected && !selected.code) {
      nextMap[node.id] = { ...selected, code: node.cpv_level_code };
      nextCodes.add(node.cpv_level_code);
    }
  });
  draftSelectedMap.value = nextMap;
  draftSelectedCodes.value = nextCodes;
}

async function toggleSelectById(id: number) {
  const node = findNodeById(rootNodes.value, id);
  if (!node) return;

  const code = node.cpv_level_code;
  const currentlySelected = isCodeSelected(code);

  if (!currentlySelected) {
    const nextMap = { ...draftSelectedMap.value };
    nextMap[node.id] = { label: node.label, code };
    draftSelectedMap.value = nextMap;

    const nextCodes = new Set(draftSelectedCodes.value);
    for (const selectedCode of Array.from(nextCodes)) {
      if (selectedCode.startsWith(code)) nextCodes.delete(selectedCode);
    }
    nextCodes.add(code);
    draftSelectedCodes.value = nextCodes;
    return;
  }

  const nextMap: Record<number, { label: string; code?: string }> = {};
  for (const [rawId, item] of Object.entries(draftSelectedMap.value)) {
    const itemCode = item.code;
    if (!itemCode) {
      nextMap[Number(rawId)] = item;
      continue;
    }
    if (!(itemCode === code || itemCode.startsWith(code))) {
      nextMap[Number(rawId)] = item;
    }
  }
  draftSelectedMap.value = nextMap;

  const nextCodes = new Set(draftSelectedCodes.value);
  for (const selectedCode of Array.from(nextCodes)) {
    if (selectedCode === code || selectedCode.startsWith(code)) {
      nextCodes.delete(selectedCode);
    }
  }
  draftSelectedCodes.value = nextCodes;
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

const loadedSelectedIds = computed(() => {
  const ids = new Set<number>();
  traverse(rootNodes.value, (node) => {
    if (isCodeSelected(node.cpv_level_code)) {
      ids.add(node.id);
    }
  });
  return ids;
});

function filterTree(nodes: CpvNode[], term: string): CpvNode[] {
  const normalized = term.trim().toLowerCase();
  if (!normalized) return nodes;

  const out: CpvNode[] = [];
  for (const node of nodes) {
    const children = filterTree(node.children || [], normalized);
    const selfMatch = node.label.toLowerCase().includes(normalized);
    if (selfMatch || children.length) {
      out.push({ ...node, children });
    }
  }
  return out;
}

const visibleNodes = computed(() => {
  return filterTree(rootNodes.value, search.value);
});

function bootstrapDraft() {
  const ids = props.selectedIds || [];
  const map: Record<number, { label: string; code?: string }> = {};
  ids.forEach((id, i) => {
    map[id] = {
      label:
        props.selectedLabels?.[i] || committedLabelsById.value[id] || `#${id}`,
    };
  });
  draftSelectedMap.value = map;
  draftSelectedCodes.value = new Set();
  hydrateCodesFromLoadedNodes();
}

async function openModal() {
  if (props.disabled) return;
  bootstrapDraft();
  search.value = "";
  isOpen.value = true;
  if (!rootNodes.value.length) {
    await loadRoot();
  }
}

function closeModal() {
  isOpen.value = false;
}

function applySelection() {
  const ids = Object.keys(draftSelectedMap.value).map((id) => Number(id));
  const labels = ids.map((id) => draftSelectedMap.value[id]?.label || `#${id}`);
  emit("update:selectedIds", ids);
  emit("update:selectedLabels", labels);
  closeModal();
}
</script>
