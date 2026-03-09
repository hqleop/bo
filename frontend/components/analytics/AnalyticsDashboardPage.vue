<template>
  <div class="h-full min-h-0 flex flex-col overflow-hidden">
    <div class="flex-shrink-0 mb-4 space-y-3">
      <h2 class="text-2xl font-bold">{{ pageTitle }}</h2>

      <div class="inline-flex rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
        <UButton
          v-for="tab in tabs"
          :key="tab.to"
          type="button"
          size="sm"
          :variant="isTabActive(tab.to) ? 'solid' : 'ghost'"
          class="px-3"
          @click="navigateTo(tab.to)"
        >
          {{ tab.label }}
        </UButton>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-hidden flex gap-4 max-lg:flex-col">
      <div
        class="flex-1 min-h-0 overflow-auto rounded-xl border border-gray-200 bg-white shadow-sm p-4 space-y-4"
      >
        <div
          v-if="loadError"
          class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ loadError }}
        </div>

        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="item in kpis"
            :key="item.key"
            class="rounded-xl border border-gray-200 bg-gradient-to-br from-white to-gray-50 px-4 py-3"
          >
            <div class="text-xs font-medium uppercase tracking-wide text-gray-500">
              {{ item.label }}
            </div>
            <div class="mt-1 text-2xl font-semibold text-gray-900">
              {{ formatNumber(item.value) }}
            </div>
          </div>
        </div>

        <div class="grid gap-4 xl:grid-cols-2">
          <div class="rounded-xl border border-gray-200 p-3">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">
              {{ isParticipationMode ? "Динаміка участей" : "Динаміка тендерів" }}
            </h3>
            <div v-if="monthlyChartData.length === 0" class="h-[320px] flex items-center justify-center text-sm text-gray-500">
              Дані відсутні
            </div>
            <LineChart
              v-else
              :data="monthlyChartData"
              :categories="monthlyChartCategories"
              :height="320"
              :xFormatter="monthlyXFormatter"
              :xGridLine="true"
              :yGridLine="true"
              :hideLegend="false"
              :tooltip="{ followCursor: true }"
            />
          </div>

          <div class="rounded-xl border border-gray-200 p-3">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">
              Розподіл по етапах
            </h3>
            <div v-if="stageDistribution.length === 0" class="h-[320px] flex items-center justify-center text-sm text-gray-500">
              Дані відсутні
            </div>
            <DonutChart
              v-else
              :data="stageDonutData"
              :categories="stageDonutCategories"
              :radius="110"
              :height="320"
              :hideLegend="false"
              legend-position="bottom"
            />
          </div>

          <div class="rounded-xl border border-gray-200 p-3">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">
              Розподіл по типу
            </h3>
            <div v-if="typeBarData.length === 0" class="h-[280px] flex items-center justify-center text-sm text-gray-500">
              Дані відсутні
            </div>
            <BarChart
              v-else
              :data="typeBarData"
              :categories="singleValueCategory"
              :xAxis="'label'"
              :yAxis="['value']"
              :height="280"
              :xGridLine="false"
              :yGridLine="true"
            />
          </div>

          <div class="rounded-xl border border-gray-200 p-3">
            <h3 class="text-sm font-semibold text-gray-700 mb-2">
              Результат
            </h3>
            <div v-if="resultBarData.length === 0" class="h-[280px] flex items-center justify-center text-sm text-gray-500">
              Дані відсутні
            </div>
            <BarChart
              v-else
              :data="resultBarData"
              :categories="singleValueCategory"
              :xAxis="'label'"
              :yAxis="['value']"
              :height="280"
              :xGridLine="false"
              :yGridLine="true"
            />
          </div>

          <div
            v-if="topBarData.length > 0"
            class="rounded-xl border border-gray-200 p-3 xl:col-span-2"
          >
            <h3 class="text-sm font-semibold text-gray-700 mb-2">
              {{ mode === "summary-tenders" ? "Топ користувачів" : "Топ організаторів" }}
            </h3>
            <BarChart
              :data="topBarData"
              :categories="singleValueCategory"
              :xAxis="'label'"
              :yAxis="['value']"
              :height="320"
              :xGridLine="false"
              :yGridLine="true"
            />
          </div>
        </div>
      </div>

      <aside
        class="w-[18rem] min-w-[240px] max-w-[380px] shrink-0 rounded-xl border border-gray-200 bg-white shadow-sm p-4 flex flex-col gap-4 overflow-hidden max-lg:w-full max-lg:min-w-0 max-lg:max-w-none"
      >
        <UButton
          type="button"
          size="sm"
          variant="outline"
          color="error"
          class="w-full"
          :loading="loading"
          @click="clearFilters"
        >
          Очистити фільтри
        </UButton>

        <UFormField label="Період по даті">
          <USelectMenu
            v-model="dateFieldFilter"
            :items="dateFieldOptions"
            value-key="value"
            label-key="label"
            class="w-full"
          />
        </UFormField>

        <UFormField label="З дати">
          <UInput v-model="dateFromFilter" type="date" class="w-full" />
        </UFormField>

        <UFormField label="По дату">
          <UInput v-model="dateToFilter" type="date" class="w-full" />
        </UFormField>

        <UFormField label="Тип тендера">
          <USelectMenu
            v-model="tenderTypeFilter"
            :items="tenderTypeOptions"
            value-key="value"
            label-key="label"
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
          placeholder="Оберіть підрозділи"
          search-placeholder="Пошук підрозділу"
          :disabled="branchIdsFilter.length === 0"
          :tree="departmentTree"
          :selected-ids="departmentIdsFilter"
          :search-term="departmentSearch"
          @toggle="toggleDepartmentFilter"
          @update:search-term="departmentSearch = $event"
        />

        <ContentSearch
          label="Категорія"
          placeholder="Оберіть категорії"
          search-placeholder="Пошук категорії"
          :tree="categoriesTree"
          :selected-ids="categoryIdsFilter"
          :search-term="categorySearch"
          @toggle="toggleCategoryFilter"
          @update:search-term="categorySearch = $event"
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

        <ContentSearch
          v-if="isSummaryMode"
          label="Користувач"
          placeholder="Оберіть користувачів"
          search-placeholder="Пошук користувача"
          :tree="usersTree"
          :selected-ids="userIdsFilter"
          :search-term="userSearch"
          @toggle="toggleUserFilter"
          @update:search-term="userSearch = $event"
        />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  AnalyticsDashboardPayload,
  AnalyticsMode,
} from "~/domains/analytics/analytics.types";
import { useAnalyticsUseCases } from "~/domains/analytics/analytics.useCases";

