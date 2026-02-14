<template>
  <div class="h-full flex flex-col">
    <UStepper v-model="currentStepValue" :items="stepperItems" value-key="value" class="mb-6" :disabled="true" />
    <div class="flex flex-1 min-h-0 gap-6">
      <div class="flex-1 min-w-0 overflow-y-auto">
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
              :selected-labels="createCpvLabels"
              @update:selected-ids="form.cpv_ids = $event"
              @update:selected-labels="createCpvLabels = $event"
            />

            <UFormField label="Стаття бюджету">
              <USelectMenu v-model="form.expense_article" :items="expenseOptions" value-key="value" placeholder="Оберіть статтю" />
            </UFormField>
            <UFormField label="Орієнтовний бюджет">
              <UInput v-model.number="form.estimated_budget" type="number" step="0.01" placeholder="0" />
            </UFormField>
            <UFormField label="Філіал">
              <USelectMenu v-model="form.branch" :items="branchOptions" value-key="value" placeholder="Оберіть філіал" @update:model-value="onBranchChange" />
            </UFormField>
            <UFormField label="Підрозділ">
              <USelectMenu v-model="form.department" :items="departmentOptions" value-key="value" placeholder="Оберіть підрозділ" />
            </UFormField>
            <UFormField label="Тип проведення" required>
              <USelectMenu v-model="form.conduct_type" :items="conductTypeOptions" value-key="value" placeholder="Оберіть тип" />
            </UFormField>
            <UFormField label="Тип публікації" required>
              <USelectMenu v-model="form.publication_type" :items="publicationTypeOptions" value-key="value" placeholder="Оберіть тип" />
            </UFormField>
            <UFormField label="Валюта тендера" required>
              <USelectMenu v-model="form.currency" :items="currencyOptions" value-key="value" placeholder="Оберіть валюту" />
            </UFormField>
            <UFormField label="Загальні умови">
              <UTextarea v-model="form.general_terms" :rows="6" placeholder="Опис загальних умов" />
            </UFormField>
          </UForm>
        </UCard>
      </div>

      <aside class="w-56 flex-shrink-0 space-y-3">
        <UButton class="w-full" :loading="saving" @click="saveTender">Зберегти</UButton>
        <UButton class="w-full" variant="outline" @click="goBack">Скасувати</UButton>
      </aside>
    </div>
    <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Створення процедури" },
});

const route = useRoute();
const isSales = computed(() => String(route.params.type || "").toLowerCase() === "sales");
const listView = computed(() => (isSales.value ? "sales" : "purchase"));

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const saving = ref(false);
const error = ref("");
const categorySearch = ref("");

const stageItems = [
  { value: "passport", title: "Паспорт тендера" },
  { value: "preparation", title: "Підготовка процедури" },
  { value: "acceptance", title: "Прийом пропозицій" },
  { value: "decision", title: "Вибір рішення" },
  { value: "approval", title: "Затвердження" },
  { value: "completed", title: "Завершений" },
];
const stepperItems = stageItems.map((s) => ({ ...s, description: "" }));
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
});

const selectedCategoryIds = computed(() => (form.category ? [form.category] : []));

const conductTypeOptions = computed(() => [
  { value: "registration", label: isSales.value ? "Реєстрація продажу" : "Реєстрація закупівлі" },
  { value: "rfx", label: "Збір пропозицій (RFx)" },
  { value: "online_auction", label: "Онлайн торги" },
]);
const publicationTypeOptions = [
  { value: "open", label: "Відкрита процедура" },
  { value: "closed", label: "Закрита процедура" },
];

const categoryTree = ref<any[]>([]);
const expenseOptions = ref<{ value: number; label: string }[]>([]);
const branchOptions = ref<{ value: number; label: string }[]>([]);
const departmentOptions = ref<{ value: number; label: string }[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);

function flattenTree(items: any[], level = 0): { value: number; label: string }[] {
  const out: { value: number; label: string }[] = [];
  for (const item of items || []) {
    out.push({ value: item.id, label: `${"  ".repeat(level)}${item.name || item.label}` });
    if (item.children?.length) out.push(...flattenTree(item.children, level + 1));
  }
  return out;
}

function toggleCategory(id: number) {
  form.category = form.category === id ? undefined : id;
  if (form.category) {
    form.cpv_ids = [];
    createCpvLabels.value = [];
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
  currencyOptions.value = ((currencies.data as any[]) || []).map((c: any) => ({ value: c.id, label: `${c.code} - ${c.name}` }));

  if (!form.currency && currencyOptions.value.length) {
    const firstCurrency = currencyOptions.value[0];
    if (firstCurrency) form.currency = firstCurrency.value;
  }
}

async function loadDepartments() {
  if (!form.branch) {
    departmentOptions.value = [];
    return;
  }
  const { data } = await fetch(`/departments/?branch_id=${form.branch}`, { headers: getAuthHeaders() });
  departmentOptions.value = flattenTree((data as any[]) || []);
}

function onBranchChange() {
  form.department = undefined;
  loadDepartments();
}

async function getCurrentCompanyId() {
  const { data } = await fetch("/auth/me/", { headers: getAuthHeaders() });
  const me = data as any;
  return me?.memberships?.[0]?.company?.id ?? null;
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

  saving.value = true;
  error.value = "";
  try {
    const companyId = await getCurrentCompanyId();
    if (!companyId) {
      error.value = "Неможливо визначити компанію.";
      return;
    }

    const endpoint = isSales.value ? "/sales-tenders/" : "/procurement-tenders/";
    const { data: createdRaw, error: createError } = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      body: {
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
      },
    });
    const created = createdRaw as any;

    if (createError || !created?.id) {
      error.value = typeof createError === "string" ? createError : "Помилка створення тендера.";
      return;
    }

    const detailUrl = isSales.value ? `/cabinet/tenders/sales/${created.id}` : `/cabinet/tenders/${created.id}`;
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
});
</script>
