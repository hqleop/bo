<template>
  <div class="h-full flex flex-col min-h-0">
    <div class="flex-shrink-0 flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">
        {{ viewType === 'purchase' ? 'Журнал закупівель' : 'Журнал продажів' }}
      </h2>
      <UButton
        icon="i-heroicons-plus"
        type="button"
        @click="navigateTo(createUrl)"
      >
        Створити процедуру
      </UButton>
    </div>

    <!-- Область таблиці зі скролом -->
    <div class="flex-1 min-h-0 overflow-auto">
      <UTable
        v-if="tableData.length > 0"
        :data="tableData"
        :columns="tableColumns"
        class="w-full"
      >
        <template #number-cell="{ row }">
          <NuxtLink
            v-if="viewType === 'purchase'"
            :to="`/cabinet/tenders/${row.original.id}`"
            class="text-primary hover:underline font-medium"
          >
            №{{ row.original.number }}{{ row.original.tour_number > 1 ? ` (тур ${row.original.tour_number})` : '' }}
          </NuxtLink>
          <NuxtLink
            v-else
            :to="`/cabinet/tenders/sales/${row.original.id}`"
            class="text-primary hover:underline font-medium"
          >
            №{{ row.original.number }}{{ row.original.tour_number > 1 ? ` (тур ${row.original.tour_number})` : '' }}
          </NuxtLink>
        </template>
        <template #name-cell="{ row }">
          <NuxtLink
            v-if="viewType === 'purchase'"
            :to="`/cabinet/tenders/${row.original.id}`"
            class="text-primary hover:underline"
          >
            {{ row.original.name }}
          </NuxtLink>
          <NuxtLink
            v-else
            :to="`/cabinet/tenders/sales/${row.original.id}`"
            class="text-primary hover:underline"
          >
            {{ row.original.name }}
          </NuxtLink>
        </template>
      </UTable>
      <div
        v-else
        class="text-center text-gray-400 py-12"
      >
        {{ viewType === 'purchase' ? 'Немає тендерів на закупівлю. Створіть перший.' : 'Немає тендерів на продаж. Створіть перший.' }}
      </div>
    </div>

    <!-- Пагінація закріплена по нижньому краю -->
    <div
      v-if="totalCount > 0"
      class="flex-shrink-0 flex items-center justify-between gap-4 py-2 border-t border-gray-200"
    >
      <span class="text-sm text-gray-600">
        Показано {{ tableData.length }} з {{ totalCount }}
        {{ viewType === 'purchase' ? 'тендерів' : 'тендерів' }}
      </span>
      <UPagination
        v-model:page="currentPage"
        :total="totalCount"
        :items-per-page="TENDERS_PAGE_SIZE"
        :sibling-count="1"
        show-edges
      />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: { title: 'Тендери' },
});

const route = useRoute();
const viewType = computed(() => (route.query.view === 'sales' ? 'sales' : 'purchase'));

const TENDERS_PAGE_SIZE = 20;

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const tenders = ref<any[]>([]);
const currentPage = ref(1);

const tableColumns = [
  { accessorKey: 'number', header: 'Номер' },
  { accessorKey: 'name', header: 'Назва' },
  { accessorKey: 'stage_label', header: 'Етап' },
  { accessorKey: 'conduct_type_label', header: 'Тип проведення' },
  { accessorKey: 'created_at', header: 'Створено' },
];

const totalCount = computed(() => tenders.value.length);

const tableData = computed(() => {
  const list = tenders.value;
  const start = (currentPage.value - 1) * TENDERS_PAGE_SIZE;
  return list.slice(start, start + TENDERS_PAGE_SIZE);
});

const createUrl = computed(() => {
  const type = viewType.value === 'purchase' ? 'purchase' : 'sales';
  return `/cabinet/tenders/create/${type}`;
});

async function loadTenders() {
  const endpoint = viewType.value === 'sales' ? '/sales-tenders/' : '/procurement-tenders/';
  const { data } = await fetch(endpoint, { headers: getAuthHeaders() });
  tenders.value = Array.isArray(data) ? data : [];
}

onMounted(() => loadTenders());
watch(viewType, () => {
  currentPage.value = 1;
  loadTenders();
});
</script>
