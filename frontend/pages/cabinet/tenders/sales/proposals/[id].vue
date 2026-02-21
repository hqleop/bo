<template>
  <div>
    <div v-if="loading" class="flex items-center justify-center py-12">
      <UIcon
        name="i-heroicons-arrow-path"
        class="animate-spin size-8 text-gray-400"
      />
    </div>
    <div v-else-if="!tender" class="text-center py-12 text-gray-500">
      Тендер не знайдено.
    </div>
    <div v-else class="h-full flex flex-col">
      <div class="mb-4">
        <h1 class="text-xl font-semibold text-gray-900 truncate">
          № {{ tender.number }}
          <span class="font-normal text-gray-700">{{ tender.name }}</span>
        </h1>
      </div>
      <div
        v-if="!isParticipant"
        class="tender-stepper tender-stepper--compact mb-2"
      >
        <UStepper
          :model-value="currentStage"
          :items="stepperItems"
          value-key="value"
          size="sm"
          @update:model-value="onStageClick"
        />
      </div>

      <div class="flex flex-1 min-h-0 gap-6">
        <div class="flex-1 min-w-0 min-h-0 flex flex-col gap-4">
          <div class="flex items-center justify-between gap-4">
            <h2 class="text-base font-bold text-gray-800">
              Подача пропозицій (продаж)
            </h2>
            <UButton
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-left"
              @click="isParticipant ? navigateTo('/cabinet/participation?type=sales') : goBack()"
            >
              {{ isParticipant ? 'До списку тендерів' : 'Повернутись до підготовки' }}
            </UButton>
          </div>
          <p
            v-if="isViewingPreviousTour"
            class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
          >
            Перегляд попереднього туру. Зміни пропозицій заборонені.
          </p>
          <UFormField v-if="!isParticipant" label="Контрагент (покупець)">
            <div class="flex gap-2 items-center">
              <span
                v-if="selectedSupplier"
                class="flex-1 py-2 px-3 border rounded bg-gray-50"
              >
                {{ selectedSupplier.label }}
                <span
                  v-if="selectedSupplier.edrpou"
                  class="text-gray-500 text-sm"
                  >({{ selectedSupplier.edrpou }})</span
                >
              </span>
              <span
                v-else
                class="flex-1 py-2 px-3 border rounded bg-gray-50 text-gray-500"
                >Не обрано</span
              >
              <UButton
                variant="outline"
                :disabled="isViewingPreviousTour"
                @click="showSupplierModal = true"
              >
                Обрати контрагента
              </UButton>
            </div>
          </UFormField>

          <div v-if="tenderCriteriaGeneral.length > 0" class="rounded-lg border border-blue-200 bg-blue-50/50 p-3 space-y-3 mb-4">
            <h4 class="text-sm font-semibold text-gray-800">Загальні критерії</h4>
            <p class="text-xs text-gray-600">Одне значення стосується всіх позицій.</p>
            <div class="flex flex-wrap gap-4">
              <UFormField
                v-for="c in tenderCriteriaGeneral"
                :key="c.id"
                :label="c.name"
                class="mb-0 min-w-[200px]"
              >
                <UInput
                  v-if="currentProposal && !isViewingPreviousTour && (!isParticipant || participantCanEdit)"
                  v-model="generalCriterionValues[c.id]"
                  size="sm"
                  class="w-full"
                  @blur="savePositionValues"
                />
                <span v-else class="block py-1.5 text-sm text-gray-700">{{
                  generalCriterionValues[c.id] || "—"
                }}</span>
              </UFormField>
            </div>
          </div>

          <div class="flex-1 min-h-0 overflow-auto">
            <UCard>
              <template #header>
                <h3 class="text-lg font-semibold">
                  Позиції тендера (додані на етапі Підготовка)
                </h3>
              </template>
              <p v-if="!tenderPositions.length" class="text-gray-500 py-4">
                У тендері немає позицій. Додайте позиції на етапі «Підготовка
                процедури» та поверніться сюди.
              </p>
              <template v-else>
                <div class="overflow-x-auto">
                  <table class="w-full text-sm border-collapse">
                    <thead>
                      <tr class="border-b bg-gray-50">
                        <th class="text-left p-2 font-medium">Назва</th>
                        <th class="text-left p-2 font-medium">Кількість</th>
                        <th class="text-left p-2 font-medium">Опис</th>
                        <th class="text-left p-2 font-medium whitespace-nowrap">
                          {{ priceColumnHeader }}
                        </th>
                        <th
                          v-for="c in tenderCriteriaIndividual"
                          :key="c.id"
                          class="text-left p-2 font-medium"
                        >
                          {{ c.name }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in positionRows"
                        :key="row.id"
                        class="border-b hover:bg-gray-50/50"
                      >
                        <td class="p-2">{{ row.name }}</td>
                        <td class="p-2">
                          {{ row.quantity }} {{ row.unit_name }}
                        </td>
                        <td class="p-2 max-w-[200px]">
                          {{ row.description || "—" }}
                        </td>
                        <td class="p-2">
                          <UInput
                            v-if="currentProposal && !isViewingPreviousTour && (!isParticipant || participantCanEdit)"
                            v-model="row.price"
                            type="number"
                            step="0.01"
                            size="sm"
                            class="min-w-[100px]"
                            @blur="savePositionValues"
                          />
                          <span v-else class="text-gray-700">{{
                            row.price || "—"
                          }}</span>
                        </td>
                        <td v-for="c in tenderCriteriaIndividual" :key="c.id" class="p-2">
                          <UInput
                            v-if="currentProposal && !isViewingPreviousTour && (!isParticipant || participantCanEdit)"
                            v-model="row.criterion_values[c.id]"
                            size="sm"
                            class="min-w-[80px]"
                            @blur="savePositionValues"
                          />
                          <span v-else class="text-gray-700">{{
                            row.criterion_values[c.id] || "—"
                          }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div
                  v-if="currentProposal && !isViewingPreviousTour && !isParticipant"
                  class="mt-3 pt-3 border-t"
                >
                  <UButton size="sm" @click="savePositionValues"
                    >Зберегти значення</UButton
                  >
                </div>
                <p
                  v-else-if="!isParticipant && !isViewingPreviousTour"
                  class="text-sm text-gray-500 mt-3"
                >
                  Оберіть контрагента (покупця) вище, щоб заповнити ціну та
                  критерії по позиціях.
                </p>
              </template>
            </UCard>
          </div>
        </div>

        <aside class="w-72 flex-shrink-0 flex flex-col gap-4">
          <template v-if="isParticipant">
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm font-medium text-gray-800">
              {{ timerText }}
            </div>
            <UButton
              v-if="!isProposalSubmitted"
              class="w-full"
              :loading="submitWithdrawLoading"
              :disabled="!participantCanEdit"
              @click="onSubmitProposal"
            >
              Подати пропозицію
            </UButton>
            <UButton
              v-else
              class="w-full"
              color="error"
              variant="solid"
              :loading="submitWithdrawLoading"
              :disabled="!participantCanWithdraw"
              @click="onWithdrawProposal"
            >
              Відкликати пропозицію
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="showFilesModal = true"
            >
              Прикріплені файли
            </UButton>
          </template>
          <template v-else>
            <div class="space-y-3">
              <UButton
                class="w-full"
                :disabled="!canGoToDecision"
                @click="goToDecisionStage"
              >
                Перейти на вибір рішення
              </UButton>
              <UButton
                class="w-full"
                variant="outline"
                @click="showCheckModal = true"
              >
                Усі пропозиції
              </UButton>
              <UButton
                class="w-full"
                variant="outline"
                @click="showFilesModal = true"
              >
                Прикріплені файли
              </UButton>
            </div>
          </template>
        </aside>
      </div>

      <!-- Модальне вікно вибору контрагента (покупця) -->
      <UModal v-model:open="showSupplierModal">
        <template #content>
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">
                Обрати контрагента (покупця)
              </h3>
            </template>
            <UFormField label="Пошук за назвою або кодом ЄДРПОУ">
              <UInput
                v-model="supplierSearch"
                placeholder="Введіть назву або ЄДРПОУ"
                class="mb-3"
              />
            </UFormField>
            <div class="max-h-80 overflow-y-auto space-y-1">
              <button
                v-for="s in filteredSuppliers"
                :key="s.value"
                type="button"
                class="w-full text-left px-3 py-2 rounded hover:bg-gray-100 border border-transparent hover:border-gray-200"
                @click="selectSupplier(s)"
              >
                <span class="font-medium">{{ s.label }}</span>
                <span v-if="s.edrpou" class="text-gray-500 text-sm ml-2"
                  >({{ s.edrpou }})</span
                >
              </button>
              <p
                v-if="filteredSuppliers.length === 0"
                class="text-gray-500 py-4 text-center"
              >
                Нічого не знайдено. Змініть пошук або додайте контрагента в
                розділі «Контрагенти».
              </p>
            </div>
          </UCard>
        </template>
      </UModal>

      <UModal
        v-model:open="showCheckModal"
        :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
      >
        <template #content>
          <UCard class="flex flex-col max-h-[90vh] overflow-hidden">
            <template #header>
              <h3 class="text-lg font-semibold">Усі пропозиції</h3>
            </template>
            <div
              class="overflow-auto min-h-0 flex-1 resize-y min-h-[300px]"
              style="resize: vertical"
            >
              <table
                v-if="tenderPositions.length && proposals.length"
                class="w-full text-sm border-collapse"
              >
                <thead>
                  <tr class="border-b bg-gray-100">
                    <th
                      class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                    >
                      Назва позиції
                    </th>
                    <th
                      class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                    >
                      Кількість
                    </th>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <th
                        :colspan="2 + tenderCriteria.length"
                        class="text-left p-2 font-medium bg-gray-200 border-l border-gray-300"
                      >
                        {{
                          proposal.supplier_company?.name ||
                          proposal.supplier_name ||
                          "—"
                        }}
                        <span
                          v-if="proposal.supplier_company?.edrpou"
                          class="text-gray-600 font-normal"
                        >
                          ({{ proposal.supplier_company.edrpou }})</span
                        >
                      </th>
                    </template>
                  </tr>
                  <tr class="border-b bg-gray-50">
                    <th class="p-2 bg-gray-50"></th>
                    <th class="p-2 bg-gray-50"></th>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        {{ priceColumnHeader }}
                      </th>
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        Сума
                      </th>
                      <th
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="text-left p-2 font-medium border-l border-gray-200"
                      >
                        {{ c.name }}
                      </th>
                    </template>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="pos in tenderPositions"
                    :key="pos.id"
                    class="border-b hover:bg-gray-50/50"
                  >
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ pos.name }}
                    </td>
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ pos.quantity }} {{ pos.unit_name || "" }}
                    </td>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <td
                        class="p-2 border-l border-gray-200"
                        :class="
                          (checkComparisonByPosition[pos.id]?.bestId ===
                            proposal.id &&
                            'bg-green-500/20') ||
                          (checkComparisonByPosition[pos.id]?.worstId ===
                            proposal.id &&
                            checkComparisonByPosition[pos.id]?.worstId !==
                              checkComparisonByPosition[pos.id]?.bestId &&
                            'bg-red-500/20')
                        "
                      >
                        {{
                          getProposalPositionValue(proposal, pos.id)?.price ??
                          "—"
                        }}
                      </td>
                      <td
                        class="p-2 border-l border-gray-200"
                        :class="
                          (checkComparisonByPosition[pos.id]?.bestId ===
                            proposal.id &&
                            'bg-green-500/20') ||
                          (checkComparisonByPosition[pos.id]?.worstId ===
                            proposal.id &&
                            checkComparisonByPosition[pos.id]?.worstId !==
                              checkComparisonByPosition[pos.id]?.bestId &&
                            'bg-red-500/20')
                        "
                      >
                        {{ getProposalPositionSum(proposal, pos) ?? "—" }}
                      </td>
                      <td
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="p-2 border-l border-gray-200"
                      >
                        {{
                          getProposalCriterionValue(proposal, pos.id, c.id) ??
                          "—"
                        }}
                      </td>
                    </template>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-gray-500 py-8 text-center">
                Немає позицій або пропозицій для порівняння. Додайте позиції в
                тендер та заповніть пропозиції від контрагентів.
              </p>
            </div>
          </UCard>
        </template>
      </UModal>
      <UModal v-model:open="showFilesModal">
        <template #content>
          <UCard>
            <template #header><h3>Прикріплені файли</h3></template>
            <div v-if="tenderFilesLoading" class="text-gray-500">Завантаження...</div>
            <p v-else-if="tenderFilesError" class="text-sm text-red-600">
              {{ tenderFilesError }}
            </p>
            <div v-else-if="tenderFiles.length" class="space-y-2">
              <div
                v-for="f in tenderFiles"
                :key="f.id"
                class="flex items-center justify-between gap-3 rounded border border-gray-200 p-2"
              >
                <a
                  :href="f.file_url || '#'"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-primary-600 hover:underline truncate"
                >
                  {{ f.name || `Файл #${f.id}` }}
                </a>
                <span class="text-xs text-gray-500 shrink-0">
                  {{ formatFileDate(f.uploaded_at) }}
                </span>
              </div>
            </div>
            <p v-else class="text-gray-500">Немає прикріплених файлів.</p>
          </UCard>
        </template>
      </UModal>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Пропозиції — продаж" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));

