<template>
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
    <div class="tender-stepper mb-6">
      <UStepper
        v-model="currentStepValue"
        :items="stepperItems"
        value-key="value"
      />
    </div>

    <div class="flex flex-1 min-h-0 gap-6">
      <div
        class="flex-1 min-w-0 min-h-0"
        :class="displayStage === 'preparation' ? '' : 'overflow-y-auto'"
      >
        <template v-if="displayStage === 'passport'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Паспорт тендера</h3>
            </template>
            <UForm :state="form" class="space-y-4">
              <UFormField label="Назва тендера" required>
                <UInput v-model="form.name" placeholder="Назва тендера" />
              </UFormField>
              <ContentSearch
                label="Категорія"
                placeholder="Оберіть категорію"
                search-placeholder="Пошук категорії"
                :disabled="(form.cpv_ids?.length ?? 0) > 0"
                :tree="categoryTree"
                :selected-ids="selectedCategoryIds"
                :search-term="categorySearch"
                @toggle="toggleCategory"
                @update:search-term="categorySearch = $event"
              />
              <CpvLazyMultiSearch
                label="Категорія CPV"
                placeholder="Оберіть CPV"
                :disabled="!!form.category"
                :selected-ids="form.cpv_ids"
                :selected-labels="tenderCpvLabels"
                @update:selected-ids="form.cpv_ids = $event"
                @update:selected-labels="tenderCpvLabels = $event"
              />
              <UFormField label="Стаття бюджету">
                <USelectMenu
                  v-model="form.expense_article"
                  :items="expenseOptions"
                  value-key="value"
                  placeholder="Оберіть статтю"
                />
              </UFormField>
              <UFormField label="Орієнтовний бюджет">
                <UInput
                  v-model.number="form.estimated_budget"
                  type="number"
                  step="0.01"
                  placeholder="0"
                />
              </UFormField>
              <UFormField label="Філіал">
                <USelectMenu
                  v-model="form.branch"
                  :items="branchOptions"
                  value-key="value"
                  placeholder="Оберіть філіал"
                  @update:model-value="onBranchChange"
                />
              </UFormField>
              <UFormField label="Підрозділ">
                <USelectMenu
                  v-model="form.department"
                  :items="departmentOptions"
                  value-key="value"
                  placeholder="Оберіть підрозділ"
                />
              </UFormField>
              <UFormField label="Тип проведення" required>
                <USelectMenu
                  v-model="form.conduct_type"
                  :items="conductTypeOptions"
                  value-key="value"
                  placeholder="Оберіть тип"
                />
              </UFormField>
              <UFormField label="Тип публікації" required>
                <USelectMenu
                  v-model="form.publication_type"
                  :items="publicationTypeOptions"
                  value-key="value"
                  placeholder="Оберіть тип"
                />
              </UFormField>
              <UFormField label="Валюта тендера" required>
                <USelectMenu
                  v-model="form.currency"
                  :items="currencyOptions"
                  value-key="value"
                  placeholder="Оберіть валюту"
                />
              </UFormField>
              <UFormField label="Загальні умови">
                <UTextarea
                  v-model="form.general_terms"
                  :rows="6"
                  placeholder="Опис загальних умов"
                />
              </UFormField>
            </UForm>
          </UCard>
        </template>

        <template v-else-if="tender.stage === 'preparation'">
          <div
            class="h-full min-h-0 flex flex-col border rounded-lg p-4 bg-white"
          >
            <h3 class="text-lg font-semibold mb-3">Підготовка процедури</h3>
            <UTabs
              v-model="prepTab"
              :items="prepTabs"
              value-key="value"
              class="mb-4"
              content
            >
              <template #content="{ item }">
                <div
                  v-if="item.value === 'positions'"
                  class="h-full min-h-0 flex flex-col gap-3"
                >
                  <div class="flex items-end gap-3">
                    <div class="w-full max-w-xl">
                      <ContentSearch
                        label="Пошук і додавання номенклатури"
                        placeholder="Номенклатура"
                        search-placeholder="Пошук номенклатури"
                        :tree="nomenclatureSearchTree"
                        :selected-ids="selectedNomenclatureIds"
                        :search-term="nomenclatureSearch"
                        @toggle="toggleTenderPosition"
                        @update:search-term="nomenclatureSearch = $event"
                      />
                    </div>
                  </div>

                  <div
                    v-if="loadingNomenclatures"
                    class="text-sm text-gray-500 py-2"
                  >
                    Завантаження номенклатур...
                  </div>
                  <div
                    v-else-if="!nomenclatureSearchTree.length"
                    class="text-sm text-gray-500 py-2"
                  >
                    Немає доступних номенклатур для обраної категорії/CPV.
                  </div>

                  <div class="flex-1 min-h-0 overflow-auto">
                    <UTable
                      :data="tenderPositions"
                      :columns="positionsColumns"
                      class="w-full"
                    >
                      <template #quantity-cell="{ row }">
                        <UInput
                          type="number"
                          min="0"
                          step="0.01"
                          v-model.number="row.original.quantity"
                          size="sm"
                        />
                      </template>
                      <template #description-cell="{ row }">
                        <UInput v-model="row.original.description" size="sm" />
                      </template>
                      <template #vat-cell>
                        <UInput value="" disabled size="sm" />
                      </template>
                    </UTable>
                  </div>
                </div>

                <div v-else class="space-y-6">
                  <!-- Параметри цінового критерія -->
                  <div class="border rounded-lg p-4 bg-gray-50/50">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3">
                      Параметри цінового критерія
                    </h4>
                    <div class="flex flex-wrap gap-6">
                      <UFormField label="ПДВ" class="min-w-[200px]">
                        <USelectMenu
                          v-model="priceCriterionVat"
                          :items="vatOptions"
                          value-key="value"
                          placeholder="Оберіть варіант"
                        />
                      </UFormField>
                      <UFormField label="Доставка" class="min-w-[260px]">
                        <USelectMenu
                          v-model="priceCriterionDelivery"
                          :items="deliveryOptions"
                          value-key="value"
                          placeholder="Оберіть варіант"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <!-- Інші критерії тендера -->
                  <div class="border rounded-lg p-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3">
                      Інші критерії тендера
                    </h4>
                    <p class="text-sm text-gray-600 mb-3">
                      Додайте критерії з довідника. Учасники заповнюватимуть їх у пропозиціях.
                    </p>
                    <div class="flex items-end gap-3 mb-3">
                      <div class="w-full max-w-xl">
                        <ContentSearch
                          label="Пошук і додавання критеріїв"
                          placeholder="Критерії з довідника"
                          search-placeholder="Пошук критеріїв"
                          :tree="criteriaSearchTree"
                          :selected-ids="selectedCriteriaIds"
                          :search-term="criteriaSearch"
                          @toggle="toggleTenderCriterion"
                          @update:search-term="criteriaSearch = $event"
                        />
                      </div>
                    </div>
                    <ul
                      v-if="tenderCriteria.length > 0"
                      class="space-y-2 text-sm"
                    >
                      <li
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="flex items-center justify-between gap-2 py-2 px-3 rounded-md bg-gray-50 border border-gray-200"
                      >
                        <span class="font-medium">{{ c.name }}</span>
                        <span class="text-gray-500 text-xs">{{ criterionTypeLabel(c.type) }}</span>
                        <UButton
                          icon="i-heroicons-trash"
                          size="xs"
                          variant="ghost"
                          color="error"
                          aria-label="Видалити з тендера"
                          @click="removeCriterionFromTender(c)"
                        />
                      </li>
                    </ul>
                    <p
                      v-else
                      class="text-sm text-gray-500 py-2"
                    >
                      Критерії не додано. Оберіть критерії з довідника вище.
                    </p>
                  </div>
                </div>
              </template>
            </UTabs>
          </div>
        </template>

        <template v-else-if="displayStage === 'acceptance'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Прийом пропозицій</h3>
            </template>
            <p class="text-sm text-gray-600">
              На цьому етапі відображаються пропозиції учасників по позиціях.
            </p>
            <p class="text-xs text-gray-500 mt-2">
              Якщо час завершення минув, етап автоматично переведеться на «Вибір
              рішення».
            </p>
          </UCard>
        </template>

        <template v-else-if="displayStage === 'decision'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Вибір рішення</h3>
            </template>
            <p class="text-sm text-gray-600">
              Рекомендація системи для закупівлі: обрати учасника з найменшою
              ціною.
            </p>
          </UCard>
        </template>

        <template v-else-if="displayStage === 'approval'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Затвердження</h3>
            </template>
            <p class="text-sm text-gray-600">
              Підтвердьте рішення, щоб завершити тендер.
            </p>
          </UCard>
        </template>

        <template v-else>
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Завершений</h3>
            </template>
            <p class="text-sm text-gray-600">Тендер завершено.</p>
          </UCard>
        </template>
      </div>

      <aside class="w-56 flex-shrink-0 space-y-3">
        <template v-if="tender.stage === 'passport'">
          <UButton class="w-full" :loading="saving" @click="savePassport"
            >Зберегти</UButton
          >
        </template>

        <template v-else-if="tender.stage === 'preparation'">
          <template v-if="form.conduct_type === 'registration'">
            <UButton
              class="w-full"
              variant="outline"
              @click="
                alert('Фіксація процедури буде деталізована наступним кроком.')
              "
              >Фіксація процедури</UButton
            >
            <UButton class="w-full" @click="goToDecision"
              >Подача пропозицій</UButton
            >
          </template>
          <template v-else>
            <UButton class="w-full" @click="openPublishModal"
              >Опублікувати</UButton
            >
            <UButton
              class="w-full"
              variant="outline"
              @click="
                alert(
                  'Модальне вікно запрошення учасників буде додано наступним кроком.',
                )
              "
              >Запросити учасників</UButton
            >
          </template>
          <UButton class="w-full" variant="outline" disabled
            >Прикріплені файли</UButton
          >
        </template>

        <template v-else-if="tender.stage === 'acceptance'">
          <UButton class="w-full" @click="openTimingModal"
            >Змінити час проведення</UButton
          >
        </template>

        <template v-else-if="tender.stage === 'decision'">
          <UButton class="w-full" @click="showDecisionModal = true"
            >Зафіксувати рішення</UButton
          >
        </template>

        <template v-else-if="tender.stage === 'approval'">
          <UButton class="w-full" @click="approveTender">Затвердити</UButton>
        </template>
      </aside>
    </div>

    <UModal v-model:open="showPublishModal">
      <template #content>
        <UCard>
          <template #header><h3>Період проведення</h3></template>
          <div class="space-y-4">
            <UFormField label="Початок">
              <UInput v-model="timingForm.start_at" type="datetime-local" />
            </UFormField>
            <UFormField label="Завершення">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="publishTender"
                >Підтвердити</UButton
              >
              <UButton
                class="flex-1"
                variant="outline"
                @click="showPublishModal = false"
                >Скасувати</UButton
              >
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showTimingModal">
      <template #content>
        <UCard>
          <template #header><h3>Змінити час проведення</h3></template>
          <div class="space-y-4">
            <UFormField
              label="Початок"
              :help="
                canEditStart
                  ? ''
                  : 'Після старту час початку змінювати не можна'
              "
            >
              <UInput
                v-model="timingForm.start_at"
                type="datetime-local"
                :disabled="!canEditStart"
              />
            </UFormField>
            <UFormField label="Завершення">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="saveTiming">Зберегти</UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showTimingModal = false"
                >Скасувати</UButton
              >
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showDecisionModal">
      <template #content>
        <UCard>
          <template #header><h3>Зафіксувати рішення</h3></template>
          <div class="space-y-2">
            <UButton class="w-full" @click="fixDecision('winner')"
              >Завершити з переможцем</UButton
            >
            <UButton
              class="w-full"
              variant="outline"
              @click="fixDecision('next_round')"
              >Перевести на наступний тур</UButton
            >
            <UButton
              class="w-full"
              color="red"
              variant="outline"
              @click="fixDecision('cancel')"
              >Скасувати</UButton
            >
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Тендер на закупівлю" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));
const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const tender = ref<any | null>(null);
const loading = ref(true);
const saving = ref(false);
const prepTab = ref<"positions" | "criteria">("positions");
const prepTabs = [
  { label: "Позиції", value: "positions" },
  { label: "Критерії", value: "criteria" },
];

