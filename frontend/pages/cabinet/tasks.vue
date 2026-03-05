<template>
  <div class="h-full min-h-0 flex flex-col">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold">Активні завдання</h2>
      <UButton
        icon="i-heroicons-arrow-path"
        variant="soft"
        :loading="isLoading"
        @click="loadTasks"
      >
        Оновити
      </UButton>
    </div>

    <div class="flex-1 min-h-0 bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-auto">
      <div
        v-if="isLoading"
        class="h-full min-h-[200px] text-gray-500 flex items-center justify-center"
      >
        Завантаження завдань...
      </div>

      <UTable
        v-else-if="tasks.length > 0"
        :data="tasks"
        :columns="columns"
        class="w-full"
      >
        <template #tender-cell="{ row }">
          <NuxtLink
            :to="row.original.tender_link"
            class="text-primary hover:underline font-medium"
          >
            {{ row.original.tender_number }}
            <template v-if="row.original.tour_number > 1">
              (тур {{ row.original.tour_number }})
            </template>
          </NuxtLink>
        </template>
      </UTable>

      <div
        v-else
        class="h-full min-h-[200px] text-gray-500 flex items-center justify-center"
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

const tendersUC = useTendersUseCases();

const isLoading = ref(false);
const tasks = ref<UserTaskRow[]>([]);

const columns = [
  { accessorKey: "task_label", header: "Завдання" },
  { accessorKey: "stage_label", header: "Етап" },
  { accessorKey: "tender_type", header: "Тип тендера" },
  { accessorKey: "tender", header: "Тендер" },
  { accessorKey: "tender_name", header: "Назва" },
];

function toTaskRows(
  tenders: TenderListItem[],
  isSales: boolean
): UserTaskRow[] {
  const tenderTypeLabel = isSales ? "Продаж" : "Закупівля";
  const basePath = isSales ? "/cabinet/tenders/sales" : "/cabinet/tenders";

  return tenders
    .map((item) => {
      const stage = String(item.stage ?? "");
      const task = STAGE_TO_TASK[stage];
      if (!task) return null;

      const numberRaw = String(item.number ?? item.id ?? "");
      return {
        task_key: `${isSales ? "sales" : "purchase"}-${item.id}-${stage}`,
        task_label: task.action,
        stage_label: item.stage_label || task.stage_label,
        tender_type: tenderTypeLabel,
        tender_number: `№${numberRaw}`,
        tender_name: String(item.name ?? ""),
        tour_number: Number(item.tour_number ?? 1),
        tender_link: `${basePath}/${item.id}`,
        created_at: typeof item.created_at === "string" ? item.created_at : undefined,
      } as UserTaskRow;
    })
    .filter((item): item is UserTaskRow => item !== null);
}

async function loadTasks() {
  isLoading.value = true;
  try {
    const [{ data: purchasePayload }, { data: salesPayload }] = await Promise.all([
      tendersUC.getTenderActiveTasks(false, { limit: 1000 }),
      tendersUC.getTenderActiveTasks(true, { limit: 1000 }),
    ]);
    const purchase = (purchasePayload as { results?: TenderListItem[] } | null)?.results ?? [];
    const sales = (salesPayload as { results?: TenderListItem[] } | null)?.results ?? [];

    const purchaseTasks = toTaskRows(
      Array.isArray(purchase) ? purchase : [],
      false
    );
    const salesTasks = toTaskRows(
      Array.isArray(sales) ? sales : [],
      true
    );

    tasks.value = [...purchaseTasks, ...salesTasks].sort((a, b) => {
      const aTime = new Date(a.created_at ?? 0).getTime();
      const bTime = new Date(b.created_at ?? 0).getTime();
      return bTime - aTime;
    });
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadTasks();
});
</script>