const tender = ref<any | null>(null);
const loading = ref(true);
const proposals = ref<any[]>([]);
const selectedSupplierId = ref<number | null>(null);
const selectedSupplier = ref<{
  value: number;
  label: string;
  edrpou?: string;
} | null>(null);
const currentProposal = ref<any | null>(null);
const positionRows = ref<any[]>([]);
const showSupplierModal = ref(false);
const supplierSearch = ref("");
const showCheckModal = ref(false);
const showFilesModal = ref(false);
const tenderFiles = ref<any[]>([]);
const tenderFilesLoading = ref(false);
const tenderFilesError = ref("");
const savingPositions = ref(false);
const submitWithdrawLoading = ref(false);
const now = ref(new Date());
let nowInterval: ReturnType<typeof setInterval> | null = null;

const isSales = true;
const tendersUC = useTendersUseCases();
const suppliersUC = useSuppliersUseCases();
const { me } = useMe();
const myCompanyId = computed(() => (me.value as any)?.memberships?.[0]?.company?.id ?? null);
const isParticipant = computed(
  () => tender.value && myCompanyId.value != null && Number(tender.value.company) !== myCompanyId.value,
);

const vatLabels: Record<string, string> = {
  with_vat: "з ПДВ",
  without_vat: "без ПДВ",
};
const deliveryLabels: Record<string, string> = {
  with_delivery: "із урахуванням доставки",
  without_delivery: "без урахування доставки",
};