// Параметри цінового критерія (значення value з опцій)
const priceCriterionVat = ref<string | undefined>(undefined);
const priceCriterionDelivery = ref<string | undefined>(undefined);
const vatOptions = [
  { value: "with_vat", label: "з ПДВ" },
  { value: "without_vat", label: "без ПДВ" },
];
const deliveryOptions = [
  { value: "with_delivery", label: "Із урахуванням доставки" },
  { value: "without_delivery", label: "Без урахування доставки" },
];

// Критерії з довідника та додані до тендера
const referenceCriteria = ref<any[]>([]);
const tenderCriteria = ref<any[]>([]);
const criteriaSearch = ref("");
const categorySearch = ref("");
const nomenclatureSearch = ref("");
const loadingNomenclatures = ref(false);
const tenderPositions = ref<any[]>([]);
const availableNomenclatures = ref<any[]>([]);

const showPublishModal = ref(false);
const showTimingModal = ref(false);
const showDecisionModal = ref(false);
const timingForm = reactive({ start_at: "", end_at: "" });

const stageItems = [
  { value: "passport", title: "Паспорт тендера" },
  { value: "preparation", title: "Підготовка процедури" },
  { value: "acceptance", title: "Прийом пропозицій" },
  { value: "decision", title: "Вибір рішення" },
  { value: "approval", title: "Затвердження" },
  { value: "completed", title: "Завершений" },
];
const STAGE_ORDER = stageItems.map((s) => s.value);
const displayStage = ref<string>("passport");

