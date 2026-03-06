<template>
  <div class="h-full flex flex-col min-h-0">
    <h2 class="text-2xl font-bold mb-4">Налаштування</h2>
    <div class="flex-1 min-h-0 bg-white rounded-lg shadow p-4 flex flex-col">
      <UTabs
        v-model="activeTab"
        :items="tabItems"
        value-key="value"
        :ui="{
          list: 'w-fit',
          trigger: 'min-w-[120px] px-3 py-1 text-xs sm:min-w-[140px]',
        }"
        class="flex-1 min-h-0 flex flex-col"
        content
      >
        <template #content="{ item }">
          <!-- Загальні налаштування -->
          <div
            v-if="item.value === 'general'"
            class="flex-1 min-h-0 overflow-auto"
          >
            <div v-if="loading" class="py-8 text-center text-gray-500">
              <UIcon
                name="i-heroicons-arrow-path"
                class="animate-spin size-6 mx-auto"
              />
            </div>
            <div v-else-if="!company" class="py-8 text-center text-gray-500">
              Дані компанії недоступні.
            </div>
            <div v-else class="max-w-xl space-y-4">
              <UFormField label="Назва компанії">
                <UInput :model-value="company.name" disabled />
              </UFormField>
              <UFormField label="Код компанії">
                <UInput :model-value="company.edrpou" disabled />
              </UFormField>
            </div>
          </div>

          <!-- Зв'язок із категорією CPV -->
          <div
            v-else
            class="flex-1 min-h-0 flex flex-col gap-4"
          >
            <div class="max-w-xl">
              <CpvTenderModalSelect
                label="Додати категорії CPV"
                placeholder="Пошук та обрання категорій CPV"
                :selected-ids="assignedCpvIds"
                :selected-labels="assignedCpvLabels"
                @update:selected-ids="onCpvSelectedIds"
                @update:selected-labels="onCpvSelectedLabels"
              />
              <p class="mt-2 text-xs text-gray-500">
                Обрані тут CPV-категорії будуть закріплені за компанією та
                використовуватимуться для участі в тендерах.
              </p>
            </div>

            <div class="flex-1 min-h-0 flex flex-col">
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-sm font-semibold">
                  Закріплені категорії CPV
                </h3>
                <UButton
                  size="xs"
                  variant="outline"
                  color="red"
                  icon="i-heroicons-trash"
                  :disabled="selectedAssignedIds.length === 0 || saving"
                  @click="removeSelectedCpvs"
                >
                  Видалити обрані
                </UButton>
              </div>

              <div
                v-if="loading"
                class="py-8 text-center text-gray-500 flex-1 flex items-center justify-center"
              >
                <UIcon
                  name="i-heroicons-arrow-path"
                  class="animate-spin size-6 mx-auto"
                />
              </div>
              <div
                v-else-if="assignedCpvs.length === 0"
                class="py-8 text-center text-gray-500 flex-1 flex items-center justify-center"
              >
                Немає закріплених CPV-категорій.
              </div>
              <div v-else class="flex-1 min-h-0 overflow-auto">
                <UTable
                  :data="assignedCpvs"
                  :columns="cpvTableColumns"
                  class="w-full"
                >
                  <template #select-header>
                    <UCheckbox
                      :model-value="isAllSelected"
                      :indeterminate="isSomeSelected && !isAllSelected"
                      aria-label="Обрати всі"
                      @update:model-value="toggleSelectAll"
                    />
                  </template>
                  <template #select-cell="{ row }">
                    <UCheckbox
                      :model-value="selectedAssignedIds.includes(row.original.id)"
                      aria-label="Обрати рядок"
                      @update:model-value="toggleSelect(row.original.id)"
                      @click.stop
                    />
                  </template>
                </UTable>
              </div>

              <div class="mt-4 flex justify-end">
                <UButton
                  color="primary"
                  :loading="saving"
                  :disabled="saving || !company"
                  @click="saveCpvs"
                >
                  Зберегти зміни
                </UButton>
              </div>
            </div>
          </div>
        </template>
      </UTabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUsersUseCases } from "~/domains/users/users.useCases";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Налаштування",
  },
});

const usersUC = useUsersUseCases();

const activeTab = ref("general");
const tabItems = [
  { label: "Загальні налаштування", value: "general" },
  { label: "Зв'язок із категорією CPV", value: "cpv" },
];