const tenderCriteria = computed(() => tender.value?.criteria ?? []);
const tenderCriteriaIndividual = computed(() =>
  tenderCriteria.value.filter((c: any) => (c.application || "individual") === "individual"),
);
const tenderCriteriaGeneral = computed(() =>
  tenderCriteria.value.filter((c: any) => (c.application || "individual") === "general"),
);
const generalCriterionValues = ref<Record<number, string>>({});

const tenderPositions = computed(() => tender.value?.positions ?? []);

const stageItems = [
  {
    value: "passport",
    title: "Паспорт тендера",
    icon: "i-heroicons-document-text",
  },
  {
    value: "preparation",
    title: "Підготовка процедури",
    icon: "i-heroicons-clipboard-document-list",
  },
  {
    value: "acceptance",
    title: "Прийом пропозицій",
    icon: "i-heroicons-envelope",
  },
  { value: "decision", title: "Вибір рішення", icon: "i-heroicons-scale" },
  {
    value: "approval",
    title: "Затвердження",
    icon: "i-heroicons-check-circle",
  },
  { value: "completed", title: "Завершений", icon: "i-heroicons-flag" },
];

const visibleStageItems = computed(() => {
  const isRegistration = tender.value?.conduct_type === "registration";
  if (isRegistration) return stageItems.filter((s) => s.value !== "acceptance");
  return stageItems;
});

