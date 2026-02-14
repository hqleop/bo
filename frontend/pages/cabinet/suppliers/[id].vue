<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <UIcon name="i-heroicons-arrow-path" class="animate-spin size-8 text-gray-400" />
  </div>
  <div v-else-if="!supplier" class="text-center py-12 text-gray-500">
    Контрагента не знайдено.
  </div>
  <div v-else class="h-full flex flex-col min-h-0">
    <div class="mb-4">
      <NuxtLink to="/cabinet/suppliers" class="text-sm text-primary hover:underline">
        ← Назад до списку контрагентів
      </NuxtLink>
    </div>
    <div class="flex flex-1 min-h-0 gap-6">
      <!-- Ліва частина: основні дані -->
      <div class="w-80 flex-shrink-0">
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">Основні дані</h3>
          </template>
          <dl class="space-y-3">
            <div>
              <dt class="text-sm text-gray-500">Назва компанії</dt>
              <dd class="font-medium">{{ supplier.name }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Код компанії</dt>
              <dd class="font-medium">{{ supplier.edrpou }}</dd>
            </div>
          </dl>
        </UCard>
      </div>

      <!-- Права частина: таби -->
      <div class="flex-1 min-w-0 min-h-0 flex flex-col">
        <UTabs
          v-model="activeTab"
          :items="tabItems"
          value-key="value"
          class="flex-1 min-h-0 flex flex-col"
          content
        >
          <template #content="{ item }">
            <div v-if="item.value === 'tenders'" class="flex-1 min-h-0 overflow-auto">
              <p class="text-sm text-gray-600 mb-3">
                Тендери (закупівлі та продажі), в яких компанія брала або бере участь.
              </p>
              <div v-if="tendersLoading" class="flex items-center justify-center py-8 text-gray-500">
                <UIcon name="i-heroicons-arrow-path" class="animate-spin size-6" />
              </div>
              <div v-else-if="tendersList.length === 0" class="text-sm text-gray-500 py-6">
                Наразі немає даних про участь у тендерах. Список з’явиться після реалізації подачі пропозицій учасниками.
              </div>
              <ul v-else class="space-y-2">
                <li
                  v-for="t in tendersList"
                  :key="t.id + (t.type || '')"
                  class="flex items-center justify-between py-2 px-3 rounded-md border border-gray-200 bg-gray-50/50"
                >
                  <NuxtLink
                    :to="t.type === 'sales' ? `/cabinet/tenders/sales/${t.id}` : `/cabinet/tenders/${t.id}`"
                    class="text-primary hover:underline font-medium"
                  >
                    {{ t.type === 'sales' ? 'Продаж' : 'Закупівля' }} №{{ t.number }}{{ t.tour_number > 1 ? ` (тур ${t.tour_number})` : '' }}
                  </NuxtLink>
                  <span class="text-sm text-gray-500">{{ t.name }}</span>
                </li>
              </ul>
            </div>

            <div v-else class="flex-1 min-h-0 overflow-auto">
              <p class="text-sm text-gray-600 mb-3">
                Користувачі, зареєстровані за цією компанією.
              </p>
              <div v-if="membersLoading" class="flex items-center justify-center py-8 text-gray-500">
                <UIcon name="i-heroicons-arrow-path" class="animate-spin size-6" />
              </div>
              <div v-else-if="members.length === 0" class="text-sm text-gray-500 py-6">
                Немає зареєстрованих агентів за цією компанією.
              </div>
              <UTable
                v-else
                :data="membersTableData"
                :columns="membersColumns"
                class="w-full"
              />
            </div>
          </template>
        </UTabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Картка контрагента" },
});

const route = useRoute();
const supplierId = computed(() => {
  const id = route.params.id;
  if (id === undefined || id === null || id === "") return 0;
  const num = Number(id);
  return Number.isNaN(num) ? 0 : num;
});
const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const loading = ref(true);
const supplier = ref<{ id: number; name: string; edrpou: string } | null>(null);
const activeTab = ref("tenders");
const tabItems = [
  { label: "Тендери", value: "tenders" },
  { label: "Агенти", value: "agents" },
];

const tendersLoading = ref(false);
const tendersList = ref<{ id: number; number: number; tour_number: number; name: string; type?: string }[]>([]);
const membersLoading = ref(false);
const members = ref<any[]>([]);

const membersColumns = [
  { accessorKey: "email", header: "Email" },
  { accessorKey: "displayName", header: "Ім'я" },
  { accessorKey: "roleName", header: "Роль" },
  { accessorKey: "statusLabel", header: "Статус" },
];

const membersTableData = computed(() =>
  members.value.map((m: any) => ({
    email: m.user?.email ?? "—",
    displayName: [m.user?.first_name, m.user?.last_name].filter(Boolean).join(" ") || "—",
    roleName: m.role?.name ?? "—",
    statusLabel: m.status === "approved" ? "Підтверджено" : m.status === "pending" ? "Очікує" : m.status === "rejected" ? "Відхилено" : m.status ?? "—",
  }))
);

async function loadSupplier() {
  const id = supplierId.value;
  if (!id) {
    supplier.value = null;
    loading.value = false;
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetch(`/companies/${id}/`, {
      headers: getAuthHeaders(),
    });
    if (error || !data) {
      supplier.value = null;
      return;
    }
    supplier.value = data as { id: number; name: string; edrpou: string };
  } finally {
    loading.value = false;
  }
}

async function loadTenders() {
  if (!supplier.value) return;
  tendersLoading.value = true;
  try {
    // У майбутньому: endpoint участь компанії в тендерах. Поки порожній список.
    tendersList.value = [];
  } finally {
    tendersLoading.value = false;
  }
}

async function loadMembers() {
  if (!supplier.value) return;
  membersLoading.value = true;
  try {
    const { data, error } = await fetch(`/companies/${supplierId.value}/members/`, {
      headers: getAuthHeaders(),
    });
    if (error) {
      members.value = [];
      return;
    }
    members.value = Array.isArray(data) ? data : [];
  } finally {
    membersLoading.value = false;
  }
}

watch(activeTab, (tab) => {
  if (tab === "tenders") loadTenders();
  if (tab === "agents") loadMembers();
});

watch(supplier, (s) => {
  if (s) {
    loadTenders();
    if (activeTab.value === "agents") loadMembers();
  }
});

onMounted(async () => {
  await loadSupplier();
  if (supplier.value && activeTab.value === "tenders") await loadTenders();
});

watch(supplierId, (id) => {
  if (id) loadSupplier();
});
</script>
