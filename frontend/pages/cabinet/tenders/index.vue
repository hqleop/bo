<template>
  <div class="h-full min-h-0 flex flex-col overflow-hidden">
    <div class="flex-shrink-0 flex justify-between items-center mb-4 gap-3 flex-wrap">
      <h2 class="text-2xl font-bold">
        {{ viewType === "purchase" ? "Журнал закупівель" : "Журнал продажів" }}
      </h2>
      <div class="flex items-center gap-2 flex-wrap justify-end">
        <span v-if="selectedTenderIds.length" class="text-sm text-gray-600">
          {{ `Обрано: ${selectedTenderIds.length}` }}
        </span>
        <UButton
          icon="i-heroicons-trash"
          type="button"
          size="sm"
          color="error"
          variant="outline"
          :disabled="deletableSelectedTenderIds.length === 0 || deleteInProgress"
          :loading="deleteInProgress"
          @click="deleteSelectedTenders"
        >
          Видалити тендери
        </UButton>
        <UButton
          icon="i-heroicons-document-duplicate"
          type="button"
          size="sm"
          variant="outline"
          :disabled="selectedTenderIds.length === 0 || copyInProgress"
          :loading="copyInProgress"
          @click="copySelectedTenders"
        >
          {{ selectedTenderIds.length > 1 ? "Копіювати тендери" : "Копіювати тендер" }}
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          type="button"
          @click="navigateTo(createUrl)"
        >
          Створити процедуру
        </UButton>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-hidden flex gap-4 max-lg:flex-col">
      <div
        class="flex-1 min-h-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col"
      >
        <div class="flex-1 min-h-0 overflow-auto p-3">
          <div v-if="tableData.length > 0" class="min-w-max">
            <UTable
              :data="tableData"
              :columns="tableColumns"
              :meta="tableMeta"
              class="w-full tenders-journal-table"
            >
              <template #select-header>
                <UCheckbox
                  :model-value="isAllOnPageSelected"
                  :indeterminate="isSomeOnPageSelected && !isAllOnPageSelected"
                  aria-label="Обрати всі тендери на сторінці"
                  @update:model-value="toggleSelectAllOnPage"
                />
              </template>

              <template #select-cell="{ row }">
                <UCheckbox
                  :model-value="selectedTenderIds.includes(row.original.id)"
                  aria-label="Обрати тендер"
                  @update:model-value="toggleSelectTender(row.original.id)"
                  @click.stop
                />
              </template>

              <template #number-cell="{ row }">
                <NuxtLink
                  :to="
                    viewType === 'purchase'
                      ? `/cabinet/tenders/${row.original.id}`
                      : `/cabinet/tenders/sales/${row.original.id}`
                  "
                  class="text-primary hover:underline font-medium"
                >
                  №{{ row.original.number
                  }}{{ ` (тур ${row.original.tour_number || 1})` }}
                </NuxtLink>
              </template>

              <template #name-cell="{ row }">
                <NuxtLink
                  :to="
                    viewType === 'purchase'
                      ? `/cabinet/tenders/${row.original.id}`
                      : `/cabinet/tenders/sales/${row.original.id}`
                  "
                  class="text-primary hover:underline"
                >
                  {{ row.original.name }}
                </NuxtLink>
              </template>

              <template #created_at-cell="{ row }">
                {{ formatDateTime(row.original.created_at) }}
              </template>

              <template #decision_label-cell="{ row }">
                {{ row.original.decision_label || "-" }}
              </template>

              <template #total_amount-cell="{ row }">
                {{ formatAmount(row.original.total_amount) }}
              </template>

              <template #economy_amount-cell="{ row }">
                {{ formatAmount(row.original.economy_amount) }}
              </template>

              <template #profit_amount-cell="{ row }">
                {{ formatAmount(row.original.profit_amount) }}
              </template>
            </UTable>
          </div>

          <div v-else class="text-center text-gray-400 py-12">
            {{
              viewType === "purchase"
                ? "Немає тендерів на закупівлю за обраними умовами."
                : "Немає тендерів на продаж за обраними умовами."
            }}
          </div>
        </div>

        <div
          class="flex-shrink-0 bg-white px-3 py-2 flex items-center justify-between gap-3"
        >
          <span class="text-sm text-gray-600">
            Показано {{ tableData.length }} з {{ totalCount }}
          </span>

          <UPagination
            v-model:page="currentPage"
            :total="totalCount"
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
            Очистити фільтри
          </UButton>
        </div>

        <UFormField
          label="Пошук"
          help="Для виконання пошуку введіть номер або назву тендера"
        >
          <UInput
            v-model="searchInput"
            placeholder="Номер або назва тендера"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Статус">
          <USelectMenu
            v-model="statusFilter"
            :items="statusOptions"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Автор">
          <USelectMenu
            v-model="authorIdFilter"
            :items="authorOptions"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>

        <ContentSearch
          label="Філіал"
          placeholder="Оберіть філіали"
          search-placeholder="Пошук філіалу"
          :tree="branchesTree"
          :selected-ids="branchIdsFilter"
          :search-term="branchSearch"
          @toggle="toggleBranchFilter"
          @update:search-term="branchSearch = $event"
        />

        <ContentSearch
          label="Підрозділ"
          placeholder="Оберіть підрозділ"
          search-placeholder="Пошук підрозділу"
          :disabled="branchIdsFilter.length === 0"
          :tree="departmentTree"
          :selected-ids="departmentIdsFilter"
          :search-term="departmentSearch"
          @toggle="toggleDepartmentFilter"
          @update:search-term="departmentSearch = $event"
        />

        <ContentSearch
          label="Стаття бюджету"
          placeholder="Оберіть статті бюджету"
          search-placeholder="Пошук статті бюджету"
          :tree="expensesTree"
          :selected-ids="expenseIdsFilter"
          :search-term="expenseSearch"
          @toggle="toggleExpenseFilter"
          @update:search-term="expenseSearch = $event"
        />

        <UFormField label="Тип процедури">
          <USelectMenu
            v-model="conductTypeFilter"
            :items="conductTypeOptions"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>

        <UFormField
          v-if="statusFilter === 'active' || statusFilter === 'all'"
          label="Етап процедури"
        >
          <USelectMenu
            v-model="stageFilter"
            :items="stageOptions"
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
import { TENDER_STAGE_ITEMS } from "~/domains/tenders/tenders.constants";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Тендери" },
});

