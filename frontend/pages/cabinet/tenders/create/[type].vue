<template>
  <div class="h-full flex flex-col">
    <div class="tender-stepper tender-stepper--compact mb-1">
      <UStepper
        v-model="currentStepValue"
        :items="stepperItems"
        value-key="value"
        size="sm"
        :disabled="true"
      />
    </div>
    <div class="flex flex-1 min-h-0 gap-6">
      <div
        class="flex-1 min-w-0 min-h-0 flex border border-gray-200 rounded-xl bg-white shadow-sm"
      >
        <UCard class="flex-1 min-h-full">
          <template #header>
            <h3 class="text-lg font-semibold text-gray-900">
              {{ passportTitle }}
            </h3>
          </template>
          <UForm :state="form" class="space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6 lg:gap-8">
              <div class="space-y-6">
                <UFormField label="Назва тендера" required class="mb-0 w-full">
                  <UInput
                    v-model="form.name"
                    placeholder="Введіть назву тендера"
                    size="md"
                    class="w-full"
                  />
                </UFormField>

                <div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ContentSearch
                      label="Категорія"
                      placeholder="Оберіть категорію"
                      search-placeholder="Пошук категорії"
                      :tree="categoryTree"
                      :selected-ids="selectedCategoryIds"
                      :search-term="categorySearch"
                      :disabled-ids="categoryDisabledIds"
                      @toggle="toggleCategory"
                      @update:search-term="categorySearch = $event"
                    />
                    <CpvTenderModalSelect
                      label="Категорія CPV"
                      placeholder="Оберіть CPV"
                      required
                      :selected-ids="form.cpv_ids"
                      :selected-labels="createCpvLabels"
                      @update:selected-ids="form.cpv_ids = $event"
                      @update:selected-labels="createCpvLabels = $event"
                    />
                  </div>
                </div>

                <div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ContentSearch
                      label="Стаття бюджету"
                      :required="isExpenseArticleRequired"
                      placeholder="Оберіть статтю"
                      search-placeholder="Пошук статті бюджету"
                      :tree="expenseTree"
                      :selected-ids="selectedExpenseIds"
                      :search-term="expenseSearch"
                      :disabled-ids="expenseDisabledIds"
                      @toggle="toggleExpense"
                      @update:search-term="expenseSearch = $event"
                    />
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <UFormField label="Орієнтовний бюджет">
                        <UInput
                          v-model.number="form.estimated_budget"
                          type="number"
                          step="0.0001"
                          placeholder="0"
                          size="sm"
                          class="w-full"
                        />
                      </UFormField>
                      <UFormField label="Валюта" required>
                        <USelectMenu
                          v-model="form.currency"
                          :items="currencyOptions"
                          value-key="value"
                          placeholder="Валюту"
                          size="sm"
                          class="w-full"
                        />
                      </UFormField>
                    </div>
                  </div>
                </div>

                <div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ContentSearch
                      label="Філіал"
                      :required="isBranchRequired"
                      placeholder="Оберіть філіал"
                      search-placeholder="Пошук філіалу"
                      :tree="branchTree"
                      :selected-ids="selectedBranchIds"
                      :search-term="branchSearch"
                      :disabled-ids="branchDisabledIds"
                      @toggle="toggleBranch"
                      @update:search-term="branchSearch = $event"
                    />
                    <ContentSearch
                      label="Підрозділ"
                      placeholder="Оберіть підрозділ"
                      search-placeholder="Пошук підрозділу"
                      :disabled="!form.branch"
                      :tree="departmentTree"
                      :selected-ids="selectedDepartmentIds"
                      :search-term="departmentSearch"
                      :disabled-ids="departmentDisabledIds"
                      @toggle="toggleDepartment"
                      @update:search-term="departmentSearch = $event"
                    />
                  </div>
                </div>

                <div>
                  <div class="grid grid-cols-2 md:grid-cols-2 gap-4">
                    <UFormField label="Тип проведення" required>
                      <USelectMenu
                        v-model="form.conduct_type"
                        :items="conductTypeOptions"
                        value-key="value"
                        placeholder="Оберіть тип"
                        size="sm"
                        class="w-full"
                      />
                    </UFormField>
                    <UFormField label="Тип публікації" required>
                      <USelectMenu
                        v-model="form.publication_type"
                        :items="publicationTypeOptions"
                        value-key="value"
                        placeholder="Оберіть тип"
                        size="sm"
                        class="w-full"
                      />
                    </UFormField>
                    <div class="grid grid-cols-1 md:grid-cols-1 gap-4">
                      <UFormField
                        label="Модель погодження"
                        :required="isApprovalModelRequired"
                      >
                        <USelectMenu
                          v-model="form.approval_model_id"
                          :items="approvalModelOptions"
                          value-key="value"
                          placeholder="Оберіть модель"
                          size="sm"
                          class="w-full"
                          :disabled="!isApprovalModelLookupReady"
                        />
                      </UFormField>
                    </div>
                  </div>
                </div>
              </div>

              <div
                class="border-t border-gray-200 pt-5 lg:border-t-0 lg:border-l lg:border-gray-200 lg:pt-0 lg:pl-6 flex flex-col min-h-[320px]"
              >
                <div class="mb-6">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <UFormField label="Орієнтовна дата прийому пропозицій">
                      <div class="grid grid-cols-[1fr_auto] gap-2">
                        <DateValuePicker
                          :model-value="plannedStartDate"
                          @update:model-value="plannedStartDate = $event || ''"
                        />
                        <UInput
                          v-model="plannedStartTime"
                          placeholder="ГГ:ХХ"
                          inputmode="numeric"
                          maxlength="5"
                          class="w-24"
                          @update:model-value="
                            plannedStartTime = formatTimeInput($event)
                          "
                        />
                      </div>
                    </UFormField>
                    <UFormField label="Орієнтовна дата та час завершення">
                      <div class="grid grid-cols-[1fr_auto] gap-2">
                        <DateValuePicker
                          :model-value="plannedEndDate"
                          @update:model-value="plannedEndDate = $event || ''"
                        />
                        <UInput
                          v-model="plannedEndTime"
                          placeholder="ГГ:ХХ"
                          inputmode="numeric"
                          maxlength="5"
                          class="w-24"
                          @update:model-value="
                            plannedEndTime = formatTimeInput($event)
                          "
                        />
                      </div>
                    </UFormField>
                  </div>
                </div>
                <UFormField
                  label="Опис умов та вимог"
                  class="mb-0 flex-1 flex flex-col min-h-0"
                >
                  <div class="mb-2">
                    <UButton
                      size="sm"
                      variant="outline"
                      icon="i-heroicons-document-text"
                      @click="openConditionTemplateModal"
                    >
                      Обрати шаблон
                    </UButton>
                  </div>
                  <div
                    class="general-terms-editor-wrapper flex flex-col min-h-[320px] rounded-md border border-gray-200 bg-white overflow-hidden"
                  >
                    <UEditor
                      v-slot="{ editor }"
                      v-model="form.general_terms"
                      content-type="html"
                      :extensions="[
                        TextAlign.configure({
                          types: ['heading', 'paragraph'],
                        }),
                      ]"
                      placeholder="Опишіть загальні умови, вимоги до учасників, порядок оцінки пропозицій тощо. Цей текст буде доступний учасникам."
                      :ui="{
                        root: 'flex flex-col min-h-[300px]',
                        content: 'flex-1 min-h-[260px] flex flex-col',
                        base: 'min-h-[260px] outline-none py-2 px-3 cursor-text',
                      }"
                      class="w-full"
                    >
                      <UEditorToolbar
                        :editor="editor"
                        :items="generalTermsEditorToolbarItems"
                        class="border-b border-gray-200 px-2 py-1 flex-shrink-0"
                      />
                    </UEditor>
                  </div>
                </UFormField>
              </div>
            </div>
          </UForm>
        </UCard>
      </div>

      <aside
        class="w-56 flex-shrink-0 space-y-3 rounded-xl border border-gray-200 bg-white shadow-sm p-3"
      >
        <UButton class="w-full" :loading="saving" @click="saveTender"
          >Зберегти</UButton
        >
        <UButton class="w-full" variant="outline" @click="goBack"
          >Скасувати</UButton
        >
      </aside>
    </div>
    <UModal v-model:open="showConditionTemplateModal">
      <template #content>
        <UCard>
          <template #header><h3>Шаблони умов</h3></template>
          <div class="space-y-3">
            <div
              v-if="conditionTemplatesLoading"
              class="py-8 text-center text-sm text-gray-500"
            >
              Завантаження шаблонів...
            </div>
            <div
              v-else-if="!conditionTemplates.length"
              class="py-8 text-center text-sm text-gray-500"
            >
              Немає доступних шаблонів умов.
            </div>
            <div v-else class="max-h-[60vh] overflow-auto space-y-2">
              <UButton
                v-for="templateItem in conditionTemplates"
                :key="templateItem.id"
                class="w-full justify-start"
                variant="outline"
                color="neutral"
                @click="applyConditionTemplate(templateItem)"
              >
                {{ templateItem.name }}
              </UButton>
            </div>
            <div class="flex justify-end">
              <UButton
                variant="outline"
                @click="showConditionTemplateModal = false"
              >
                Закрити
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { TextAlign } from "@tiptap/extension-text-align";
import { TENDER_STAGE_ITEMS } from "~/domains/tenders/tenders.constants";
import type { TenderConditionTemplate } from "~/domains/tenders/tenders.types";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Створення тендера" },
});

