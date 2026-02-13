<template>
  <UFormField :label="label">
    <UPopover v-model:open="isOpen">
      <UButton block variant="outline" :disabled="disabled">
        <span v-if="selectedText">{{ selectedText }}</span>
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
              <UButton
                v-for="node in searchedNodes"
                :key="node.id"
                size="xs"
                variant="ghost"
                class="w-full justify-start truncate"
                :class="{ 'font-semibold text-primary': selectedId === node.id }"
                @click="selectNode(node)"
              >
                {{ node.label }}
              </UButton>
            </template>
            <template v-else>
              <CpvLazyNode
                v-for="node in rootNodes"
                :key="node.id"
                :node="node"
                :depth="0"
                :selected-id="selectedId"
                :expanded="expanded"
                :loading-children="loadingChildren"
                @toggle-expand="toggleExpand"
                @select="selectNode"
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
    selectedId?: number;
    selectedLabel?: string;
  }>(),
  {
    placeholder: "Оберіть CPV",
    disabled: false,
    selectedId: undefined,
    selectedLabel: "",
  },
);

const emit = defineEmits<{
  "update:selectedId": [value?: number];
}>();

const { fetch } = useApi();
const { getAuthHeaders } = useAuth();

const isOpen = ref(false);
const search = ref("");
const rootNodes = ref<CpvNode[]>([]);
const loadingRoot = ref(false);
const loadingChildren = ref<Set<number>>(new Set());
const expanded = ref<Set<number>>(new Set());
const selectedTextInternal = ref("");

const selectedId = computed(() => props.selectedId);
const selectedText = computed(() => {
  return selectedTextInternal.value || props.selectedLabel || "";
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

function setNodeChildren(targetId: number, nodes: CpvNode[], children: CpvNode[]): boolean {
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

function findNodeById(targetId: number, nodes: CpvNode[]): CpvNode | null {
  for (const n of nodes) {
    if (n.id === targetId) return n;
    if (n.children?.length) {
      const found = findNodeById(targetId, n.children);
      if (found) return found;
    }
  }
  return null;
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
  const { data } = await fetch(`/cpv/children/?parent_level_code=${encodeURIComponent(node.cpv_level_code)}`, {
    headers: getAuthHeaders(),
  });
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

function selectNode(node: CpvNode) {
  selectedTextInternal.value = node.label;
  emit("update:selectedId", node.id);
  isOpen.value = false;
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
  () => props.selectedId,
  (id) => {
    if (!id) {
      selectedTextInternal.value = "";
      return;
    }
    const node = findNodeById(id, rootNodes.value);
    if (node) selectedTextInternal.value = node.label;
  },
);
</script>