type TenderViewType = "purchase" | "sales";
type TenderStatusFilter = "active" | "completed" | "all";
type ConductTypeFilter = "all" | "registration" | "rfx" | "online_auction";

const PAGE_SIZE = 20;

const route = useRoute();
const viewType = computed<TenderViewType>(() =>
  route.query.view === "sales" ? "sales" : "purchase",
);

const tendersUC = useTendersUseCases();
const usersUC = useUsersUseCases();
const toast = useToast();

const tenders = ref<any[]>([]);
const totalCount = ref(0);
const currentPage = ref(1);
const selectedTenderIds = ref<number[]>([]);
const deleteInProgress = ref(false);
const copyInProgress = ref(false);

const searchInput = ref("");
const searchFilter = ref("");
const statusFilter = ref<TenderStatusFilter>("active");
const authorIdFilter = ref<number | null>(null);
const branchIdsFilter = ref<number[]>([]);
const departmentIdsFilter = ref<number[]>([]);
const expenseIdsFilter = ref<number[]>([]);
const conductTypeFilter = ref<ConductTypeFilter>("all");
const stageFilter = ref("all");

const branchSearch = ref("");
const departmentSearch = ref("");
const expenseSearch = ref("");

const branchesTree = ref<any[]>([]);
const expensesTree = ref<any[]>([]);
const departmentsByBranch = ref<Record<number, any[]>>({});
const authorOptions = ref<Array<{ value: number | null; label: string }>>([
  { value: null, label: "Усі" },
]);

