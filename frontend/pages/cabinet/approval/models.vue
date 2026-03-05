<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Довідник моделей</h2>
      <div class="flex items-center gap-2">
        <UButton
          icon="i-heroicons-trash"
          color="error"
          variant="outline"
          :disabled="selectedModelIds.length === 0"
          @click="deleteSelectedModels"
        >
          Видалити модель
        </UButton>
        <UButton icon="i-heroicons-plus" @click="openCreateModal">Додати модель</UButton>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4 min-h-0 flex-1">
      <UCard class="min-h-0 border border-gray-200 shadow-sm">
        <div class="max-h-[70vh] overflow-auto">
          <UTable :data="filteredModels" :columns="columns" class="w-full">
            <template #select-header>
              <UCheckbox
                :model-value="isAllFilteredSelected"
                :indeterminate="isSomeFilteredSelected && !isAllFilteredSelected"
                aria-label="Обрати всі моделі"
                @update:model-value="toggleSelectAllFiltered"
              />
            </template>
            <template #select-cell="{ row }">
              <UCheckbox
                :model-value="selectedModelIds.includes(Number(row.original.id))"
                aria-label="Обрати модель"
                @update:model-value="toggleSelectModel(Number(row.original.id))"
                @click.stop
              />
            </template>
            <template #name-cell="{ row }">
              <button class="text-left hover:underline" @click="openEditModal(row.original)">
                {{ row.original.name }}
              </button>
            </template>
          </UTable>
        </div>
      </UCard>

      <UCard class="border border-gray-200 shadow-sm">
        <template #header><h3 class="font-semibold">Фільтри</h3></template>
        <div class="space-y-4">
          <UFormField label="Застосування">
            <USelectMenu
              v-model="filters.application"
              :items="[{ value: '', label: 'Усі' }, ...applicationOptions]"
              value-key="value"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Категорія">
            <USelectMenu
              v-model="filters.categoryId"
              :items="categoryOptionsWithEmpty"
              value-key="value"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Діапазон">
            <USelectMenu
              v-model="filters.rangeId"
              :items="rangeOptionsWithEmpty"
              value-key="value"
              class="w-full"
            />
          </UFormField>
        </div>
      </UCard>
    </div>

    <UModal v-model:open="showModal" :ui="{ content: 'max-w-5xl' }">
      <template #content>
        <UCard>
          <template #header><h3>Модель погодження</h3></template>
          <div class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UFormField label="Назва моделі" required>
                <UInput v-model="form.name" />
              </UFormField>
              <UFormField label="Застосування" required>
                <USelectMenu
                  v-model="form.application"
                  :items="applicationOptions"
                  value-key="value"
                  class="w-full"
                />
              </UFormField>
              <UFormField label="Категорія">
                <USelectMenu
                  v-model="form.category_ids"
                  :items="categoryOptions"
                  value-key="value"
                  multiple
                  class="w-full"
                />
              </UFormField>
              <UFormField label="Діапазон застосування">
                <USelectMenu
                  v-model="form.range_ids"
                  :items="rangeOptions"
                  value-key="value"
                  multiple
                  class="w-full"
                />
              </UFormField>
            </div>

            <div class="border border-gray-200 rounded-lg overflow-hidden">
              <table class="w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="text-left p-2 border-b border-gray-200">Роль</th>
                    <th class="text-left p-2 border-b border-gray-200">Підготовка процедури</th>
                    <th class="text-left p-2 border-b border-gray-200">Затвердження</th>
                    <th class="w-8 border-b border-gray-200"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in form.steps" :key="idx">
                    <td class="p-2 border-b border-gray-200">
                      <USelectMenu
                        v-model="row.role"
                        :items="roleOptionsByApplication"
                        value-key="value"
                        class="w-full"
                      />
                    </td>
                    <td class="p-2 border-b border-gray-200">
                      <USelectMenu
                        v-model="row.preparation_rule"
                        :items="ruleOptions"
                        value-key="value"
                        class="w-full"
                      />
                    </td>
                    <td class="p-2 border-b border-gray-200">
                      <USelectMenu
                        v-model="row.approval_rule"
                        :items="ruleOptions"
                        value-key="value"
                        class="w-full"
                      />
                    </td>
                    <td class="p-2 border-b border-gray-200">
                      <UButton
                        icon="i-heroicons-trash"
                        size="xs"
                        color="error"
                        variant="ghost"
                        @click="form.steps.splice(idx, 1)"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <UButton
              icon="i-heroicons-plus"
              variant="outline"
              @click="addStepRow"
            >
              Додати роль
            </UButton>

            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showModal = false">Скасувати</UButton>
              <UButton :loading="saving" @click="saveModel">Зберегти</UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: "cabinet", middleware: "auth", meta: { title: "Довідник моделей" } });

const approvalUC = useApprovalUseCases();
const tendersUC = useTendersUseCases();
const { me, refreshMe } = useMe();

const list = ref<any[]>([]);
const categories = ref<any[]>([]);
const ranges = ref<any[]>([]);
const roles = ref<any[]>([]);
const selectedModelIds = ref<number[]>([]);
const editingModelId = ref<number | null>(null);

const showModal = ref(false);
const saving = ref(false);
const form = reactive({
  name: "",
  application: "procurement" as "procurement" | "sales",
  category_ids: [] as number[],
  range_ids: [] as number[],
  steps: [] as Array<{
    role: number | null;
    order?: number;
    preparation_rule: "one_of" | "all";
    approval_rule: "one_of" | "all";
  }>,
});

const filters = reactive({
  application: "",
  categoryId: null as number | null,
  rangeId: null as number | null,
});

const columns = [
  { id: "select", header: "" },
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "application_label", header: "Застосування" },
  { accessorKey: "is_active", header: "Активна" },
];