const route = useRoute();
const isSales = computed(
  () => String(route.params.type || "").toLowerCase() === "sales",
);
const isRegistrationMode = computed(
  () => String(route.query.mode || "").toLowerCase() === "registration",
);
const pageTitle = computed(() =>
  isRegistrationMode.value
    ? isSales.value
      ? "Реєстрація продажу"
      : "Реєстрація закупівлі"
    : "Створення тендера",
);

// Динамічно оновлюємо title сторінки
const passportTitle = computed(() =>
  isSales.value ? "Паспорт тендера продажу" : "Паспорт тендера закупівлі",
);

useHead({
  title: pageTitle,
});

const listView = computed(() => (isSales.value ? "sales" : "purchase"));

const { me } = useMe();
const tendersUC = useTendersUseCases();
const toast = useToast();

const saving = ref(false);
const categorySearch = ref("");
const expenseSearch = ref("");
const branchSearch = ref("");
const departmentSearch = ref("");
const showConditionTemplateModal = ref(false);
const conditionTemplatesLoading = ref(false);
const conditionTemplates = ref<TenderConditionTemplate[]>([]);

const stepperItems = computed(() => {
  const base =
    // Для будь-якого mode=registration ховаємо етап "Прийом пропозицій"
    isRegistrationMode.value
      ? TENDER_STAGE_ITEMS.filter((s) => s.value !== "acceptance")
      : TENDER_STAGE_ITEMS;
  return base.map((s) => ({
    ...s,
    description: "",
  }));
});
const currentStepValue = ref("passport");