let searchTimer: ReturnType<typeof setTimeout> | null = null;
let loadCounter = 0;

const statusOptions = [
  { value: "active", label: "Активні" },
  { value: "completed", label: "Завершені" },
  { value: "all", label: "Усі" },
] as const;

const conductTypeOptions = [
  { value: "all", label: "Усі" },
  { value: "registration", label: "Реєстрація" },
  { value: "rfx", label: "Збір пропозицій (RFx)" },
  { value: "online_auction", label: "Онлайн торги" },
];

const activeStageValues = new Set([
  "preparation",
  "acceptance",
  "decision",
  "approval",
]);

const allStageOptions = TENDER_STAGE_ITEMS.map((item) => ({
  value: item.value,
  label: item.title,
}));

const stageOptions = computed(() => {
  const source =
    statusFilter.value === "active"
      ? allStageOptions.filter((option) => activeStageValues.has(option.value))
      : allStageOptions;
  return [{ value: "all", label: "Усі" }, ...source];
});

function normalizeSelectStringValue(raw: unknown, fallback = "all") {
  if (typeof raw === "string" && raw.trim().length > 0) {
    return raw;
  }
  if (raw && typeof raw === "object") {
    const nestedValue = (raw as { value?: unknown }).value;
    if (typeof nestedValue === "string" && nestedValue.trim().length > 0) {
      return nestedValue;
    }
  }
  return fallback;
}

const tableColumns = computed(() => {
  const metricColumn =
    viewType.value === "purchase"
      ? { accessorKey: "economy_amount", header: "Економія" }
      : { accessorKey: "profit_amount", header: "Вигода" };
  const totalAmountColumn =
    viewType.value === "purchase"
      ? { accessorKey: "total_amount", header: "Сума закупівлі" }
      : { accessorKey: "total_amount", header: "Сума продажу" };

  return [
    { id: "select", header: "" },
    { accessorKey: "number", header: "Номер тендера" },
    { accessorKey: "name", header: "Назва" },
    { accessorKey: "created_by_display", header: "Автор" },
    { accessorKey: "stage_label", header: "Етап" },
    { accessorKey: "conduct_type_label", header: "Тип процедури" },
    { accessorKey: "branch_name", header: "Філіал" },
    { accessorKey: "department_name", header: "Підрозділ" },
    { accessorKey: "expense_article_name", header: "Стаття бюджету" },
    { accessorKey: "category_name", header: "Категорія" },
    { accessorKey: "cpv_label", header: "Категорія CPV" },
    { accessorKey: "decision_label", header: "Прийняте рішення" },
    totalAmountColumn,
    metricColumn,
  ];
});

const tableData = computed(() => tenders.value);

const deletableSelectedTenderIds = computed(() => {
  const selected = new Set(selectedTenderIds.value);
  return tableData.value
    .filter((row: any) => selected.has(Number(row?.id || 0)) && Boolean(row?.can_delete))
    .map((row: any) => Number(row.id))
    .filter((id: number) => id > 0);
});

const ineligibleSelectedDeleteCount = computed(() => {
  const selected = new Set(selectedTenderIds.value);
  let count = 0;
  for (const row of tableData.value) {
    const rowId = Number((row as any)?.id || 0);
    if (!rowId || !selected.has(rowId)) continue;
    if (!(row as any)?.can_delete) count += 1;
  }
  return count;
});

const isAllOnPageSelected = computed(() => {
  if (!tableData.value.length) return false;
  const ids = new Set(selectedTenderIds.value);
  return tableData.value.every((row: any) => ids.has(Number(row?.id || 0)));
});

const isSomeOnPageSelected = computed(() => {
  const ids = new Set(selectedTenderIds.value);
  return tableData.value.some((row: any) => ids.has(Number(row?.id || 0)));
});