const loading = ref(true);
const saving = ref(false);
const company = ref<{ id: number; name: string; edrpou: string } | null>(null);

type AssignedCpv = { id: number; label: string };
const assignedCpvs = ref<AssignedCpv[]>([]);
const assignedCpvIds = ref<number[]>([]);
const assignedCpvLabels = ref<string[]>([]);
const selectedAssignedIds = ref<number[]>([]);

const cpvTableColumns = [
  { id: "select", header: "" },
  { accessorKey: "label", header: "CPV-категорія" },
];

const isAllSelected = computed(() => {
  const ids = selectedAssignedIds.value;
  const rows = assignedCpvs.value;
  return rows.length > 0 && rows.every((r) => ids.includes(r.id));
});

const isSomeSelected = computed(() => {
  const ids = selectedAssignedIds.value;
  return assignedCpvs.value.some((r) => ids.includes(r.id));
});

const syncAssignedCpvs = (ids: number[], labels: string[]) => {
  const map = new Map<number, string>();
  assignedCpvs.value.forEach((c) => map.set(c.id, c.label));
  ids.forEach((id, index) => {
    const label = labels[index] || map.get(id) || `#${id.toString()}`;
    map.set(id, label);
  });
  assignedCpvs.value = ids.map((id) => ({
    id,
    label: map.get(id) || `#${id.toString()}`,
  }));
  selectedAssignedIds.value = selectedAssignedIds.value.filter((id) =>
    ids.includes(id),
  );
};

const onCpvSelectedIds = (ids: number[]) => {
  assignedCpvIds.value = ids;
  syncAssignedCpvs(ids, assignedCpvLabels.value);
};

const onCpvSelectedLabels = (labels: string[]) => {
  assignedCpvLabels.value = labels;
  syncAssignedCpvs(assignedCpvIds.value, labels);
};
const toggleSelect = (id: number) => {
  const idx = selectedAssignedIds.value.indexOf(id);
  if (idx === -1) {
    selectedAssignedIds.value = [...selectedAssignedIds.value, id];
  } else {
    selectedAssignedIds.value = selectedAssignedIds.value.filter((x) => x !== id);
  }
};

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedAssignedIds.value = [];
  } else {
    selectedAssignedIds.value = assignedCpvs.value.map((c) => c.id);
  }
};

const removeSelectedCpvs = () => {
  if (!selectedAssignedIds.value.length) return;
  const toRemove = new Set(selectedAssignedIds.value);
  const remaining = assignedCpvs.value.filter((c) => !toRemove.has(c.id));
  assignedCpvs.value = remaining;
  assignedCpvIds.value = remaining.map((c) => c.id);
  assignedCpvLabels.value = remaining.map((c) => c.label);
  selectedAssignedIds.value = [];
};

const loadData = async () => {
  loading.value = true;
  try {
    const { data, error } = await usersUC.getCurrentCompanyCpvs();
    if (error || !data) {
      company.value = null;
      assignedCpvs.value = [];
      assignedCpvIds.value = [];
      assignedCpvLabels.value = [];
      return;
    }
    company.value = {
      id: data.id,
      name: data.name,
      edrpou: data.edrpou,
    };
    const cpvs =
      Array.isArray(data.cpv_categories) && data.cpv_categories.length
        ? (data.cpv_categories as { id: number; label?: string; cpv_code?: string; name_ua?: string }[])
        : [];
    assignedCpvs.value = cpvs.map((c) => ({
      id: c.id,
      label:
        c.label ||
        `${c.cpv_code || ""} - ${c.name_ua || ""}`.trim() ||
        `#${c.id}`,
    }));
    assignedCpvIds.value = assignedCpvs.value.map((c) => c.id);
    assignedCpvLabels.value = assignedCpvs.value.map((c) => c.label);
    selectedAssignedIds.value = [];
  } finally {
    loading.value = false;
  }
};

const saveCpvs = async () => {
  if (!company.value) return;
  saving.value = true;
  try {
    const { error } = await usersUC.updateCurrentCompanyCpvs(
      assignedCpvs.value.map((c) => c.id),
    );
    if (error) {
      alert("Помилка збереження CPV-категорій.");
      return;
    }
    await loadData();
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  await loadData();
});
</script>
