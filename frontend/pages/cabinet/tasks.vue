<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-2xl font-bold">Активні завдання</h2>
      <UButton
        icon="i-heroicons-arrow-path"
        variant="soft"
        :loading="isLoading || isRefreshing"
        @click="loadTasks"
      >
        Оновити
      </UButton>
    </div>

    <div
      class="flex-1 min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div
        v-if="isLoading"
        class="flex h-full min-h-[200px] items-center justify-center text-gray-500"
      >
        Завантаження завдань...
      </div>

      <div v-else-if="tasks.length > 0" class="flex h-full min-h-0 flex-col">
        <div class="min-h-0 flex-1 overflow-auto pr-1">
          <UTable
            :data="paginatedTasks"
            :columns="columns"
            class="w-full"
          >
            <template #tender-cell="{ row }">
              <NuxtLink
                :to="row.original.tender_link"
                class="font-medium text-primary hover:underline"
              >
                Тендер {{ row.original.tender_number }}
                <template v-if="row.original.tour_number > 1">
                  (тур {{ row.original.tour_number }})
                </template>
              </NuxtLink>
            </template>
          </UTable>
        </div>

        <div
          class="flex flex-shrink-0 items-center justify-between gap-3 border-t border-gray-200 pt-3"
        >
          <span class="text-sm text-gray-600">
            Показано {{ paginatedTasks.length }} з {{ totalTasks }}
          </span>

          <UPagination
            v-model:page="currentPage"
            :total="totalTasks"
            :items-per-page="TASKS_PAGE_SIZE"
            :sibling-count="1"
            show-edges
          />
        </div>
      </div>

      <div
        v-else
        class="flex h-full min-h-[200px] items-center justify-center text-gray-500"
      >
        Активних завдань немає.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TenderListItem } from "~/domains/tenders/tenders.types";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Активні завдання",
  },
});

type StageTask = {
  action: string;
  stage_label: string;
};

type UserTaskRow = {
  task_key: string;
  task_label: string;
  stage_label: string;
  tender_type: string;
  tender_number: string;
  tender_name: string;
  tour_number: number;
  tender_link: string;
  created_at?: string;
};

const STAGE_TO_TASK: Record<string, StageTask> = {
  preparation: {
    action: "Виконати підготовку процедури",
    stage_label: "Підготовка процедури",
  },
  decision: {
    action: "Прийняти рішення",
    stage_label: "Вибір рішення",
  },
  approval: {
    action: "Затвердити рішення",
    stage_label: "Затвердження",
  },
};

const TASKS_PAGE_SIZE = 50;
const TASKS_POLL_INTERVAL_MS = 60_000;

const tendersUC = useTendersUseCases();

const isLoading = ref(false);
const isRefreshing = ref(false);
const hasLoadedOnce = ref(false);
const tasks = ref<UserTaskRow[]>([]);
const currentPage = ref(1);
let tasksRefreshTimer: ReturnType<typeof setInterval> | null = null;

const totalTasks = computed(() => tasks.value.length);
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * TASKS_PAGE_SIZE;
  return tasks.value.slice(start, start + TASKS_PAGE_SIZE);
});

const columns = [
  { accessorKey: "task_label", header: "Завдання" },
  { accessorKey: "tender", header: "Документ" },
  { accessorKey: "tender_name", header: "Назва" },
  { accessorKey: "tender_type", header: "Тип" },
  { accessorKey: "stage_label", header: "Етап" },
];

function toTaskRows(tenders: TenderListItem[], isSales: boolean): UserTaskRow[] {
  const tenderTypeLabel = isSales ? "Продаж" : "Закупівля";
  const basePath = isSales ? "/cabinet/tenders/sales" : "/cabinet/tenders";

  return tenders
    .map((item) => {
      const stage = String(item.stage ?? "");
      const task = STAGE_TO_TASK[stage];
      const taskAction =
        typeof item.task_action === "string" && item.task_action.trim()
          ? item.task_action.trim()
          : "";
      if (!task && !taskAction) return null;

      const numberRaw = String(item.number ?? item.id ?? "");
      return {
        task_key: `${isSales ? "sales" : "purchase"}-${item.id}-${stage}-${String(item.task_kind ?? "author")}`,
        task_label: taskAction || task!.action,
        stage_label: item.stage_label || task?.stage_label || "",
        tender_type: tenderTypeLabel,
        tender_number: `№${numberRaw}`,
        tender_name: String(item.name ?? ""),
        tour_number: Number(item.tour_number ?? 1),
        tender_link: `${basePath}/${item.id}`,
        created_at:
          typeof item.task_created_at === "string"
            ? item.task_created_at
            : typeof item.created_at === "string"
              ? item.created_at
              : undefined,
      } as UserTaskRow;
    })
    .filter((item): item is UserTaskRow => item !== null);
}

async function loadTasks(options: { silent?: boolean } = {}) {
  const silent = options.silent === true;
  if (!hasLoadedOnce.value) {
    isLoading.value = true;
  } else if (!silent) {
    isRefreshing.value = true;
  }

  try {
    const [{ data: purchasePayload }, { data: salesPayload }] = await Promise.all([
      tendersUC.getTenderActiveTasks(false, { limit: 1000, skipLoader: true }),
      tendersUC.getTenderActiveTasks(true, { limit: 1000, skipLoader: true }),
    ]);
    const purchase =
      (purchasePayload as { results?: TenderListItem[] } | null)?.results ?? [];
    const sales =
      (salesPayload as { results?: TenderListItem[] } | null)?.results ?? [];

    const purchaseTasks = toTaskRows(Array.isArray(purchase) ? purchase : [], false);
    const salesTasks = toTaskRows(Array.isArray(sales) ? sales : [], true);

    tasks.value = [...purchaseTasks, ...salesTasks].sort((a, b) => {
      const aTime = new Date(a.created_at ?? 0).getTime();
      const bTime = new Date(b.created_at ?? 0).getTime();
      return bTime - aTime;
    });
  } finally {
    if (!hasLoadedOnce.value) {
      hasLoadedOnce.value = true;
      isLoading.value = false;
      return;
    }

    if (!silent) {
      isRefreshing.value = false;
    }
  }
}

watch(totalTasks, (total) => {
  const maxPage = Math.max(1, Math.ceil(total / TASKS_PAGE_SIZE));
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage;
  }
});

onMounted(async () => {
  await loadTasks();
  if (!tasksRefreshTimer) {
    tasksRefreshTimer = setInterval(() => {
      void loadTasks({ silent: true });
    }, TASKS_POLL_INTERVAL_MS);
  }
});

onBeforeUnmount(() => {
  if (tasksRefreshTimer) {
    clearInterval(tasksRefreshTimer);
    tasksRefreshTimer = null;
  }
});
</script>
