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
      <div class="flex-1 min-w-0 overflow-y-auto">
        <UCard class="overflow-hidden">
          <template #header>
            <h3 class="text-lg font-semibold text-gray-900">{{ passportTitle }}</h3>
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
                  <p
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                  >
                    Категорізація
                  </p>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    <CpvTenderModalSelect
                      label="Категорія CPV"
                      placeholder="Оберіть CPV"
                      required
                      :disabled="!!form.category"
                      :selected-ids="form.cpv_ids"
                      :selected-labels="createCpvLabels"
                      @update:selected-ids="form.cpv_ids = $event"
                      @update:selected-labels="createCpvLabels = $event"
                    />
                  </div>
                </div>

                <div>
                  <p
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                  >
                    Бюджет і валюта
                  </p>
                  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <UFormField label="Стаття бюджету">
                      <USelectMenu
                        v-model="form.expense_article"
                        :items="expenseOptions"
                        value-key="value"
                        placeholder="Оберіть статтю"
                        size="sm"
                      />
                    </UFormField>
                    <UFormField label="Орієнтовний бюджет">
                      <UInput
                        v-model.number="form.estimated_budget"
                        type="number"
                        step="0.01"
                        placeholder="0"
                        size="sm"
                      />
                    </UFormField>
                    <UFormField label="Валюта" required>
                      <USelectMenu
                        v-model="form.currency"
                        :items="currencyOptions"
                        value-key="value"
                        placeholder="Валюту"
                        size="sm"
                      />
                    </UFormField>
                  </div>
                </div>

                <div>
                  <p
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                  >
                    Організаційна структура
                  </p>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <UFormField label="Філіал">
                      <USelectMenu
                        v-model="form.branch"
                        :items="branchOptions"
                        value-key="value"
                        placeholder="Оберіть філіал"
                        size="sm"
                        @update:model-value="onBranchChange"
                      />
                    </UFormField>
                    <UFormField label="Підрозділ">
                      <USelectMenu
                        v-model="form.department"
                        :items="departmentOptions"
                        value-key="value"
                        placeholder="Оберіть підрозділ"
                        size="sm"
                      />
                    </UFormField>
                  </div>
                </div>

                <div>
                  <p
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                  >
                    Параметри процедури
                  </p>
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <UFormField label="Тип проведення" required>
                      <USelectMenu
                        v-model="form.conduct_type"
                        :items="conductTypeOptions"
                        value-key="value"
                        placeholder="Оберіть тип"
                        size="sm"
                      />
                    </UFormField>
                    <UFormField label="Тип публікації" required>
                      <USelectMenu
                        v-model="form.publication_type"
                        :items="publicationTypeOptions"
                        value-key="value"
                        placeholder="Оберіть тип"
                        size="sm"
                      />
                    </UFormField>
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
                        :disabled="!isApprovalModelLookupReady"
                      />
                    </UFormField>
                  </div>
                </div>
              </div>

              <div
                class="border-t border-gray-200 pt-5 lg:border-t-0 lg:border-l lg:border-gray-200 lg:pt-0 lg:pl-6 flex flex-col min-h-[320px]"
              >
                <p
                  class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                >
                  Загальні умови проведення тендера
                </p>
                <UFormField
                  label="Опис умов та вимог"
                  class="mb-0 flex-1 flex flex-col min-h-0"
                >
                  <div
                    class="general-terms-editor-wrapper flex flex-col min-h-[320px] rounded-md border border-gray-200 bg-white overflow-hidden"
                  >
                    <UEditor
                      v-slot="{ editor }"
                      v-model="form.general_terms"
                      content-type="html"
                      :extensions="[TextAlign.configure({ types: ['heading', 'paragraph'] })]"
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

      <aside class="w-56 flex-shrink-0 space-y-3">
        <UButton class="w-full" :loading="saving" @click="saveTender"
          >Зберегти</UButton
        >
        <UButton class="w-full" variant="outline" @click="goBack"
          >Скасувати</UButton
        >
      </aside>
    </div>
    <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { TextAlign } from "@tiptap/extension-text-align";
import { TENDER_STAGE_ITEMS } from "~/domains/tenders/tenders.constants";

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

const saving = ref(false);
const error = ref("");
const categorySearch = ref("");

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
  publication_type: "open",
  currency: undefined as number | undefined,
  general_terms: "",
  approval_model_id: null as number | null,
});