const stepperItems = computed(() => {
  const progressIndex = STAGE_ORDER.indexOf(tender.value?.stage ?? "passport");
  return stageItems.map((s, index) => ({
    ...s,
    description: "",
    class: [
      index < progressIndex ? "tender-step-done" : "",
      index === progressIndex ? "tender-step-progress-current" : "",
      s.value === displayStage.value ? "tender-step-viewing" : "",
    ]
      .filter(Boolean)
      .join(" "),
  }));
});

const currentStepValue = computed({
  get: () => displayStage.value,
  set: (value: string) => {
    const currentIndex = STAGE_ORDER.indexOf(tender.value?.stage ?? "passport");
    const targetIndex = STAGE_ORDER.indexOf(value);
    if (targetIndex !== -1 && targetIndex <= currentIndex) {
      displayStage.value = value;
    }
  },
});

const tenderCpvLabels = ref<string[]>([]);
const form = reactive({
  name: "",
  category: null as number | null,
  cpv_ids: [] as number[],
  expense_article: null as number | null,
  estimated_budget: null as number | null,
  branch: null as number | null,
  department: null as number | null,
  conduct_type: "rfx",
  publication_type: "open",
  currency: null as number | null,
  general_terms: "",
});
const selectedCategoryIds = computed(() =>
  form.category ? [form.category] : [],
);

