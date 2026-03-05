<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Матриця діапазонів</h2>
      <UButton icon="i-heroicons-plus" @click="openCreateModal">Додати діапазон</UButton>
    </div>

    <UAlert
      color="warning"
      variant="subtle"
      icon="i-heroicons-exclamation-triangle"
      title="Курс валют"
      description="Поки що застосовано заглушку: курс усіх валют вважається 1."
    />

    <UCard class="min-h-0 flex-1 border border-gray-200 shadow-sm">
      <div class="max-h-[65vh] overflow-auto">
        <UTable :data="ranges" :columns="columns" class="w-full" />
      </div>
    </UCard>

    <UModal v-model:open="showCreateModal">
      <template #content>
        <UCard>
          <template #header><h3>Новий діапазон</h3></template>
          <div class="space-y-4">
            <UFormField label="Бюджет з" required>
              <UInput v-model.number="form.budget_from" type="number" step="0.01" />
            </UFormField>
            <UFormField label="Бюджет по" required>
              <UInput v-model.number="form.budget_to" type="number" step="0.01" />
            </UFormField>
            <UFormField label="Валюта" required>
              <USelectMenu v-model="form.currency" :items="currencyOptions" value-key="value" class="w-full" />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showCreateModal = false">Скасувати</UButton>
              <UButton :loading="saving" @click="save">Зберегти</UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: "cabinet", middleware: "auth", meta: { title: "Матриця діапазонів" } });

const approvalUC = useApprovalUseCases();
const tendersUC = useTendersUseCases();
const { me, refreshMe } = useMe();

const ranges = ref<any[]>([]);
const currencies = ref<any[]>([]);
const showCreateModal = ref(false);
const saving = ref(false);
const form = reactive({
  budget_from: null as number | null,
  budget_to: null as number | null,
  currency: null as number | null,
});

const columns = [
  { accessorKey: "budget_from", header: "Бюджет з" },
  { accessorKey: "budget_to", header: "Бюджет по" },
  { accessorKey: "currency_code", header: "Валюта" },
];

const currencyOptions = computed(() =>
  currencies.value.map((c: any) => ({
    value: Number(c.id),
    label: `${c.code || ""} ${c.name || ""}`.trim(),
  }))
);

async function ensureCompanyId() {
  if (!me.value?.memberships?.length) await refreshMe();
  return Number(me.value?.memberships?.[0]?.company?.id || me.value?.memberships?.[0]?.company || 0);
}

async function loadData() {
  const [{ data: list }, { data: curr }] = await Promise.all([
    approvalUC.getRangeMatrix(),
    tendersUC.getCurrencies(),
  ]);
  ranges.value = list;
  currencies.value = Array.isArray(curr) ? curr : [];
}

function openCreateModal() {
  form.budget_from = null;
  form.budget_to = null;
  form.currency = null;
  showCreateModal.value = true;
}

async function save() {
  const companyId = await ensureCompanyId();
  if (!companyId || form.budget_from == null || form.budget_to == null || !form.currency) return;
  saving.value = true;
  try {
    // Currency rates integration is not implemented yet.
    // Temporary business rule: all currency rates are treated as 1.
    const { error } = await approvalUC.createRangeMatrix({
      company: companyId,
      budget_from: Number(form.budget_from),
      budget_to: Number(form.budget_to),
      currency: Number(form.currency),
    });
    if (error) return;
    showCreateModal.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>