function toggleSelectTender(tenderId: number) {
  const normalizedId = Number(tenderId || 0);
  if (!normalizedId) return;
  const set = new Set(selectedTenderIds.value);
  if (set.has(normalizedId)) {
    set.delete(normalizedId);
  } else {
    set.add(normalizedId);
  }
  selectedTenderIds.value = [...set];
}

function toggleSelectAllOnPage() {
  const pageIds = tableData.value
    .map((row: any) => Number(row?.id || 0))
    .filter((id: number) => id > 0);
  if (!pageIds.length) return;
  const selected = new Set(selectedTenderIds.value);
  const allSelected = pageIds.every((id) => selected.has(id));
  if (allSelected) {
    pageIds.forEach((id) => selected.delete(id));
  } else {
    pageIds.forEach((id) => selected.add(id));
  }
  selectedTenderIds.value = [...selected];
}

const tableMeta = computed(() => ({
  class: {
    tr: (row: any) =>
      selectedTenderIds.value.includes(Number(row?.original?.id || 0))
        ? "bg-blue-50"
        : "",
  },
}));

const createUrl = computed(() => {
  const type = viewType.value === "purchase" ? "purchase" : "sales";
  return `/cabinet/tenders/create/${type}`;
});

const departmentTree = computed(() => {
  if (!branchIdsFilter.value.length) return [];
  const out: any[] = [];
  for (const branchId of branchIdsFilter.value) {
    const branchDepartments = departmentsByBranch.value[branchId] || [];
    out.push(...branchDepartments);
  }
  return out;
});

function formatDateTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("uk-UA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatAmount(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return String(value);
  return numericValue.toLocaleString("uk-UA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function flattenTree(items: any[]): any[] {
  const out: any[] = [];
  const walk = (nodes: any[]) => {
    for (const node of nodes || []) {
      out.push(node);
      if (Array.isArray(node.children) && node.children.length) {
        walk(node.children);
      }
    }
  };
  walk(items || []);
  return out;
}

function formatAuthorLabel(user: any) {
  const parts = [user?.last_name, user?.first_name, user?.middle_name].filter(
    Boolean,
  );
  const fullName = parts.join(" ").trim();
  return fullName || String(user?.email || `ID ${user?.id || ""}`).trim();
}

async function loadAuthors() {
  const { data } = await usersUC.getMemberships();
  const list = Array.isArray(data) ? data : [];
  const byId = new Map<number, string>();

  for (const membership of list) {
    if ((membership as any)?.status !== "approved") continue;
    const user = (membership as any)?.user;
    const userId = Number(user?.id || 0);
    if (!userId || byId.has(userId)) continue;
    byId.set(userId, formatAuthorLabel(user));
  }

  const options = [...byId.entries()]
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, "uk-UA"));

  authorOptions.value = [{ value: null, label: "Усі" }, ...options];
}

async function ensureDepartmentsLoaded(branchId: number) {
  if (!branchId || departmentsByBranch.value[branchId]) return;
  const { data } = await tendersUC.getDepartments(branchId);
  departmentsByBranch.value = {
    ...departmentsByBranch.value,
    [branchId]: Array.isArray(data) ? data : [],
  };
}

function toggleBranchFilter(id: number) {
  const idx = branchIdsFilter.value.indexOf(id);
  if (idx > -1) {
    branchIdsFilter.value.splice(idx, 1);
    const branchDepartmentIds = new Set(
      flattenTree(departmentsByBranch.value[id] || []).map((item: any) =>
        Number(item?.id || 0),
      ),
    );
    departmentIdsFilter.value = departmentIdsFilter.value.filter(
      (departmentId) => !branchDepartmentIds.has(departmentId),
    );
    return;
  }

  branchIdsFilter.value.push(id);
  ensureDepartmentsLoaded(id);
}