const conductTypeOptions = [
  { value: "registration", label: "Реєстрація закупівлі" },
  { value: "rfx", label: "Збір пропозицій (RFx)" },
  { value: "online_auction", label: "Онлайн торги" },
];
const publicationTypeOptions = [
  { value: "open", label: "Відкрита процедура" },
  { value: "closed", label: "Закрита процедура" },
];

const categoryTree = ref<any[]>([]);
const expenseOptions = ref<{ value: number; label: string }[]>([]);
const branchOptions = ref<{ value: number; label: string }[]>([]);
const departmentOptions = ref<{ value: number; label: string }[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);
const positionsColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "unit_name", header: "Од. виміру" },
  { accessorKey: "quantity", header: "Кількість" },
  { accessorKey: "description", header: "Опис" },
  { accessorKey: "vat", header: "ПДВ" },
];

const selectedNomenclatureIds = computed(() =>
  tenderPositions.value.map((p) => p.nomenclature_id),
);
const nomenclatureSearchTree = computed(() =>
  availableNomenclatures.value.map((n: any) => ({
    id: n.id,
    name: `${n.name}${n.unit_name ? ` (${n.unit_name})` : ""}`,
    children: [],
  })),
);

const canEditStart = computed(() => {
  if (!tender.value?.start_at) return true;
  return new Date() < new Date(tender.value.start_at);
});