const currentStage = computed(() => tender.value?.stage ?? "passport");

const isViewingPreviousTour = computed(
  () => tender.value && tender.value.is_latest_tour === false,
);

const acceptanceStartAt = computed(() => {
  const t = tender.value?.start_at;
  return t ? new Date(t).getTime() : null;
});
const acceptanceEndAt = computed(() => {
  const t = tender.value?.end_at;
  return t ? new Date(t).getTime() : null;
});
const timerText = computed(() => {
  const n = now.value.getTime();
  const start = acceptanceStartAt.value;
  const end = acceptanceEndAt.value;
  if (start != null && n < start) {
    const d = Math.max(0, Math.floor((start - n) / 1000));
    const h = Math.floor(d / 3600);
    const m = Math.floor((d % 3600) / 60);
    const s = d % 60;
    return `До початку прийому: ${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  if (end != null && n > end) return "Прийом пропозицій завершено.";
  if (end != null && n <= end) {
    const d = Math.max(0, Math.floor((end - n) / 1000));
    const h = Math.floor(d / 3600);
    const m = Math.floor((d % 3600) / 60);
    const s = d % 60;
    return `До завершення прийому: ${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return "Прийом пропозицій";
});
const participantCanManageProposal = computed(() => {
  if (!tender.value || tender.value.stage !== "acceptance") return false;
  const n = now.value.getTime();
  const start = acceptanceStartAt.value;
  const end = acceptanceEndAt.value;
  if (start != null && n < start) return false;
  if (end != null && n > end) return false;
  return true;
});
const myProposal = computed(() =>
  proposals.value.find(
    (p: any) =>
      p.supplier_company_id === myCompanyId.value ||
      p.supplier_company?.id === myCompanyId.value,
  ),
);
const isProposalSubmitted = computed(() => {
  const proposal = myProposal.value as Record<string, unknown> | undefined;
  if (!proposal) return false;
  const status = String(proposal.status ?? "").toLowerCase();
  if (proposal.withdrawn_at) return false;
  if (status === "withdrawn" || status === "retracted") return false;
  return !!proposal.submitted_at;
});
const participantCanWithdraw = computed(
  () => participantCanManageProposal.value && isProposalSubmitted.value,
);
const participantCanEdit = computed(
  () => participantCanManageProposal.value && !isProposalSubmitted.value,
);

const stepperItems = computed(() => {
  const stage = currentStage.value;
  const order = visibleStageItems.value.map((s) => s.value);
  const progressIndex = order.indexOf(stage);
  return visibleStageItems.value.map((s, index) => ({
    ...s,
    description: "",
    class: [
      index < progressIndex ? "tender-step-done" : "",
      index === progressIndex ? "tender-step-progress-current" : "",
    ]
      .filter(Boolean)
      .join(" "),
  }));
});

const priceColumnHeader = computed(() => {
  const v = tender.value?.price_criterion_vat;
  const d = tender.value?.price_criterion_delivery;
  const vLabel = v && vatLabels[v] ? vatLabels[v] : v || "";
  const dLabel = d && deliveryLabels[d] ? deliveryLabels[d] : d || "";
  const parts = ["Ціна", vLabel, dLabel].filter(Boolean);
  return parts.join(" ");
});

const supplierOptions = ref<
  { value: number; label: string; edrpou?: string }[]
>([]);

const filteredSuppliers = computed(() => {
  const q = (supplierSearch.value || "").trim().toLowerCase();
  if (!q) return supplierOptions.value;
  return supplierOptions.value.filter(
    (s) =>
      (s.label && s.label.toLowerCase().includes(q)) ||
      (s.edrpou && String(s.edrpou).toLowerCase().includes(q)),
  );
});

function getProposalPositionValue(proposal: any, positionId: number) {
  const list = proposal?.position_values || [];
  return list.find(
    (pv: any) =>
      (pv.tender_position_id ??
        pv.tender_position?.id ??
        pv.tender_position) === positionId,
  );
}

function getProposalCriterionValue(
  proposal: any,
  positionId: number,
  criterionId: number,
) {
  const pv = getProposalPositionValue(proposal, positionId);
  const cv = pv?.criterion_values;
  if (!cv || typeof cv !== "object") return null;
  const v = cv[criterionId] ?? cv[String(criterionId)];
  return v != null && v !== "" ? v : null;
}

function getProposalPositionSum(
  proposal: any,
  pos: { id: number; quantity: number },
) {
  const pv = getProposalPositionValue(proposal, pos.id);
  const price = pv?.price;
  if (price == null || price === "") return null;
  const num = Number(price);
  if (Number.isNaN(num)) return null;
  const qty = Number(pos.quantity) || 0;
  return (qty * num).toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

/** Продаж: краща = більша ціна, гірша = менша ціна */
function getBestWorstForPosition(positionId: number) {
  const withPrice: { id: number; price: number }[] = [];
  for (const p of proposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const num = Number(pv?.price);
    if (!Number.isNaN(num)) withPrice.push({ id: p.id, price: num });
  }
  if (withPrice.length === 0) return { bestId: null, worstId: null };
  const best = withPrice.reduce((a, b) => (a.price >= b.price ? a : b));
  const worst = withPrice.reduce((a, b) => (a.price <= b.price ? a : b));
  return { bestId: best.id, worstId: worst.id };
}

const checkComparisonByPosition = computed(() => {
  const out: Record<number, { bestId: number | null; worstId: number | null }> =
    {};
  for (const pos of tenderPositions.value) {
    out[pos.id] = getBestWorstForPosition(pos.id);
  }
  return out;
});

const canGoToDecision = computed(() => {
  return proposals.value.some(
    (p: any) =>
      p.position_values &&
      p.position_values.length > 0 &&
      p.position_values.some((pv: any) => pv.price != null),
  );
});

async function loadTender() {
  const { data } = await tendersUC.getTender(tenderId.value, isSales);
  if (data) {
    tender.value = data;
    buildPositionRowsFromTender();
  }
}

async function loadProposals() {
  const { data } = await tendersUC.getTenderProposals(tenderId.value, isSales);
  if (data) proposals.value = Array.isArray(data) ? data : [];
}

async function loadTenderFiles() {
  tenderFilesLoading.value = true;
  tenderFilesError.value = "";
  try {
    const { data, error } = await tendersUC.getTenderFiles(tenderId.value, isSales);
    if (error) {
      tenderFilesError.value = error;
      tenderFiles.value = [];
      return;
    }
    tenderFiles.value = Array.isArray(data) ? data : [];
  } finally {
    tenderFilesLoading.value = false;
  }
}

function formatFileDate(value?: string) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString("uk-UA");
}

async function loadSuppliers() {
  const { data } = await suppliersUC.getSupplierRelations();
  if (data && Array.isArray(data)) {
    supplierOptions.value = data
      .filter((r: any) => r.supplier_company)
      .map((r: any) => ({
        value: r.supplier_company.id,
        label:
          r.supplier_company.name || String(r.supplier_company.edrpou || ""),
        edrpou: r.supplier_company.edrpou,
      }));
  }
}

async function selectSupplier(s: {
  value: number;
  label: string;
  edrpou?: string;
}) {
  selectedSupplierId.value = s.value;
  selectedSupplier.value = s;
  showSupplierModal.value = false;
  supplierSearch.value = "";
  await onSupplierSelect(s.value);
}

async function onSupplierSelect(id: number | null) {
  if (!id) {
    currentProposal.value = null;
    buildPositionRowsFromTender();
    return;
  }
  const proposal = proposals.value.find(
    (p: any) => p.supplier_company_id === id || p.supplier_company?.id === id,
  );
  if (!proposal) {
    await addProposal(id);
    return;
  }
  currentProposal.value = proposal;
  buildPositionRows(proposal);
}

async function addProposal(supplierCompanyId: number) {
  const { data } = await tendersUC.addProposal(tenderId.value, isSales, {
    supplier_company_id: supplierCompanyId,
  });
  if (data) {
    proposals.value = [...proposals.value, data];
    currentProposal.value = data;
    buildPositionRows(data);
  }
}

function buildPositionRowsFromTender() {
  const positions = tender.value?.positions || [];
  const criteria = tender.value?.criteria || [];
  const generalIds = (tender.value?.criteria || []).filter((c: any) => (c.application || "individual") === "general").map((c: any) => c.id);
  generalCriterionValues.value = generalIds.reduce((acc: Record<number, string>, id: number) => {
    acc[id] = "";
    return acc;
  }, {});
  positionRows.value = positions.map((pos: any) => {
    const criterion_values: Record<number, string> = {};
    for (const c of criteria) {
      criterion_values[c.id] = "";
    }
    return {
      id: pos.id,
      name: pos.name,
      quantity: pos.quantity,
      unit_name: pos.unit_name ?? "",
      description: pos.description ?? "",
      price: "",
      criterion_values,
    };
  });
}

function buildPositionRows(proposal: any) {
  const positions = tender.value?.positions || [];
  const valuesByPos = (proposal.position_values || []).reduce(
    (acc: any, pv: any) => {
      const posId =
        pv.tender_position_id ?? pv.tender_position?.id ?? pv.tender_position;
      acc[posId] = pv;
      return acc;
    },
    {},
  );
  const criteria = tender.value?.criteria || [];
  const generalCriteria = criteria.filter((c: any) => (c.application || "individual") === "general");
  const newRows = positions.map((pos: any) => {
    const pv = valuesByPos[pos.id];
    const criterion_values: Record<number, string> = {};
    if (pv?.criterion_values && typeof pv.criterion_values === "object") {
      for (const [k, v] of Object.entries(pv.criterion_values)) {
        criterion_values[Number(k)] = String(v ?? "");
      }
    }
    for (const c of criteria) {
      if (criterion_values[c.id] === undefined) criterion_values[c.id] = "";
    }
    return {
      id: pos.id,
      name: pos.name,
      quantity: pos.quantity,
      unit_name: pos.unit_name ?? "",
      description: pos.description ?? "",
      price: pv?.price != null ? String(pv.price) : "",
      criterion_values,
    };
  });
  positionRows.value = [...newRows];
  for (const c of generalCriteria) {
    const firstVal = newRows[0]?.criterion_values?.[c.id];
    if (firstVal !== undefined) generalCriterionValues.value[c.id] = firstVal;
  }
}

async function savePositionValues() {
  if (!currentProposal.value?.id || !positionRows.value.length) return;
  savingPositions.value = true;
  const generalVals = generalCriterionValues.value;
  try {
    const position_values = positionRows.value.map((row) => {
      const cv = row.criterion_values || {};
      const criterion_values: Record<string, string | number> = {};
      for (const c of tenderCriteria.value) {
        const val = (c.application || "individual") === "general"
          ? generalVals[c.id]
          : cv[c.id];
        if (val !== "" && val != null) criterion_values[String(c.id)] = val;
      }
      return {
        tender_position_id: row.id,
        price: row.price !== "" ? parseFloat(String(row.price)) : null,
        criterion_values,
      };
    });
    const { data } = await tendersUC.patchProposalPositionValues(
      tenderId.value,
      currentProposal.value.id,
      isSales,
      { position_values },
    );
    if (data) {
      currentProposal.value = data;
      buildPositionRows(data);
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) {
        proposals.value = proposals.value.map((p: any, i: number) =>
          i === idx ? data : p,
        );
      }
      await nextTick();
    }
  } finally {
    savingPositions.value = false;
  }
}

async function onSubmitProposal() {
  submitWithdrawLoading.value = true;
  try {
    const { data } = await tendersUC.submitProposal(tenderId.value, isSales);
    if (data) {
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) proposals.value[idx] = data;
      if (currentProposal.value?.id === data.id) {
        currentProposal.value = data;
      }
    }
  } finally {
    submitWithdrawLoading.value = false;
  }
}

