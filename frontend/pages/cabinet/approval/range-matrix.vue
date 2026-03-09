<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <UAlert
      color="warning"
      variant="subtle"
      icon="i-heroicons-exclamation-triangle"
      title="Курс валют"
      description="Поки що застосовано заглушку: курс усіх валют вважається 1."
    />

    <UCard class="min-h-0 flex-1 border border-gray-200 shadow-sm flex flex-col">
      <template #header>
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-2xl font-bold">Матриця діапазонів</h2>
          <div class="flex items-center gap-2">
            <UButton
              icon="i-heroicons-x-circle"
              color="warning"
              variant="outline"
              :disabled="selectedRanges.length === 0 || selectedRanges.every((item) => !item.is_active)"
              @click="deactivateSelected"
            >
              Деактивувати
            </UButton>
            <UButton
              icon="i-heroicons-trash"
              color="error"
              variant="outline"
              :disabled="selectedRanges.length === 0"
              @click="deleteSelected"
            >
              Видалити
            </UButton>
            <UButton icon="i-heroicons-plus" @click="openCreateModal">Додати діапазон</UButton>
          </div>
        </div>
      </template>

      <div class="flex-1 min-h-0 overflow-auto">
        <div class="min-w-max">
          <UTable
            :data="tableRows"
            :columns="columns"
            :meta="tableMeta"
            class="w-full range-matrix-table"
            @on-select="(_e, row) => toggleSelectRange(Number(row.original.id))"
          >
            <template #select-header>
              <UCheckbox
                :model-value="isAllOnPageSelected"
                :indeterminate="isSomeOnPageSelected && !isAllOnPageSelected"
                aria-label="Обрати всі діапазони"
                @update:model-value="toggleSelectAllOnPage"
              />
            </template>
            <template #select-cell="{ row }">
              <UCheckbox
                :model-value="selectedRangeIds.includes(Number(row.original.id))"
                aria-label="Обрати діапазон"
                @update:model-value="toggleSelectRange(Number(row.original.id))"
                @click.stop
              />
            </template>
            <template #range_name-cell="{ row }">
              <button
                type="button"
                class="text-primary text-left font-medium hover:underline"
                @click.stop="openEditModal(row.original)"
              >
                {{ row.original.range_name }}
              </button>
            </template>
            <template #is_active-cell="{ row }">
              {{ row.original.is_active ? "Так" : "Ні" }}
            </template>
          </UTable>
        </div>
        <div v-if="tableRows.length === 0" class="py-8 text-center text-gray-400">
          Немає діапазонів.
        </div>
      </div>
    </UCard>

    <UModal v-model:open="showRangeModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>{{ editingRangeId ? "Редагувати діапазон" : "Новий діапазон" }}</h3>
          </template>
          <div class="space-y-4">
            <UFormField label="Бюджет з" required>
              <UInput v-model.number="form.budget_from" type="number" step="0.01" />
            </UFormField>
            <UFormField label="Бюджет по" required>
              <UInput v-model.number="form.budget_to" type="number" step="0.01" />
            </UFormField>
            <UFormField label="Валюта" required>
              <USelectMenu
                v-model="form.currency"
                :items="currencyOptions"
                value-key="value"
                class="w-full"
              />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showRangeModal = false">Скасувати</UButton>
              <UButton :loading="saving" @click="save">Зберегти</UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Матриця діапазонів" },
});

const approvalUC = useApprovalUseCases();
const tendersUC = useTendersUseCases();
const { me, refreshMe } = useMe();

const ranges = ref<any[]>([]);
const currencies = ref<any[]>([]);

const selectedRangeIds = ref<number[]>([]);
const editingRangeId = ref<number | null>(null);

const showRangeModal = ref(false);
const saving = ref(false);

const form = reactive({
  budget_from: null as number | null,
  budget_to: null as number | null,
  currency: null as number | null,
  is_active: true,
});

const columns = [
  { id: "select", header: "" },
  { accessorKey: "range_name", header: "Назва діапазону" },
  { accessorKey: "budget_from", header: "Бюджет з" },
  { accessorKey: "budget_to", header: "Бюджет по" },
  { accessorKey: "currency_code", header: "Валюта" },
  { accessorKey: "is_active", header: "Активний" },
];

const currencyOptions = computed(() =>
  currencies.value.map((c: any) => ({
    value: Number(c.id),
    label: `${c.code || ""} ${c.name || ""}`.trim(),
  })),
);

