<template>
  <div class="h-full min-h-0 flex flex-col overflow-hidden">
    <h2 class="text-2xl font-bold mb-4">Журнал участей</h2>

    <div class="flex-1 min-h-0 overflow-hidden flex gap-4 max-lg:flex-col">
      <div class="flex-1 min-h-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col">
        <div class="flex-1 min-h-0 overflow-auto p-3">
          <div v-if="pagedData.length > 0" class="min-w-max">
            <UTable
              :data="pagedData"
              :columns="tableColumns"
              class="w-full participation-journal-table"
            >
            <template #number-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click="openProposalPage(row.original)"
              >
                №{{ row.original.number }}{{ ` (тур ${row.original.tour_number || 1})` }}
              </button>
            </template>

            <template #name-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline text-left"
                @click="openProposalPage(row.original)"
              >
                {{ row.original.name }}
              </button>
            </template>

            <template #company-cell="{ row }">
              <div class="text-sm">
                <div>{{ row.original.company?.name || "-" }}</div>
                <div class="text-xs text-gray-500">
                  {{ row.original.company?.edrpou || "" }}
                </div>
              </div>
            </template>

            <template #created_at-cell="{ row }">
              {{ formatDate(row.original.created_at) }}
            </template>

            <template #start_at-cell="{ row }">
              {{ formatDateTime(row.original.start_at) }}
            </template>

            <template #end_at-cell="{ row }">
              {{ formatDateTime(row.original.end_at) }}
            </template>
            </UTable>
          </div>

          <div v-else class="text-center text-gray-400 py-12">
            Немає тендерів у журналі участей.
          </div>
        </div>

        <div
          class="flex-shrink-0 bg-white px-3 py-2 flex items-center justify-between gap-3"
        >
          <span class="text-sm text-gray-600">
            Показано {{ pagedData.length }} з {{ mergedList.length }}
          </span>

          <UPagination
            v-model:page="currentPage"
            :total="mergedList.length"
            :items-per-page="PAGE_SIZE"
            :sibling-count="1"
            show-edges
          />
        </div>
      </div>

      <aside
        class="w-[18rem] min-w-[240px] max-w-[380px] shrink-0 rounded-xl border border-gray-200 bg-white shadow-sm p-4 flex flex-col gap-4 overflow-hidden max-lg:w-full max-lg:min-w-0 max-lg:max-w-none"
      >
        <div class="w-full">
          <UButton
            type="button"
            size="sm"
            variant="outline"
            color="error"
            class="w-full"
            @click="clearFilters"
          >
            Очистити
          </UButton>
        </div>

        <UFormField label="Номер тендера">
          <UInput
            v-model="tenderNumberFilter"
            placeholder="Введіть номер"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Результат участі">
          <USelectMenu
            v-model="participationResultFilter"
            :items="participationResultOptions"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Журнал участей" },
});

const PAGE_SIZE = 20;
const currentPage = ref(1);
const tendersUC = useTendersUseCases();

const mergedList = ref<any[]>([]);
const tenderNumberFilter = ref("");
const participationResultFilter = ref<"all" | "participation" | "win">("all");
const participationResultOptions = [
  { value: "all", label: "Усі" },
  { value: "participation", label: "Участь" },
  { value: "win", label: "Перемога" },
];

let tenderNumberTimer: ReturnType<typeof setTimeout> | null = null;
let loadCounter = 0;

const tableColumns = [
  { accessorKey: "tender_type_label", header: "Тип" },
  { accessorKey: "number", header: "Номер" },
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "company", header: "Компанія" },
  { accessorKey: "stage_label", header: "Етап" },
  { accessorKey: "start_at", header: "Початок прийому пропозицій" },
  { accessorKey: "end_at", header: "Завершення прийому пропозицій" },
  { accessorKey: "created_at", header: "Створено" },
];

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return mergedList.value.slice(start, start + PAGE_SIZE);
});

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("uk-UA");
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("uk-UA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadAllByType(isSales: boolean, loadId: number) {
  const out: any[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const { data } = await tendersUC.getTendersForParticipation(
      isSales,
      "journal",
      {
        page,
        submittedOnly: true,
        tenderNumber: tenderNumberFilter.value,
        participationResult:
          participationResultFilter.value === "all"
            ? undefined
            : participationResultFilter.value,
      },
    );
    const payload = (data as any) || {};
    const list = Array.isArray(payload.results) ? payload.results : [];
    totalPages = Number(payload.total_pages || 1);

    if (loadId !== loadCounter) {
      return [];
    }

    out.push(
      ...list.map((item: any) => ({
        ...item,
        tender_type: isSales ? "sales" : "purchase",
        tender_type_label: isSales ? "Продаж" : "Закупівля",
      })),
    );
    page += 1;
  }

  return out;
}

async function loadJournal() {
  const loadId = ++loadCounter;

  const [sales, purchase] = await Promise.all([
    loadAllByType(true, loadId),
    loadAllByType(false, loadId),
  ]);

  if (loadId !== loadCounter) {
    return;
  }

  mergedList.value = [...sales, ...purchase].sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
    return bTime - aTime;
  });
  currentPage.value = 1;
}

function clearFilters() {
  tenderNumberFilter.value = "";
  participationResultFilter.value = "all";
  currentPage.value = 1;
}

function openProposalPage(row: any) {
  const tenderId = Number(row?.id);
  if (!tenderId) return;
  if (row?.tender_type === "sales") {
    navigateTo(`/cabinet/tenders/sales/proposals/${tenderId}`);
    return;
  }
  navigateTo(`/cabinet/tenders/proposals/${tenderId}`);
}

function normalizeParticipationResultValue(
  raw: unknown,
): "all" | "participation" | "win" {
  if (raw === "participation" || raw === "win" || raw === "all") {
    return raw;
  }
  if (raw && typeof raw === "object") {
    const nestedValue = (raw as { value?: unknown }).value;
    if (
      nestedValue === "participation" ||
      nestedValue === "win" ||
      nestedValue === "all"
    ) {
      return nestedValue;
    }
  }
  return "all";
}

onMounted(() => {
  loadJournal();
});

watch(participationResultFilter as any, (nextValue: unknown) => {
  const normalizedValue = normalizeParticipationResultValue(nextValue);
  if (participationResultFilter.value !== normalizedValue) {
    participationResultFilter.value = normalizedValue;
    return;
  }
  loadJournal();
});

watch(tenderNumberFilter, () => {
  if (tenderNumberTimer) {
    clearTimeout(tenderNumberTimer);
  }

  tenderNumberTimer = setTimeout(() => {
    loadJournal();
  }, 350);
});

onBeforeUnmount(() => {
  if (tenderNumberTimer) {
    clearTimeout(tenderNumberTimer);
  }
});
</script>

<style scoped>
.participation-journal-table :deep(thead th) {
  position: sticky;
  top: 0;
  z-index: 5;
  background: white;
}

.participation-journal-table :deep(table) {
  min-width: max-content;
}

.participation-journal-table :deep(th),
.participation-journal-table :deep(td) {
  white-space: nowrap;
}
</style>