// Дерево критеріїв для ContentSearch (плоский список з полем name)
const criteriaSearchTree = computed(() =>
  referenceCriteria.value.map((c: any) => ({
    id: c.id,
    name: `${c.name} (${criterionTypeLabel(c.type)})`,
    children: [],
  })),
);

const selectedCriteriaIds = computed(() =>
  tenderCriteria.value.map((c) => c.id),
);

function criterionTypeLabel(type: string) {
  const map: Record<string, string> = {
    numeric: "Числовий",
    text: "Текстовий",
    file: "Файловий",
    boolean: "Булевий",
  };
  return map[type] ?? type;
}

async function loadReferenceCriteria() {
  const { data } = await fetch("/tender-criteria/", { headers: getAuthHeaders() });
  referenceCriteria.value = Array.isArray(data) ? data : [];
}

function toggleTenderCriterion(criterionId: number) {
  const existing = tenderCriteria.value.find((c) => c.id === criterionId);
  if (existing) {
    tenderCriteria.value = tenderCriteria.value.filter((x) => x.id !== criterionId);
    return;
  }
  const c = referenceCriteria.value.find((x) => x.id === criterionId);
  if (c) tenderCriteria.value = [...tenderCriteria.value, c];
}

function removeCriterionFromTender(c: any) {
  tenderCriteria.value = tenderCriteria.value.filter((x) => x.id !== c.id);
}

function flattenTree(
  items: any[],
  level = 0,
): { value: number; label: string }[] {
  const out: { value: number; label: string }[] = [];
  for (const item of items || []) {
    out.push({
      value: item.id,
      label: `${"  ".repeat(level)}${item.name || item.label}`,
    });
    if (item.children?.length)
      out.push(...flattenTree(item.children, level + 1));
  }
  return out;
}

function toggleCategory(id: number) {
  form.category = form.category === id ? null : id;
  if (form.category) {
    form.cpv_ids = [];
    tenderCpvLabels.value = [];
  }
}