const tableRows = computed(() =>
  ranges.value.map((item: any) => ({
    ...item,
    range_name: `${item.budget_from} - ${item.budget_to}`,
    is_active: item.is_active !== false,
  })),
);

const selectedRanges = computed(() =>
  tableRows.value.filter((item: any) => selectedRangeIds.value.includes(Number(item.id))),
);

const isAllOnPageSelected = computed(
  () =>
    tableRows.value.length > 0 &&
    tableRows.value.every((item: any) => selectedRangeIds.value.includes(Number(item.id))),
);

const isSomeOnPageSelected = computed(() =>
  tableRows.value.some((item: any) => selectedRangeIds.value.includes(Number(item.id))),
);

const tableMeta = computed(() => ({
  class: {
    tr: (row: any) =>
      selectedRangeIds.value.includes(Number(row.original?.id))
        ? "bg-primary-50 cursor-pointer"
        : "cursor-pointer",
  },
}));

async function ensureCompanyId() {
  if (!me.value?.memberships?.length) await refreshMe();
  return Number(me.value?.memberships?.[0]?.company?.id || me.value?.memberships?.[0]?.company || 0);
}

function toggleSelectRange(id: number) {
  if (selectedRangeIds.value.includes(id)) {
    selectedRangeIds.value = selectedRangeIds.value.filter((itemId) => itemId !== id);
    return;
  }
  selectedRangeIds.value = [...selectedRangeIds.value, id];
}

function toggleSelectAllOnPage() {
  const pageIds = tableRows.value.map((item: any) => Number(item.id));
  if (isAllOnPageSelected.value) {
    selectedRangeIds.value = selectedRangeIds.value.filter((itemId) => !pageIds.includes(itemId));
    return;
  }
  selectedRangeIds.value = Array.from(new Set([...selectedRangeIds.value, ...pageIds]));
}

async function loadData() {
  const [{ data: list }, { data: curr }] = await Promise.all([
    approvalUC.getRangeMatrix(),
    tendersUC.getCurrencies(),
  ]);
  ranges.value = Array.isArray(list) ? list : [];
  currencies.value = Array.isArray(curr) ? curr : [];
}

function openCreateModal() {
  editingRangeId.value = null;
  form.budget_from = null;
  form.budget_to = null;
  form.currency = null;
  form.is_active = true;
  showRangeModal.value = true;
}

function openEditModal(range: any) {
  editingRangeId.value = Number(range?.id || 0) || null;
  form.budget_from = Number(range?.budget_from ?? 0);
  form.budget_to = Number(range?.budget_to ?? 0);
  form.currency = Number(range?.currency || 0) || null;
  form.is_active = range?.is_active !== false;
  showRangeModal.value = true;
}

async function save() {
  if (form.budget_from == null || form.budget_to == null || !form.currency) return;
  saving.value = true;
  try {
    if (editingRangeId.value) {
      const { error } = await approvalUC.patchRangeMatrix(editingRangeId.value, {
        budget_from: Number(form.budget_from),
        budget_to: Number(form.budget_to),
        currency: Number(form.currency),
        is_active: form.is_active,
      });
      if (error) return;
    } else {
      const companyId = await ensureCompanyId();
      if (!companyId) return;
      const { error } = await approvalUC.createRangeMatrix({
        company: companyId,
        budget_from: Number(form.budget_from),
        budget_to: Number(form.budget_to),
        currency: Number(form.currency),
      });
      if (error) return;
    }

    showRangeModal.value = false;
    selectedRangeIds.value = [];
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function deactivateSelected() {
  const activeItems = selectedRanges.value.filter((item: any) => item.is_active);
  if (!activeItems.length) return;
  if (!confirm(`Деактивувати обрані діапазони (${activeItems.length})?`)) return;

  for (const item of activeItems) {
    const { error } = await approvalUC.patchRangeMatrix(Number(item.id), {
      is_active: false,
    });
    if (error) return;
  }

  selectedRangeIds.value = [];
  await loadData();
}

async function deleteSelected() {
  if (!selectedRanges.value.length) return;
  if (!confirm(`Видалити обрані діапазони (${selectedRanges.value.length})?`)) return;

  for (const item of selectedRanges.value) {
    const { error } = await approvalUC.deleteRangeMatrix(Number(item.id));
    if (error) return;
  }

  selectedRangeIds.value = [];
  await loadData();
}

onMounted(loadData);
</script>

<style scoped>
.range-matrix-table :deep(table) {
  min-width: max-content;
}

.range-matrix-table :deep(th),
.range-matrix-table :deep(td) {
  white-space: nowrap;
}
</style>