function toggleDepartmentFilter(id: number) {
  const idx = departmentIdsFilter.value.indexOf(id);
  if (idx > -1) {
    departmentIdsFilter.value.splice(idx, 1);
    return;
  }
  departmentIdsFilter.value.push(id);
}

function toggleExpenseFilter(id: number) {
  const idx = expenseIdsFilter.value.indexOf(id);
  if (idx > -1) {
    expenseIdsFilter.value.splice(idx, 1);
    return;
  }
  expenseIdsFilter.value.push(id);
}

async function loadFilterTrees() {
  const [{ data: branchesData }, { data: expensesData }] = await Promise.all([
    tendersUC.getBranches(),
    tendersUC.getExpenses(),
  ]);
  branchesTree.value = Array.isArray(branchesData) ? branchesData : [];
  expensesTree.value = Array.isArray(expensesData) ? expensesData : [];
}

async function loadTenders() {
  const loadId = ++loadCounter;
  const { data } = await tendersUC.getTenderJournalList(
    viewType.value === "sales",
    {
      page: currentPage.value,
      pageSize: PAGE_SIZE,
      search: searchFilter.value,
      status: statusFilter.value,
      authorId: authorIdFilter.value,
      branchIds: branchIdsFilter.value,
      departmentIds: departmentIdsFilter.value,
      expenseIds: expenseIdsFilter.value,
      conductType: conductTypeFilter.value,
      stage: stageFilter.value === "all" ? undefined : stageFilter.value,
    },
  );

  if (loadId !== loadCounter) return;

  const payload = (data as any) || {};
  tenders.value = Array.isArray(payload.results) ? payload.results : [];
  const count = Number(payload.count);
  totalCount.value = Number.isFinite(count) && count >= 0 ? count : 0;
  const totalPages = Number(payload.total_pages || 0);
  if (totalPages > 0 && currentPage.value > totalPages) {
    currentPage.value = totalPages;
  }
  const pageIds = new Set(
    tenders.value
      .map((row: any) => Number(row?.id || 0))
      .filter((id: number) => id > 0),
  );
  selectedTenderIds.value = selectedTenderIds.value.filter((id) =>
    pageIds.has(id),
  );
}

async function deleteSelectedTenders() {
  if (deleteInProgress.value) return;
  const ids = deletableSelectedTenderIds.value;
  if (!ids.length) {
    toast.add({
      title: "Немає доступних для видалення тендерів серед вибраних.",
      color: "warning",
    });
    return;
  }
  if (ineligibleSelectedDeleteCount.value > 0) {
    toast.add({
      title: "Частина вибраних тендерів недоступна для видалення і буде пропущена.",
      color: "warning",
    });
  }

  deleteInProgress.value = true;
  try {
    const { data, error } = await tendersUC.bulkDeleteTenders(
      viewType.value === "sales",
      ids,
    );
    if (error) {
      toast.add({ title: error, color: "error" });
      return;
    }
    const payload = (data as any) || {};
    const deletedIds = Array.isArray(payload.deleted_ids)
      ? payload.deleted_ids
          .map((id: unknown) => Number(id))
          .filter((id: number) => Number.isInteger(id) && id > 0)
      : [];
    if (!deletedIds.length) {
      toast.add({
        title: "Не вдалося видалити вибрані тендери.",
        color: "warning",
      });
      return;
    }
    const selected = new Set(selectedTenderIds.value);
    deletedIds.forEach((id: number) => selected.delete(id));
    selectedTenderIds.value = [...selected];
    toast.add({
      title: `Видалено тендерів: ${deletedIds.length}`,
      color: "success",
    });
    await loadTenders();
  } finally {
    deleteInProgress.value = false;
  }
}