type TabLink = { label: string; to: string };

const props = defineProps<{
  mode: AnalyticsMode;
  pageTitle: string;
  tabs: TabLink[];
}>();

const route = useRoute();
const analyticsUC = useAnalyticsUseCases();
const tendersUC = useTendersUseCases();
const usersUC = useUsersUseCases();

const dashboard = ref<AnalyticsDashboardPayload | null>(null);
const loading = ref(false);
const loadError = ref("");
const initialized = ref(false);

const companyId = ref<number | null>(null);
const dateFieldFilter = ref<any>("start_at");
const dateFromFilter = ref("");
const dateToFilter = ref("");
const tenderTypeFilter = ref<any>("all");
const statusFilter = ref<any>("active");

const branchIdsFilter = ref<number[]>([]);
const departmentIdsFilter = ref<number[]>([]);
const categoryIdsFilter = ref<number[]>([]);
const expenseIdsFilter = ref<number[]>([]);
const userIdsFilter = ref<number[]>([]);

const branchSearch = ref("");
const departmentSearch = ref("");
const categorySearch = ref("");
const expenseSearch = ref("");
const userSearch = ref("");

const branchesTree = ref<any[]>([]);
const categoriesTree = ref<any[]>([]);
const expensesTree = ref<any[]>([]);
const usersTree = ref<any[]>([]);
const departmentsByBranch = ref<Record<number, any[]>>({});

let loadCounter = 0;

const dateFieldOptions = [
  { value: "start_at", label: "По даті початку" },
  { value: "end_at", label: "По даті завершення" },
];

const tenderTypeOptions = [
  { value: "all", label: "Усі" },
  { value: "purchase", label: "Закупівля" },
  { value: "sales", label: "Продаж" },
];

const statusOptions = [
  { value: "active", label: "Активні" },
  { value: "completed", label: "Завершені" },
  { value: "all", label: "Усі" },
];

const singleValueCategory = {
  value: { name: "Кількість", color: "#0ea5e9" },
};

const chartPalette = [
  "#2563eb",
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#a855f7",
  "#14b8a6",
  "#f97316",
];

const isSummaryMode = computed(() => props.mode.startsWith("summary-"));
const isParticipationMode = computed(
  () => props.mode.includes("participant") || props.mode.includes("participation"),
);

const departmentTree = computed(() => {
  if (!branchIdsFilter.value.length) return [];
  const out: any[] = [];
  for (const branchId of branchIdsFilter.value) {
    out.push(...(departmentsByBranch.value[branchId] || []));
  }
  return out;
});

const kpis = computed(() => dashboard.value?.kpis || []);