function isoToInput(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function inputToIso(value: string) {
  return value ? new Date(value).toISOString() : null;
}

async function loadTender() {
  loading.value = true;
  try {
    const { data, error } = await fetch(
      `/procurement-tenders/${tenderId.value}/`,
      { headers: getAuthHeaders() },
    );
    if (error || !data) {
      tender.value = null;
      return;
    }
    tender.value = data;
    displayStage.value = data.stage ?? "passport";
    const cpvList = data.cpv_categories || [];
    form.cpv_ids = cpvList.length
      ? cpvList.map((c: any) => c.id)
      : data.cpv_category != null
        ? [data.cpv_category]
        : [];
    tenderCpvLabels.value = cpvList.length
      ? cpvList.map(
          (c: any) =>
            c.label || `${c.cpv_code || ""} - ${c.name_ua || ""}`.trim(),
        )
      : data.cpv_label
        ? [data.cpv_label]
        : [];
    Object.assign(form, {
      name: data.name ?? "",
      category: data.category ?? null,
      expense_article: data.expense_article ?? null,
      estimated_budget: data.estimated_budget ?? null,
      branch: data.branch ?? null,
      department: data.department ?? null,
      conduct_type: data.conduct_type ?? "rfx",
      publication_type: data.publication_type ?? "open",
      currency: data.currency ?? null,
      general_terms: data.general_terms ?? "",
    });
    timingForm.start_at = isoToInput(data.start_at);
    timingForm.end_at = isoToInput(data.end_at);
    await autoAdvanceAcceptance();
  } finally {
    loading.value = false;
  }
}

async function loadOptions() {
  const headers = getAuthHeaders();
  const [cats, expenses, branches, currencies] = await Promise.all([
    fetch("/categories/", { headers }),
    fetch("/expenses/", { headers }),
    fetch("/branches/", { headers }),
    fetch("/currencies/", { headers }),
  ]);
  categoryTree.value = (cats.data as any[]) || [];
  expenseOptions.value = flattenTree((expenses.data as any[]) || []);
  branchOptions.value = flattenTree((branches.data as any[]) || []);
  currencyOptions.value = ((currencies.data as any[]) || []).map((c: any) => ({
    value: c.id,
    label: `${c.code} - ${c.name}`,
  }));
}

async function loadNomenclaturesForPreparation() {
  loadingNomenclatures.value = true;
  try {
    const headers = getAuthHeaders();
    let items: any[] = [];

    if ((form.cpv_ids?.length ?? 0) > 0) {
      const merged = new Map<number, any>();
      for (const cpvId of form.cpv_ids) {
        const { data: byCpv } = await fetch(`/nomenclatures/?cpv_id=${cpvId}`, {
          headers,
        });
        for (const n of (byCpv as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    } else if (form.category) {
      const { data: byCategory } = await fetch(
        `/nomenclatures/?category_id=${form.category}`,
        { headers },
      );
      const merged = new Map<number, any>();
      for (const n of (byCategory as any[]) || []) merged.set(n.id, n);

      const { data: categoryData } = await fetch(
        `/categories/${form.category}/`,
        {
          headers,
        },
      );
      const cpvIds: number[] = ((categoryData as any)?.cpvs || []).map(
        (c: any) => c.id,
      );
      for (const cpvId of cpvIds) {
        const { data: byCpv } = await fetch(`/nomenclatures/?cpv_id=${cpvId}`, {
          headers,
        });
        for (const n of (byCpv as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    }

    availableNomenclatures.value = items;

    const availableIds = new Set(items.map((n: any) => n.id));
    tenderPositions.value = tenderPositions.value.filter((p) =>
      availableIds.has(p.nomenclature_id),
    );
  } finally {
    loadingNomenclatures.value = false;
  }
}

function toggleTenderPosition(nomenclatureId: number) {
  const existingIndex = tenderPositions.value.findIndex(
    (p) => p.nomenclature_id === nomenclatureId,
  );

  if (existingIndex >= 0) {
    tenderPositions.value.splice(existingIndex, 1);
    return;
  }

  const n = availableNomenclatures.value.find(
    (x: any) => x.id === nomenclatureId,
  );
  if (!n) return;

  tenderPositions.value.push({
    nomenclature_id: n.id,
    name: n.name,
    unit_name: n.unit_name || "",
    quantity: 1,
    description: "",
    vat: "",
  });
}

async function loadDepartments() {
  if (!form.branch) {
    departmentOptions.value = [];
    return;
  }
  const { data } = await fetch(`/departments/?branch_id=${form.branch}`, {
    headers: getAuthHeaders(),
  });
  departmentOptions.value = flattenTree((data as any[]) || []);
}

function onBranchChange() {
  form.department = null;
  loadDepartments();
}

async function patchTender(payload: Record<string, unknown>) {
  if (!tender.value?.id) return false;
  const { data, error } = await fetch(
    `/procurement-tenders/${tender.value.id}/`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: payload,
    },
  );
  if (error || !data) return false;
  tender.value = { ...tender.value, ...data };
  if (data.stage != null) displayStage.value = data.stage;
  return true;
}

async function savePassport() {
  saving.value = true;
  try {
    await patchTender({
      name: form.name,
      category: form.category,
      cpv_ids: form.cpv_ids,
      expense_article: form.expense_article,
      estimated_budget: form.estimated_budget,
      branch: form.branch,
      department: form.department,
      conduct_type: form.conduct_type,
      publication_type: form.publication_type,
      currency: form.currency,
      general_terms: form.general_terms,
      stage: "preparation",
    });
  } finally {
    saving.value = false;
  }
}

function openPublishModal() {
  timingForm.start_at = isoToInput(tender.value?.start_at);
  timingForm.end_at = isoToInput(tender.value?.end_at);
  showPublishModal.value = true;
}

function openTimingModal() {
  timingForm.start_at = isoToInput(tender.value?.start_at);
  timingForm.end_at = isoToInput(tender.value?.end_at);
  showTimingModal.value = true;
}

async function publishTender() {
  if (!timingForm.start_at || !timingForm.end_at) return;
  const ok = await patchTender({
    start_at: inputToIso(timingForm.start_at),
    end_at: inputToIso(timingForm.end_at),
    stage: "acceptance",
  });
  if (ok) showPublishModal.value = false;
}

async function saveTiming() {
  const payload: Record<string, unknown> = {
    end_at: inputToIso(timingForm.end_at),
  };
  if (canEditStart.value) payload.start_at = inputToIso(timingForm.start_at);
  const ok = await patchTender(payload);
  if (ok) showTimingModal.value = false;
}

async function goToDecision() {
  await patchTender({ stage: "decision" });
}

async function autoAdvanceAcceptance() {
  if (tender.value?.stage !== "acceptance" || !tender.value?.end_at) return;
  if (new Date() > new Date(tender.value.end_at)) {
    await patchTender({ stage: "decision" });
  }
}

async function fixDecision(mode: "winner" | "cancel" | "next_round") {
  showDecisionModal.value = false;
  if (mode === "winner" || mode === "cancel") {
    await patchTender({ stage: "approval" });
    return;
  }
  const { data } = await fetch("/procurement-tenders/", {
    method: "POST",
    headers: getAuthHeaders(),
    body: {
      company: tender.value.company,
      parent: tender.value.id,
      tour_number: (tender.value.tour_number || 1) + 1,
      name: tender.value.name,
      stage: "preparation",
      category: tender.value.category,
      cpv_ids: (tender.value.cpv_categories || []).map((c: any) => c.id),
      expense_article: tender.value.expense_article,
      estimated_budget: tender.value.estimated_budget,
      branch: tender.value.branch,
      department: tender.value.department,
      conduct_type: tender.value.conduct_type,
      publication_type: tender.value.publication_type,
      currency: tender.value.currency,
      general_terms: tender.value.general_terms,
    },
  });
  if (data?.id) await navigateTo(`/cabinet/tenders/${data.id}`);
}

async function approveTender() {
  await patchTender({ stage: "completed" });
}

onMounted(async () => {
  await loadTender();
  await loadOptions();
  await loadNomenclaturesForPreparation();
  if (form.branch) await loadDepartments();
});

watch(tenderId, () => loadTender());
watch(
  () => [form.category, form.cpv_ids, tender.value?.stage],
  async () => {
    if (tender.value?.stage === "preparation") {
      await loadNomenclaturesForPreparation();
    }
  },
);
watch(prepTab, (tab) => {
  if (tab === "criteria") loadReferenceCriteria();
});
</script>

<style scoped>
/* Прогрес: пройдені кроки та поточний етап тендера — акцентний колір */
.tender-stepper :deep(.tender-step-done [data-slot="trigger"]),
.tender-stepper :deep(.tender-step-progress-current [data-slot="trigger"]) {
  background-color: var(--color-primary-500);
  color: white;
}
.tender-stepper :deep(.tender-step-done [data-slot="separator"]) {
  background-color: var(--color-primary-500);
}
/* Крок, на якому зараз користувач (перегляд) — світліший */
.tender-stepper :deep(.tender-step-viewing [data-slot="trigger"]) {
  background-color: var(--color-primary-300);
  color: white;
}
</style>