async function onWithdrawProposal() {
  submitWithdrawLoading.value = true;
  try {
    const { data } = await tendersUC.withdrawProposal(tenderId.value, isSales);
    if (data) {
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) proposals.value[idx] = data;
      if (currentProposal.value?.id === data.id) {
        currentProposal.value = data;
      }
    }
  } finally {
    submitWithdrawLoading.value = false;
  }
}

function goBack() {
  navigateTo(`/cabinet/tenders/sales/${tenderId.value}`);
}

function onStageClick(_stageValue: string) {
  navigateTo(`/cabinet/tenders/sales/${tenderId.value}`);
}

async function goToDecisionStage() {
  const { data } = await tendersUC.patchTender(tenderId.value, isSales, {
    stage: "decision",
  });
  if (data) {
    tender.value = { ...tender.value, ...data };
    await navigateTo(`/cabinet/tenders/sales/${tenderId.value}`);
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await loadTender();
    await loadProposals();
    const part = tender.value && myCompanyId.value != null && Number(tender.value.company) !== myCompanyId.value;
    if (!part) await loadSuppliers();
    if (part && myProposal.value) {
      currentProposal.value = myProposal.value;
      buildPositionRows(myProposal.value);
    } else if (proposals.value.length > 0 && !selectedSupplierId.value) {
      const first = proposals.value[0];
      const id = first.supplier_company?.id ?? first.supplier_company_id ?? null;
      if (id) {
        selectedSupplierId.value = id;
        selectedSupplier.value = supplierOptions.value.find(
          (s) => s.value === id,
        ) || {
          value: id,
          label:
            first.supplier_company?.name ||
            String(first.supplier_company?.edrpou || ""),
          edrpou: first.supplier_company?.edrpou,
        };
        onSupplierSelect(id);
      }
    }
    if (part) {
      nowInterval = setInterval(() => {
        now.value = new Date();
      }, 1000);
    }
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  if (nowInterval) clearInterval(nowInterval);
});

watch(showFilesModal, async (open) => {
  if (!open) return;
  await loadTenderFiles();
});
</script>