const monthlyChartData = computed(() =>
  (dashboard.value?.monthly_series || []).map((row) => ({
    month: String(row.month || ""),
    month_label: formatMonthLabel(String(row.month || "")),
    tenders_total: Number(row.tenders_total || 0),
    tenders_completed: Number(row.tenders_completed || 0),
    submitted_proposals: Number(row.submitted_proposals || 0),
    participations_total: Number(row.participations_total || 0),
    wins_total: Number(row.wins_total || 0),
  })),
);

const monthlyChartCategories = computed(() =>
  isParticipationMode.value
    ? {
        participations_total: { name: "Участі", color: "#2563eb" },
        wins_total: { name: "Перемоги", color: "#10b981" },
      }
    : {
        tenders_total: { name: "Усього", color: "#2563eb" },
        tenders_completed: { name: "Завершені", color: "#10b981" },
        submitted_proposals: { name: "Пропозиції", color: "#f59e0b" },
      },
);

const stageDistribution = computed(
  () => dashboard.value?.distributions?.stage || [],
);

const stageDonutData = computed(() =>
  stageDistribution.value.map((item) => Number(item.value || 0)),
);

const stageDonutCategories = computed(() => {
  const out: Record<string, { name: string; color: string }> = {};
  stageDistribution.value.forEach((item, index) => {
    out[item.key] = {
      name: item.label,
      color: chartPalette[index % chartPalette.length],
    };
  });
  return out;
});

const typeBarData = computed(() =>
  (dashboard.value?.distributions?.tender_type || []).map((item) => ({
    label: item.label,
    value: Number(item.value || 0),
  })),
);

const resultBarData = computed(() =>
  (dashboard.value?.distributions?.result || []).map((item) => ({
    label: item.label,
    value: Number(item.value || 0),
  })),
);

const topBarData = computed(() => {
  if (props.mode === "summary-tenders") {
    return (dashboard.value?.top_users || []).map((item) => ({
      label: String(item.label || ""),
      value: Number(item.value || 0),
    }));
  }
  if (props.mode === "summary-participation") {
    return (dashboard.value?.top_companies || []).map((item) => ({
      label: String(item.label || ""),
      value: Number(item.value || 0),
    }));
  }
  return [];
});

function createEmptyPayload(mode: AnalyticsMode): AnalyticsDashboardPayload {
  return {
    mode,
    generated_at: "",
    kpis: [],
    monthly_series: [],
    distributions: {
      stage: [],
      tender_type: [],
      result: [],
    },
    top_users: [],
    top_companies: [],
  };
}

function isTabActive(to: string) {
  return route.path === to;
}

function normalizeSelectStringValue(raw: unknown, fallback: string) {
  if (typeof raw === "string" && raw.trim().length > 0) return raw;
  if (raw && typeof raw === "object") {
    const nested = (raw as { value?: unknown }).value;
    if (typeof nested === "string" && nested.trim().length > 0) return nested;
  }
  return fallback;
}

function formatMonthLabel(value: string) {
  const [year, month] = String(value || "").split("-");
  if (!year || !month) return value;
  return `${month}.${year}`;
}