const selectedCategoryIds = computed(() =>
  form.category ? [form.category] : [],
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
        { kind: "orderedList", icon: "i-lucide-list-ordered", label: "Ordered List" },
      ],
    },
  ],
  [
    {
      icon: "i-lucide-align-justify",
      tooltip: { text: "Text Align" },
      content: { align: "end" },
      items: [
        { kind: "textAlign", align: "left", icon: "i-lucide-align-left", label: "Align Left" },
        { kind: "textAlign", align: "center", icon: "i-lucide-align-center", label: "Align Center" },
        { kind: "textAlign", align: "right", icon: "i-lucide-align-right", label: "Align Right" },
        { kind: "textAlign", align: "justify", icon: "i-lucide-align-justify", label: "Align Justify" },
      ],
    },
  ],
];

const categoryTree = ref<any[]>([]);
const expenseOptions = ref<{ value: number; label: string }[]>([]);
const branchOptions = ref<{ value: number; label: string }[]>([]);
const departmentOptions = ref<{ value: number; label: string }[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);
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
  const hasBudget =
    budgetRaw != null && Number.isFinite(Number(budgetRaw));
  return hasCategory && hasBudget;
});
const isApprovalModelRequired = computed(
  () =>
    isApprovalModelLookupReady.value &&
    approvalModelOptions.value.length > 0,
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

function findCategoryById(items: any[], id: number): any | null {
  for (const item of items || []) {
    if (Number(item?.id) === Number(id)) return item;
    if (item?.children?.length) {
      const found = findCategoryById(item.children, id);
      if (found) return found;
    }
  }
  return null;
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
  } else {
    form.cpv_ids = [];
    createCpvLabels.value = [];
  }
}

async function loadOptions() {
  const [cats, expenses, branches, currencies] = await Promise.all([
    tendersUC.getCategories(),
    tendersUC.getExpenses(),
    tendersUC.getBranches(),
    tendersUC.getCurrencies(),
  ]);

  categoryTree.value = (cats.data as any[]) || [];
  expenseOptions.value = flattenTree((expenses.data as any[]) || []);
  branchOptions.value = flattenTree((branches.data as any[]) || []);
  currencyOptions.value = ((currencies.data as any[]) || []).map((c: any) => ({
    value: c.id,
    label: `${c.code} - ${c.name}`,
  }));

  if (!form.currency && currencyOptions.value.length) {
    const firstCurrency = currencyOptions.value[0];
    if (firstCurrency) form.currency = firstCurrency.value;
  }
}

async function loadAvailableApprovalModels() {
  const companyId = Number((me.value as any)?.memberships?.[0]?.company?.id || 0);
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

async function loadDepartments() {
  if (!form.branch) {
    departmentOptions.value = [];
    return;
  }
  const { data } = await tendersUC.getDepartments(form.branch);
  departmentOptions.value = flattenTree((data as any[]) || []);
}

function onBranchChange() {
  form.department = undefined;
  loadDepartments();
}

async function saveTender() {
  if (!form.name.trim()) {
    error.value = "Вкажіть назву тендера.";
    return;
  }
  if (!form.currency) {
    error.value = "Оберіть валюту тендера.";
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
    error.value = "Оберіть хоча б одну категорію CPV.";
    return;
  }
  if (isApprovalModelRequired.value && !form.approval_model_id) {
    error.value = "Оберіть модель погодження.";
    return;
  }

  saving.value = true;
  error.value = "";
  try {
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
        publication_type: form.publication_type,
        currency: form.currency,
        general_terms: form.general_terms,
        approval_model_id: form.approval_model_id,
      },
    );

    if (createError || !created?.id) {
      error.value =
        typeof createError === "string"
          ? createError
          : "Помилка створення тендера.";
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
  () => [form.category, form.estimated_budget, isSales.value, (me.value as any)?.memberships?.[0]?.company?.id],
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
.general-terms-editor-wrapper:focus-within :deep(.ProseMirror p.is-empty::before) {
  opacity: 0;
}
.general-terms-editor-wrapper :deep(.ProseMirror.is-editor-empty:focus::before),
.general-terms-editor-wrapper :deep(.ProseMirror p.is-empty:first-child:focus::before) {
  opacity: 0;
}
</style>