async function copySelectedTenders() {
  if (copyInProgress.value) return;
  const ids = selectedTenderIds.value.filter((id) => Number(id) > 0);
  if (!ids.length) {
    toast.add({ title: "Спочатку оберіть тендери для копіювання.", color: "warning" });
    return;
  }

  copyInProgress.value = true;
  try {
    const { data, error } = await tendersUC.bulkCopyTenders(
      viewType.value === "sales",
      ids,
    );
    if (error) {
      toast.add({ title: error, color: "error" });
      return;
    }
    const payload = (data as any) || {};
    const copiedCount = Number(payload.copied_count || 0);
    if (copiedCount <= 0) {
      toast.add({
        title: "Не вдалося створити копію тендера.",
        color: "warning",
      });
      return;
    }
    toast.add({
      title: `Скопійовано тендерів: ${copiedCount}`,
      color: "success",
    });
    selectedTenderIds.value = [];
    if (currentPage.value !== 1) {
      currentPage.value = 1;
    } else {
      await loadTenders();
    }
  } finally {
    copyInProgress.value = false;
  }
}

function clearFilters() {
  searchInput.value = "";
  searchFilter.value = "";
  statusFilter.value = "active";
  authorIdFilter.value = null;
  branchIdsFilter.value = [];
  departmentIdsFilter.value = [];
  expenseIdsFilter.value = [];
  conductTypeFilter.value = "all";
  stageFilter.value = "all";
  branchSearch.value = "";
  departmentSearch.value = "";
  expenseSearch.value = "";
  currentPage.value = 1;
  selectedTenderIds.value = [];
}

onMounted(async () => {
  await Promise.all([loadFilterTrees(), loadAuthors()]);
});

watch(searchInput, () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchFilter.value = searchInput.value.trim();
  }, 350);
});

watch(
  () => [...branchIdsFilter.value],
  async (branchIds) => {
    if (!branchIds.length) {
      departmentIdsFilter.value = [];
      return;
    }

    await Promise.all(
      branchIds.map((branchId) => ensureDepartmentsLoaded(branchId)),
    );

    const allowedDepartmentIds = new Set<number>();
    for (const branchId of branchIds) {
      const departmentIds = flattenTree(
        departmentsByBranch.value[branchId] || [],
      )
        .map((item: any) => Number(item?.id || 0))
        .filter((value) => value > 0);
      for (const departmentId of departmentIds) {
        allowedDepartmentIds.add(departmentId);
      }
    }
    departmentIdsFilter.value = departmentIdsFilter.value.filter((id) =>
      allowedDepartmentIds.has(id),
    );
  },
);

watch(statusFilter, (nextStatus) => {
  if (nextStatus === "completed") {
    stageFilter.value = "all";
    return;
  }
  if (
    nextStatus === "active" &&
    stageFilter.value !== "all" &&
    !activeStageValues.has(stageFilter.value)
  ) {
    stageFilter.value = "all";
  }
});

watch(stageFilter as any, (nextValue: unknown) => {
  const normalizedValue = normalizeSelectStringValue(nextValue, "all");
  if (stageFilter.value !== normalizedValue) {
    stageFilter.value = normalizedValue;
  }
});

const filterState = computed(() => [
  viewType.value,
  searchFilter.value,
  statusFilter.value,
  authorIdFilter.value ?? 0,
  branchIdsFilter.value.join(","),
  departmentIdsFilter.value.join(","),
  expenseIdsFilter.value.join(","),
  conductTypeFilter.value,
  stageFilter.value,
]);

watch(
  filterState,
  () => {
    selectedTenderIds.value = [];
    if (currentPage.value !== 1) {
      currentPage.value = 1;
      return;
    }
    loadTenders();
  },
  { immediate: true },
);

watch(currentPage, () => {
  loadTenders();
});

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<style scoped>
.tenders-journal-table :deep(thead th) {
  position: sticky;
  top: 0;
  z-index: 5;
  background: white;
}

.tenders-journal-table :deep(table) {
  min-width: max-content;
}

.tenders-journal-table :deep(th),
.tenders-journal-table :deep(td) {
  white-space: nowrap;
}
</style>
