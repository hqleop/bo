<template>
  <div class="h-full flex flex-col min-h-0">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Контрагенти</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">
        Додати контрагента
      </UButton>
    </div>

    <div class="flex flex-1 min-h-0 gap-4">
      <!-- Таблиця зліва -->
      <div class="flex-1 min-w-0 min-h-0 flex flex-col border rounded-lg bg-white">
        <div class="flex-1 min-h-0 overflow-auto">
          <UTable
            v-if="filteredSuppliers.length > 0"
            :data="filteredSuppliers"
            :columns="columns"
            class="w-full"
          >
            <template #name-cell="{ row }">
              <NuxtLink
                :to="`/cabinet/suppliers/${row.original.id}`"
                class="text-primary hover:underline font-medium"
              >
                {{ row.original.name }}
              </NuxtLink>
            </template>
          </UTable>
          <div
            v-else-if="loading"
            class="flex items-center justify-center py-12 text-gray-500"
          >
            <UIcon name="i-heroicons-arrow-path" class="animate-spin size-6" />
          </div>
          <div
            v-else
            class="text-center text-gray-500 py-12"
          >
            {{ searchTerm ? 'Контрагентів за пошуком не знайдено.' : 'Немає контрагентів. Додайте першого вручну або вони з\'являться після участі в тендерах.' }}
          </div>
        </div>
      </div>

      <!-- Пошук справа -->
      <aside class="w-64 flex-shrink-0">
        <UFormField label="Пошук контрагента">
          <UInput
            v-model="searchTerm"
            placeholder="Назва або код"
            class="w-full"
          />
        </UFormField>
      </aside>
    </div>

    <!-- Модальне вікно додавання -->
    <UModal v-model:open="showAddModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>Додати контрагента</h3>
          </template>
          <UForm :state="addForm" @submit="onAdd" class="space-y-4">
            <UFormField label="Код компанії" name="edrpou" required>
              <UInput v-model="addForm.edrpou" placeholder="ЄДРПОУ або інший код" />
            </UFormField>
            <UFormField label="Назва компанії" name="name" required>
              <UInput v-model="addForm.name" placeholder="Назва компанії" />
            </UFormField>
            <div class="flex gap-4">
              <UButton
                variant="outline"
                class="flex-1"
                type="button"
                @click="showAddModal = false"
              >
                Скасувати
              </UButton>
              <UButton type="submit" class="flex-1" :loading="saving">
                Додати
              </UButton>
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Контрагенти" },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const loading = ref(true);
const saving = ref(false);
/** Відношення контрагентів: додані вручну + (згодом) участь у тендерах */
const supplierRelations = ref<{ id: number; supplier_company: { id: number; edrpou: string; name: string }; source: string }[]>([]);
const searchTerm = ref("");
const showAddModal = ref(false);
const addForm = reactive({ edrpou: "", name: "" });

const columns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "edrpou", header: "Код компанії" },
];

/** Для таблиці: один ряд = один контрагент (id для посилання на картку) */
const filteredSuppliers = computed(() => {
  const list = supplierRelations.value.map((r) => ({
    id: r.supplier_company.id,
    name: r.supplier_company.name,
    edrpou: r.supplier_company.edrpou ?? "",
  }));
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) return list;
  return list.filter(
    (s) =>
      s.name.toLowerCase().includes(term) ||
      (s.edrpou && s.edrpou.toLowerCase().includes(term))
  );
});

async function loadSuppliers() {
  loading.value = true;
  try {
    const { data } = await fetch("/company-suppliers/", { headers: getAuthHeaders() });
    supplierRelations.value = Array.isArray(data) ? data : [];
  } finally {
    loading.value = false;
  }
}

async function onAdd() {
  if (!addForm.edrpou.trim() || !addForm.name.trim()) return;
  saving.value = true;
  const headers = getAuthHeaders();
  try {
    let companyId: number | null = null;
    const { data: createData, error: createError } = await fetch("/companies/", {
      method: "POST",
      body: { edrpou: addForm.edrpou.trim(), name: addForm.name.trim() },
      headers,
    });
    if (createError) {
      const errMsg = typeof createError === "string" ? createError : (createError as any)?.supplier_company_id ?? "Помилка";
      if (errMsg.includes("вже існує") || errMsg.includes("already exists")) {
        const { data: companies } = await fetch("/companies/", { headers });
        const list = Array.isArray(companies) ? companies : [];
        const found = list.find((c: any) => String(c.edrpou).trim() === addForm.edrpou.trim());
        if (found) companyId = found.id;
      }
      if (!companyId) {
        alert(errMsg);
        return;
      }
    } else {
      companyId = (createData as any)?.id ?? null;
    }
    if (!companyId) {
      alert("Не вдалося визначити компанію");
      return;
    }
    const { error: linkError } = await fetch("/company-suppliers/", {
      method: "POST",
      body: { supplier_company_id: companyId },
      headers,
    });
    if (linkError) {
      alert(typeof linkError === "string" ? linkError : (linkError as any)?.supplier_company_id ?? "Помилка додавання до списку контрагентів");
      return;
    }
    showAddModal.value = false;
    addForm.edrpou = "";
    addForm.name = "";
    await loadSuppliers();
  } finally {
    saving.value = false;
  }
}

onMounted(() => loadSuppliers());
</script>