const createCpvLabels = ref<string[]>([]);
const form = reactive({
  name: "",
  category: undefined as number | undefined,
  cpv_ids: [] as number[],
  expense_article: undefined as number | undefined,
  estimated_budget: undefined as number | undefined,
  branch: undefined as number | undefined,
  department: undefined as number | undefined,
  conduct_type: "rfx",
  auction_model: "classic_auction",
  publication_type: "open",
  currency: undefined as number | undefined,
  general_terms: "",
  approval_model_id: null as number | null,
});
const plannedStartDate = ref("");
const plannedEndDate = ref("");
const plannedStartTime = ref("");
const plannedEndTime = ref("");

const selectedCategoryIds = computed(() =>
  form.category ? [form.category] : [],
);
const selectedExpenseIds = computed(() =>
  form.expense_article ? [form.expense_article] : [],
);
const selectedBranchIds = computed(() => (form.branch ? [form.branch] : []));
const selectedDepartmentIds = computed(() =>
  form.department ? [form.department] : [],
);

const conductTypeOptions = computed(() => {
  if (isRegistrationMode.value) {
    return [
      {
        value: "registration",
        label: isSales.value ? "Реєстрація продажу" : "Реєстрація закупівлі",
      },
    ];
  }
  // Створення нового тендера (перший тур): тільки Збір пропозицій та Онлайн торги
  return [
    { value: "rfx", label: "Збір пропозицій (RFx)" },
    { value: "online_auction", label: "Онлайн торги" },
  ];
});
const publicationTypeOptions = [
  { value: "open", label: "Відкрита процедура" },
  { value: "closed", label: "Закрита процедура" },
];