const applicationOptions = [
  { value: "sales", label: "Тендер-Продаж" },
  { value: "procurement", label: "Тендер-Закупівля" },
];
const ruleOptions = [
  { value: "one_of", label: "Один зі" },
  { value: "all", label: "Усі" },
];

const categoryOptions = computed(() =>
  categories.value.map((c: any) => ({ value: Number(c.id), label: c.name || c.label || String(c.id) }))
);
const categoryOptionsWithEmpty = computed(() => [{ value: null, label: "Усі" }, ...categoryOptions.value]);
const rangeOptions = computed(() =>
  ranges.value.map((r: any) => ({
    value: Number(r.id),
    label: `${r.budget_from} - ${r.budget_to} ${r.currency_code || ""}`.trim(),
  }))
);
const rangeOptionsWithEmpty = computed(() => [{ value: null, label: "Усі" }, ...rangeOptions.value]);
const roleOptionsByApplication = computed(() =>
  roles.value
    .filter((r: any) => r.application === form.application)
    .map((r: any) => ({ value: Number(r.id), label: r.name }))
);

const filteredModels = computed(() => {
  return list.value.filter((m: any) => {
    if (filters.application && m.application !== filters.application) return false;
    if (filters.categoryId && !(Array.isArray(m.categories) && m.categories.includes(filters.categoryId))) return false;
    if (filters.rangeId && !(Array.isArray(m.ranges) && m.ranges.includes(filters.rangeId))) return false;
    return true;
  });
});
const filteredModelIds = computed(() =>
  filteredModels.value.map((m: any) => Number(m.id)).filter((id: number) => Number.isFinite(id))
);
const isAllFilteredSelected = computed(() =>
  filteredModelIds.value.length > 0 && filteredModelIds.value.every((id) => selectedModelIds.value.includes(id))
);
const isSomeFilteredSelected = computed(() =>
  filteredModelIds.value.some((id) => selectedModelIds.value.includes(id))
);

async function ensureCompanyId() {
  if (!me.value?.memberships?.length) await refreshMe();
  return Number(me.value?.memberships?.[0]?.company?.id || me.value?.memberships?.[0]?.company || 0);
}

function addStepRow() {
  form.steps.push({ role: null, preparation_rule: "one_of", approval_rule: "one_of" });
}

function openCreateModal() {
  editingModelId.value = null;
  form.name = "";
  form.application = "procurement";
  form.category_ids = [];
  form.range_ids = [];
  form.steps = [];
  showModal.value = true;
}

function openEditModal(model: any) {
  editingModelId.value = Number(model.id);
  form.name = model?.name || "";
  form.application = model?.application === "sales" ? "sales" : "procurement";
  form.category_ids = Array.isArray(model?.categories)
    ? model.categories.map((id: any) => Number(id)).filter((id: number) => Number.isFinite(id))
    : [];
  form.range_ids = Array.isArray(model?.ranges)
    ? model.ranges.map((id: any) => Number(id)).filter((id: number) => Number.isFinite(id))
    : [];
  form.steps = Array.isArray(model?.steps)
    ? model.steps.map((s: any, idx: number) => ({
        role: s?.role ? Number(s.role) : null,
        order: Number(s?.order) || idx + 1,
        preparation_rule: s?.preparation_rule === "all" ? "all" : "one_of",
        approval_rule: s?.approval_rule === "all" ? "all" : "one_of",
      }))
    : [];
  showModal.value = true;
}

function toggleSelectModel(id: number) {
  if (selectedModelIds.value.includes(id)) {
    selectedModelIds.value = selectedModelIds.value.filter((x) => x !== id);
    return;
  }
  selectedModelIds.value = [...selectedModelIds.value, id];
}

function toggleSelectAllFiltered() {
  if (isAllFilteredSelected.value) {
    selectedModelIds.value = selectedModelIds.value.filter((id) => !filteredModelIds.value.includes(id));
    return;
  }
  selectedModelIds.value = Array.from(new Set([...selectedModelIds.value, ...filteredModelIds.value]));
}

async function loadData() {
  const [{ data: models }, { data: cats }, { data: rangesData }, { data: rolesData }] =
    await Promise.all([
      approvalUC.getApprovalModels(),
      tendersUC.getCategories(),
      approvalUC.getRangeMatrix(),
      approvalUC.getModelRoles(),
    ]);
  list.value = models;
  categories.value = Array.isArray(cats) ? cats : [];
  ranges.value = rangesData;
  roles.value = rolesData;
}

async function saveModel() {
  const companyId = await ensureCompanyId();
  const name = form.name.trim();
  if (!companyId || !name) return;
  saving.value = true;
  try {
    const payload = {
      company: companyId,
      name,
      application: form.application,
      categories_ids: form.category_ids,
      range_ids: form.range_ids,
      steps: form.steps
        .filter((s) => s.role)
        .map((s, idx) => ({
          role: Number(s.role),
          order: idx + 1,
          preparation_rule: s.preparation_rule,
          approval_rule: s.approval_rule,
        })),
    };
    const { error } = editingModelId.value
      ? await approvalUC.patchApprovalModel(editingModelId.value, payload)
      : await approvalUC.createApprovalModel(payload);
    if (error) return;
    selectedModelIds.value = [];
    editingModelId.value = null;
    showModal.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function deleteSelectedModels() {
  if (!selectedModelIds.value.length) return;
  if (!confirm(`Видалити обрані моделі (${selectedModelIds.value.length})?`)) return;
  const ids = [...selectedModelIds.value];
  for (const id of ids) {
    const { error } = await approvalUC.deleteApprovalModel(id);
    if (error) return;
  }
  selectedModelIds.value = [];
  await loadData();
}

onMounted(loadData);
</script>