function formatNumber(value: unknown) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return String(value ?? 0);
  const fractional = Math.abs(numericValue % 1) > 0;
  return numericValue.toLocaleString("uk-UA", {
    minimumFractionDigits: fractional ? 2 : 0,
    maximumFractionDigits: fractional ? 2 : 0,
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

function formatUserLabel(user: any) {
  const parts = [user?.last_name, user?.first_name, user?.middle_name].filter(Boolean);
  const fullName = parts.join(" ").trim();
  return fullName || String(user?.email || `ID ${user?.id || ""}`).trim();
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
  if (idx > -1) departmentIdsFilter.value.splice(idx, 1);
  else departmentIdsFilter.value.push(id);
}

function toggleCategoryFilter(id: number) {
  const idx = categoryIdsFilter.value.indexOf(id);
  if (idx > -1) categoryIdsFilter.value.splice(idx, 1);
  else categoryIdsFilter.value.push(id);
}

function toggleExpenseFilter(id: number) {
  const idx = expenseIdsFilter.value.indexOf(id);
  if (idx > -1) expenseIdsFilter.value.splice(idx, 1);
  else expenseIdsFilter.value.push(id);
}

function toggleUserFilter(id: number) {
  const idx = userIdsFilter.value.indexOf(id);
  if (idx > -1) userIdsFilter.value.splice(idx, 1);
  else userIdsFilter.value.push(id);
}

async function loadFilterOptions() {
  const mePayload = await usersUC.refreshMe();
  const approvedMemberships = (Array.isArray(mePayload?.memberships) ? mePayload?.memberships : []).filter(
    (membership: any) => membership?.status === "approved",
  );

  if (!companyId.value) {
    const firstCompanyId = Number(approvedMemberships[0]?.company?.id || 0);
    companyId.value = firstCompanyId > 0 ? firstCompanyId : null;
  }

  const [{ data: branchesData }, { data: categoriesData }, { data: expensesData }] =
    await Promise.all([
      tendersUC.getBranches(),
      tendersUC.getCategories(),
      tendersUC.getExpenses(),
    ]);

  branchesTree.value = Array.isArray(branchesData) ? branchesData : [];
  categoriesTree.value = Array.isArray(categoriesData) ? categoriesData : [];
  expensesTree.value = Array.isArray(expensesData) ? expensesData : [];

  if (isSummaryMode.value) {
    const { data } = await usersUC.getMemberships();
    const byId = new Map<number, { id: number; name: string }>();
    for (const membership of Array.isArray(data) ? data : []) {
      if ((membership as any)?.status !== "approved") continue;
      const user = (membership as any)?.user;
      const userId = Number(user?.id || 0);
      if (!userId || byId.has(userId)) continue;
      byId.set(userId, { id: userId, name: formatUserLabel(user) });
    }
    usersTree.value = Array.from(byId.values()).sort((a, b) =>
      a.name.localeCompare(b.name, "uk-UA"),
    );
  } else {
    usersTree.value = [];
    userIdsFilter.value = [];
  }
}

async function loadAnalytics() {
  if (!companyId.value) {
    dashboard.value = createEmptyPayload(props.mode);
    loadError.value = "";
    return;
  }

  const loadId = ++loadCounter;
  loading.value = true;
  loadError.value = "";

  const { data, error } = await analyticsUC.getAnalyticsDashboard(props.mode, {
    companyId: companyId.value,
    dateField: normalizeSelectStringValue(dateFieldFilter.value, "start_at") as
      | "start_at"
      | "end_at",
    dateFrom: dateFromFilter.value || undefined,
    dateTo: dateToFilter.value || undefined,
    tenderType: normalizeSelectStringValue(tenderTypeFilter.value, "all") as
      | "all"
      | "purchase"
      | "sales",
    status: normalizeSelectStringValue(statusFilter.value, "active") as
      | "all"
      | "active"
      | "completed",
    branchIds: branchIdsFilter.value,
    departmentIds: departmentIdsFilter.value,
    categoryIds: categoryIdsFilter.value,
    expenseIds: expenseIdsFilter.value,
    userIds: isSummaryMode.value ? userIdsFilter.value : [],
  });

  if (loadId !== loadCounter) return;

  if (error) {
    dashboard.value = createEmptyPayload(props.mode);
    loadError.value = error;
    loading.value = false;
    return;
  }

  dashboard.value = data || createEmptyPayload(props.mode);
  loading.value = false;
}

function clearFilters() {
  dateFieldFilter.value = "start_at";
  dateFromFilter.value = "";
  dateToFilter.value = "";
  tenderTypeFilter.value = "all";
  statusFilter.value = "active";
  branchIdsFilter.value = [];
  departmentIdsFilter.value = [];
  categoryIdsFilter.value = [];
  expenseIdsFilter.value = [];
  userIdsFilter.value = [];
  branchSearch.value = "";
  departmentSearch.value = "";
  categorySearch.value = "";
  expenseSearch.value = "";
  userSearch.value = "";
}

const monthlyXFormatter = (index: number) =>
  monthlyChartData.value[index]?.month_label || "";

watch(
  () => [...branchIdsFilter.value],
  async (branchIds) => {
    if (!branchIds.length) {
      departmentIdsFilter.value = [];
      return;
    }

    await Promise.all(branchIds.map((branchId) => ensureDepartmentsLoaded(branchId)));

    const allowedDepartmentIds = new Set<number>();
    for (const branchId of branchIds) {
      const departmentIds = flattenTree(departmentsByBranch.value[branchId] || [])
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

const filterSignature = computed(() => [
  props.mode,
  companyId.value || 0,
  normalizeSelectStringValue(dateFieldFilter.value, "start_at"),
  dateFromFilter.value,
  dateToFilter.value,
  normalizeSelectStringValue(tenderTypeFilter.value, "all"),
  normalizeSelectStringValue(statusFilter.value, "active"),
  branchIdsFilter.value.join(","),
  departmentIdsFilter.value.join(","),
  categoryIdsFilter.value.join(","),
  expenseIdsFilter.value.join(","),
  userIdsFilter.value.join(","),
]);

watch(filterSignature, () => {
  if (!initialized.value) return;
  loadAnalytics();
});

onMounted(async () => {
  await loadFilterOptions();
  initialized.value = true;
  await loadAnalytics();
});
</script>