const generalTermsEditorToolbarItems = [
  [
    { kind: "mark", mark: "bold", icon: "i-lucide-bold" },
    { kind: "mark", mark: "italic", icon: "i-lucide-italic" },
    { kind: "mark", mark: "underline", icon: "i-lucide-underline" },
  ],
  [
    {
      icon: "i-lucide-list",
      tooltip: { text: "Lists" },
      content: { align: "start" },
      items: [
        { kind: "bulletList", icon: "i-lucide-list", label: "Bullet List" },
        {
          kind: "orderedList",
          icon: "i-lucide-list-ordered",
          label: "Ordered List",
        },
      ],
    },
  ],
  [
    {
      icon: "i-lucide-align-justify",
      tooltip: { text: "Text Align" },
      content: { align: "end" },
      items: [
        {
          kind: "textAlign",
          align: "left",
          icon: "i-lucide-align-left",
          label: "Align Left",
        },
        {
          kind: "textAlign",
          align: "center",
          icon: "i-lucide-align-center",
          label: "Align Center",
        },
        {
          kind: "textAlign",
          align: "right",
          icon: "i-lucide-align-right",
          label: "Align Right",
        },
        {
          kind: "textAlign",
          align: "justify",
          icon: "i-lucide-align-justify",
          label: "Align Justify",
        },
      ],
    },
  ],
];

const categoryTree = ref<any[]>([]);
const expenseTree = ref<any[]>([]);
const branchTree = ref<any[]>([]);
const departmentsByBranch = ref<Record<number, any[]>>({});
const departmentTree = computed(() => {
  const branchId = Number(form.branch || 0);
  if (!Number.isInteger(branchId) || branchId <= 0) return [];
  return departmentsByBranch.value[branchId] || [];
});
const currencyOptions = ref<{ value: number; label: string }[]>([]);
const categoryDisabledIds = computed(() => collectDisabledTreeIds(categoryTree.value));
const expenseDisabledIds = computed(() => collectDisabledTreeIds(expenseTree.value));
const branchDisabledIds = computed(() => collectDisabledTreeIds(branchTree.value));
const departmentDisabledIds = computed(() =>
  collectDisabledTreeIds(departmentTree.value),
);
const isExpenseArticleRequired = computed(
  () => countSelectableTreeNodes(expenseTree.value) > 0,
);
const isBranchRequired = computed(() => countSelectableTreeNodes(branchTree.value) > 0);
const isDepartmentRequired = computed(() => false);
const availableApprovalModels = ref<any[]>([]);
let approvalModelsDebounceTimer: ReturnType<typeof setTimeout> | null = null;
const approvalModelOptions = computed(() =>
  availableApprovalModels.value.map((m: any) => ({
    value: Number(m.id),
    label: m.name || `#${m.id}`,
  })),
);
const isApprovalModelLookupReady = computed(() => {
  const categoryId = Number(form.category || 0);
  const hasCategory = Number.isInteger(categoryId) && categoryId > 0;
  const budgetRaw = form.estimated_budget;
  const hasBudget = budgetRaw != null && Number.isFinite(Number(budgetRaw));
  return hasCategory && hasBudget;
});
const isApprovalModelRequired = computed(
  () =>
    isApprovalModelLookupReady.value && approvalModelOptions.value.length > 0,
);

// Ініціалізація типу проведення за режимом
if (isRegistrationMode.value) {
  form.conduct_type = "registration";
} else {
  form.conduct_type = "rfx";
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

function findTreeNodeById(items: any[], id: number): any | null {
  for (const item of items || []) {
    if (Number(item?.id) === Number(id)) return item;
    if (item?.children?.length) {
      const found = findTreeNodeById(item.children, id);
      if (found) return found;
    }
  }
  return null;
}

function collectDisabledTreeIds(items: any[]): number[] {
  const out: number[] = [];
  const walk = (nodes: any[]) => {
    for (const node of nodes || []) {
      if (node?.is_directly_assigned === false) out.push(Number(node.id));
      if (node?.children?.length) walk(node.children);
    }
  };
  walk(items);
  return out;
}

function countSelectableTreeNodes(items: any[]): number {
  let count = 0;
  const walk = (nodes: any[]) => {
    for (const node of nodes || []) {
      if (node?.is_directly_assigned !== false) count += 1;
      if (node?.children?.length) walk(node.children);
    }
  };
  walk(items);
  return count;
}

function findCategoryById(items: any[], id: number): any | null {
  return findTreeNodeById(items, id);
}

function applyCategoryCpvs(categoryId: number | undefined) {
  if (!categoryId) return;
  const category = findCategoryById(categoryTree.value, categoryId);
  const cpvs = Array.isArray(category?.cpvs) ? category.cpvs : [];
  form.cpv_ids = cpvs
    .map((c: any) => Number(c?.id))
    .filter((id: number) => Number.isFinite(id));
  createCpvLabels.value = cpvs
    .map(
      (c: any) =>
        c?.label || `${c?.cpv_code || ""} - ${c?.name_ua || ""}`.trim(),
    )
    .filter((label: string) => !!label);
}

function toggleCategory(id: number) {
  form.category = form.category === id ? undefined : id;
  if (form.category) {
    applyCategoryCpvs(form.category);
  }
}

function toggleExpense(id: number) {
  form.expense_article = form.expense_article === id ? undefined : id;
}

async function ensureDepartmentsLoaded(branchId?: number) {
  const normalizedBranchId = Number(branchId || 0);
  if (!Number.isInteger(normalizedBranchId) || normalizedBranchId <= 0) return;
  if (departmentsByBranch.value[normalizedBranchId]) return;

  const { data } = await tendersUC.getDepartments(normalizedBranchId);
  departmentsByBranch.value = {
    ...departmentsByBranch.value,
    [normalizedBranchId]: Array.isArray(data) ? data : [],
  };
}

async function toggleBranch(id: number) {
  form.branch = form.branch === id ? undefined : id;
  departmentSearch.value = "";
  if (!form.branch) {
    form.department = undefined;
    return;
  }

  await ensureDepartmentsLoaded(form.branch);

  const selectedDepartment = form.department
    ? findTreeNodeById(departmentTree.value, form.department)
    : null;
  if (!selectedDepartment) {
    form.department = undefined;
  }
}

function toggleDepartment(id: number) {
  if (!form.branch) return;
  form.department = form.department === id ? undefined : id;
  if (!form.department) return;

  const selectedDepartment = findTreeNodeById(departmentTree.value, form.department);
  if (!selectedDepartment) {
    form.department = undefined;
  }
}

async function ensureConditionTemplatesLoaded() {
  const companyId = Number(
    (me.value as any)?.memberships?.[0]?.company?.id || 0,
  );
  if (!companyId) return;
  conditionTemplatesLoading.value = true;
  try {
    const { data } = await tendersUC.getTenderConditionTemplates(companyId);
    conditionTemplates.value = Array.isArray(data) ? data : [];
  } finally {
    conditionTemplatesLoading.value = false;
  }
}

async function openConditionTemplateModal() {
  await ensureConditionTemplatesLoaded();
  showConditionTemplateModal.value = true;
}

function applyConditionTemplate(templateItem: TenderConditionTemplate) {
  form.general_terms = String(templateItem.content || "");
  showConditionTemplateModal.value = false;
}

async function loadOptions() {
  const [cats, expenses, branches, currencies] = await Promise.all([
    tendersUC.getCategories(),
    tendersUC.getExpenses(),
    tendersUC.getBranches(),
    tendersUC.getCurrencies(),
  ]);

  categoryTree.value = (cats.data as any[]) || [];
  expenseTree.value = (expenses.data as any[]) || [];
  branchTree.value = (branches.data as any[]) || [];
  const rawCurrencies = (currencies.data as any[]) || [];
  currencyOptions.value = rawCurrencies.map((c: any) => ({
    value: c.id,
    label: String(c.code || ""),
  }));

  if (!form.currency && currencyOptions.value.length) {
    const preferredCurrency = rawCurrencies.find(
      (currency: any) => String(currency?.code || "").toUpperCase() === "UAH",
    );
    const preferredCurrencyId = Number(preferredCurrency?.id);
    if (Number.isInteger(preferredCurrencyId) && preferredCurrencyId > 0) {
      form.currency = preferredCurrencyId;
    } else {
      const firstCurrency = currencyOptions.value[0];
      if (firstCurrency) form.currency = firstCurrency.value;
    }
  }
}

async function loadAvailableApprovalModels() {
  const companyId = Number(
    (me.value as any)?.memberships?.[0]?.company?.id || 0,
  );
  if (!companyId || !isApprovalModelLookupReady.value) {
    availableApprovalModels.value = [];
    form.approval_model_id = null;
    return;
  }
  const { data } = await tendersUC.getAvailableApprovalModels({
    companyId,
    application: isSales.value ? "sales" : "procurement",
    categoryId: form.category ?? null,
    estimatedBudget:
      form.estimated_budget != null ? Number(form.estimated_budget) : null,
  });
  availableApprovalModels.value = Array.isArray(data) ? data : [];
  if (
    form.approval_model_id != null &&
    !availableApprovalModels.value.some(
      (m: any) => Number(m.id) === Number(form.approval_model_id),
    )
  ) {
    form.approval_model_id = null;
  }
}

function inputToIso(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function normalizeDateValue(value?: string | null): string {
  const raw = String(value || "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  return "";
}

function normalizeTimeValue(value?: string | null): string {
  const raw = String(value || "").trim();
  const parsed = raw.match(/^(\d{1,2}):(\d{1,2})$/);
  if (!parsed) return "";
  const hours = Number(parsed[1]);
  const minutes = Number(parsed[2]);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return "";
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}`;
}

function formatTimeInput(value: string | number | null | undefined): string {
  const raw = String(value ?? "").replace(/[^\d:]/g, "");
  if (!raw) return "";

  const normalizeHours = (input: string): string => {
    if (!input) return "";
    const parsed = Number(input);
    if (!Number.isFinite(parsed)) return "";
    const bounded = Math.max(0, Math.min(23, parsed));
    return input.length >= 2
      ? String(bounded).padStart(2, "0")
      : String(bounded);
  };
  const normalizeMinutes = (input: string): string => {
    if (!input) return "";
    const parsed = Number(input);
    if (!Number.isFinite(parsed)) return "";
    const bounded = Math.max(0, Math.min(59, parsed));
    return input.length >= 2
      ? String(bounded).padStart(2, "0")
      : String(bounded);
  };

  if (raw.includes(":")) {
    const colonIndex = raw.indexOf(":");
    const hoursInput = raw.slice(0, colonIndex).replace(/\D/g, "").slice(0, 2);
    const minutesInput = raw
      .slice(colonIndex + 1)
      .replace(/\D/g, "")
      .slice(0, 2);
    if (!hoursInput) return "";
    const hours = normalizeHours(hoursInput);
    if (raw.endsWith(":") && !minutesInput) return `${hours}:`;
    const minutes = normalizeMinutes(minutesInput);
    return `${hours}:${minutes}`;
  }

  const digits = raw.replace(/\D/g, "").slice(0, 4);
  if (!digits) return "";
  if (digits.length <= 2) {
    const hours = normalizeHours(digits);
    return `${hours}${digits.length === 2 ? ":" : ""}`;
  }
  if (digits.length === 3) {
    const hours = normalizeHours(digits.slice(0, 1));
    const minutes = normalizeMinutes(digits.slice(1, 3));
    return `${hours}:${minutes}`;
  }
  const hours = normalizeHours(digits.slice(0, 2));
  const minutes = normalizeMinutes(digits.slice(2, 4));
  return `${hours}:${minutes}`;
}

function buildDateTimeInput(dateValue: string, timeValue: string): string {
  const normalizedDate = normalizeDateValue(dateValue);
  const normalizedTime = normalizeTimeValue(timeValue);
  if (!normalizedDate || !normalizedTime) return "";
  return `${normalizedDate}T${normalizedTime}`;
}

async function saveTender() {
  if (!form.name.trim()) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Вкажіть назву тендера.",
      color: "error",
    });
    return;
  }
  if (!form.currency) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть валюту тендера.",
      color: "error",
    });
    return;
  }

  const companyId = (me.value as any)?.memberships?.[0]?.company?.id ?? null;
  if (!companyId) {
    const { logout } = useAuth();
    logout();
    return;
  }

  const cpvIds = form.cpv_ids ?? [];
  if (cpvIds.length === 0) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть хоча б одну категорію CPV.",
      color: "error",
    });
    return;
  }
  if (isApprovalModelRequired.value && !form.approval_model_id) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть модель погодження.",
      color: "error",
    });
    return;
  }
  if (isExpenseArticleRequired.value && !form.expense_article) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть статтю бюджету.",
      color: "error",
    });
    return;
  }
  if (isBranchRequired.value && !form.branch) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть філіал.",
      color: "error",
    });
    return;
  }
  if (isDepartmentRequired.value && !form.department) {
    toast.add({
      title: "Заповніть обов'язкове поле",
      description: "Оберіть підрозділ.",
      color: "error",
    });
    return;
  }

  saving.value = true;
  try {
    const plannedStart = buildDateTimeInput(
      plannedStartDate.value,
      plannedStartTime.value,
    );
    const plannedEnd = buildDateTimeInput(
      plannedEndDate.value,
      plannedEndTime.value,
    );
    const { data: created, error: createError } = await tendersUC.createTender(
      isSales.value,
      {
        company: companyId,
        name: form.name.trim(),
        stage: "preparation",
        category: form.category,
        cpv_ids: form.cpv_ids,
        expense_article: form.expense_article,
        estimated_budget: form.estimated_budget,
        branch: form.branch,
        department: form.department,
        conduct_type: form.conduct_type,
        auction_model: form.auction_model,
        publication_type: form.publication_type,
        currency: form.currency,
        general_terms: form.general_terms,
        approval_model_id: form.approval_model_id,
        planned_start_at: plannedStart ? inputToIso(plannedStart) : null,
        planned_end_at: plannedEnd ? inputToIso(plannedEnd) : null,
      },
    );

    if (createError || !created?.id) {
      toast.add({
        title: "Помилка створення тендера",
        description:
          typeof createError === "string"
            ? createError
            : "Перевірте заповнення полів та спробуйте ще раз.",
        color: "error",
      });
      return;
    }

    const detailUrl = isSales.value
      ? `/cabinet/tenders/sales/${created.id}`
      : `/cabinet/tenders/${created.id}`;
    await navigateTo(detailUrl, { replace: true });
  } finally {
    saving.value = false;
  }
}

function goBack() {
  navigateTo(`/cabinet/tenders?view=${listView.value}`);
}

onMounted(async () => {
  await loadOptions();
  await loadAvailableApprovalModels();
});

watch(
  () => [
    form.category,
    form.estimated_budget,
    isSales.value,
    (me.value as any)?.memberships?.[0]?.company?.id,
  ],
  () => {
    if (approvalModelsDebounceTimer) {
      clearTimeout(approvalModelsDebounceTimer);
    }
    approvalModelsDebounceTimer = setTimeout(() => {
      void loadAvailableApprovalModels();
    }, 250);
  },
);

onUnmounted(() => {
  if (approvalModelsDebounceTimer) {
    clearTimeout(approvalModelsDebounceTimer);
    approvalModelsDebounceTimer = null;
  }
});
</script>

<style scoped>
/* Компактний степер — такий самий вигляд, як на сторінці тендера [id] */
.tender-stepper--compact :deep([data-slot="header"]) {
  gap: 0.25rem;
}
.tender-stepper--compact :deep([data-slot="indicator"]) {
  width: 1.75rem;
  height: 1.75rem;
  font-size: 0.75rem;
}
.tender-stepper--compact :deep([data-slot="title"]) {
  font-size: 0.8125rem;
}
.tender-stepper--compact :deep([data-slot="wrapper"]) {
  min-height: auto;
}

/* Редактор «Опис умов та вимог»: плейсхолдер зникає при фокусі, вся область клікабельна */
.general-terms-editor-wrapper:focus-within
  :deep(.ProseMirror p.is-empty::before) {
  opacity: 0;
}
.general-terms-editor-wrapper :deep(.ProseMirror.is-editor-empty:focus::before),
.general-terms-editor-wrapper
  :deep(.ProseMirror p.is-empty:first-child:focus::before) {
  opacity: 0;
}
</style>
