<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Критерії тендерів</h2>
    </div>

    <div
      class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-hidden"
    >
      <UCard class="h-full flex flex-col min-h-0 border border-gray-200 shadow-sm">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-semibold">Продаж</h3>
            <UButton
              size="sm"
              variant="outline"
              icon="i-heroicons-archive-box"
              @click="openInactiveCriteriaModal('sales')"
            >
              Деактивовані
            </UButton>
            <UButton
              size="sm"
              icon="i-heroicons-plus"
              @click="openModal(undefined, 'sales')"
            >
              Додати
            </UButton>
          </div>
        </template>

        <div class="flex-1 min-h-0 overflow-auto">
          <UTable
            :data="salesTableData"
            :columns="tableColumns"
            :meta="tableMeta"
            class="w-full"
            @on-select="(_e, row) => selectCriterion(row.original)"
          >
            <template #name-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click.stop="openModal(row.original, 'sales')"
              >
                {{ row.original.name }}
              </button>
            </template>
            <template #actions-cell="{ row }">
              <div class="flex gap-1">
                
                <UButton
                  icon="i-heroicons-archive-box"
                  size="xs"
                  variant="ghost"
                  color="warning"
                  aria-label="Деактивувати"
                  @click.stop="deactivateCriterion(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteCriterion(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div
            v-if="salesCriteria.length === 0"
            class="text-center text-gray-400 py-8"
          >
            Немає критеріїв для продажу.
          </div>
        </div>
      </UCard>

      <UCard class="h-full flex flex-col min-h-0 border border-gray-200 shadow-sm">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-semibold">Закупівля</h3>
            <UButton
              size="sm"
              variant="outline"
              icon="i-heroicons-archive-box"
              @click="openInactiveCriteriaModal('procurement')"
            >
              Деактивовані
            </UButton>
            <UButton
              size="sm"
              icon="i-heroicons-plus"
              @click="openModal(undefined, 'procurement')"
            >
              Додати
            </UButton>
          </div>
        </template>

        <div class="flex-1 min-h-0 overflow-auto">
          <UTable
            :data="procurementTableData"
            :columns="tableColumns"
            :meta="tableMeta"
            class="w-full"
            @on-select="(_e, row) => selectCriterion(row.original)"
          >
            <template #name-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click.stop="openModal(row.original, 'procurement')"
              >
                {{ row.original.name }}
              </button>
            </template>
            <template #actions-cell="{ row }">
              <div class="flex gap-1">
                
                <UButton
                  icon="i-heroicons-archive-box"
                  size="xs"
                  variant="ghost"
                  color="warning"
                  aria-label="Деактивувати"
                  @click.stop="deactivateCriterion(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteCriterion(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div
            v-if="procurementCriteria.length === 0"
            class="text-center text-gray-400 py-8"
          >
            Немає критеріїв для закупівлі.
          </div>
        </div>
      </UCard>
    </div>

    <UModal v-model:open="showModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{ editing ? "Редагувати критерій" : "Додати критерій" }} ({{
                form.tender_type === "sales" ? "Продаж" : "Закупівля"
              }})
            </h3>
          </template>
          <UForm :state="form" @submit="save" class="space-y-4">
            <UFormField label="Назва критерію" name="name" required>
              <UInput
                v-model="form.name"
                placeholder="Наприклад: Ціна за одиницю"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Тип критерію" name="type" required>
              <USelectMenu
                v-model="form.type"
                :items="typeOptions"
                value-key="value"
                placeholder="Оберіть тип"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Застосування" name="application" required>
              <USelectMenu
                v-model="form.application"
                :items="applicationOptions"
                value-key="value"
                placeholder="Оберіть застосування"
                class="w-full"
              />
            </UFormField>

            <UFormField>
              <UCheckbox
                v-model="form.is_required"
                label="Обов'язковий критерій"
              />
            </UFormField>

            <template v-if="form.type === 'numeric'">
              <div class="grid grid-cols-2 gap-4">
                <UFormField label="Мін. значення" name="range_min">
                  <UInput
                    v-model.number="form.options.range_min"
                    type="number"
                    placeholder="Не обмежено"
                    class="w-full"
                  />
                </UFormField>
                <UFormField label="Макс. значення" name="range_max">
                  <UInput
                    v-model.number="form.options.range_max"
                    type="number"
                    placeholder="Не обмежено"
                    class="w-full"
                  />
                </UFormField>
              </div>
              <UFormField label="Варіанти числових значень">
                <div class="space-y-2">
                  <div
                    v-for="(val, idx) in form.options.numeric_choices"
                    :key="idx"
                    class="flex gap-2 items-center"
                  >
                    <UInput
                      v-model.number="form.options.numeric_choices[idx]"
                      type="number"
                      class="flex-1"
                    />
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="red"
                      aria-label="Видалити"
                      @click="form.options.numeric_choices.splice(idx, 1)"
                    />
                  </div>
                  <UButton
                    size="sm"
                    variant="outline"
                    icon="i-heroicons-plus"
                    @click="form.options.numeric_choices.push(null)"
                  >
                    Додати значення
                  </UButton>
                </div>
              </UFormField>
            </template>

            <template v-if="form.type === 'text'">
              <UFormField label="Текстові значення">
                <div class="space-y-2">
                  <div
                    v-for="(val, idx) in form.options.text_choices"
                    :key="idx"
                    class="flex gap-2 items-center"
                  >
                    <UInput
                      v-model="form.options.text_choices[idx]"
                      class="flex-1"
                      placeholder="Текст варіанту"
                    />
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="red"
                      aria-label="Видалити"
                      @click="form.options.text_choices.splice(idx, 1)"
                    />
                  </div>
                  <UButton
                    size="sm"
                    variant="outline"
                    icon="i-heroicons-plus"
                    @click="form.options.text_choices.push('')"
                  >
                    Додати варіант
                  </UButton>
                </div>
              </UFormField>
            </template>

            <template v-if="form.type === 'date'">
              <UFormField label="Варіанти дат">
                <div class="space-y-2">
                  <div
                    v-for="(val, idx) in form.options.date_choices"
                    :key="idx"
                    class="flex gap-2 items-center"
                  >
                    <DateValuePicker
                      :model-value="form.options.date_choices[idx] || ''"
                      class="flex-1"
                      @update:model-value="
                        form.options.date_choices[idx] = $event || ''
                      "
                    />
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="red"
                      aria-label="Видалити"
                      @click="form.options.date_choices.splice(idx, 1)"
                    />
                  </div>
                  <UButton
                    size="sm"
                    variant="outline"
                    icon="i-heroicons-plus"
                    @click="form.options.date_choices.push('')"
                  >
                    Додати дату
                  </UButton>
                </div>
              </UFormField>
            </template>

            <p v-if="form.type === 'file'" class="text-sm text-gray-500">
              Учасник завантажить файл у відповідь на цей критерій.
            </p>
            <p v-if="form.type === 'boolean'" class="text-sm text-gray-500">
              Учасник обере лише «Так» або «Ні».
            </p>

            <div class="flex gap-4 pt-2">
              <UButton
                variant="outline"
                class="flex-1"
                @click="showModal = false"
                >Скасувати</UButton
              >
              <UButton type="submit" class="flex-1" :loading="saving">{{
                editing ? "Зберегти" : "Додати"
              }}</UButton>
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>

    <InactiveItemsModal
      :open="showInactiveModal"
      :title="
        inactiveTenderType === 'sales'
          ? 'Деактивовані критерії продажу'
          : 'Деактивовані критерії закупівлі'
      "
      :items="inactiveCriteria"
      :fields="inactiveCriteriaFields"
      :loading="loadingInactiveCriteria"
      empty-text="Немає деактивованих критеріїв."
      @update:open="showInactiveModal = $event"
      @restore="restoreCriterion"
      @delete="deleteInactiveCriterion"
    />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Критерії тендерів" },
});

const { getAuthHeaders, logout } = useAuth();
const { fetch } = useApi();

const salesCriteria = ref<any[]>([]);
const procurementCriteria = ref<any[]>([]);
const inactiveCriteria = ref<any[]>([]);
const selectedCriterion = ref<any | null>(null);
const showModal = ref(false);
const showInactiveModal = ref(false);
const saving = ref(false);
const loadingInactiveCriteria = ref(false);
const editing = ref(false);
const inactiveTenderType = ref<"sales" | "procurement">("sales");

const typeOptions = [
  { value: "numeric", label: "Числовий" },
  { value: "text", label: "Текстовий" },
  { value: "date", label: "Дата" },
  { value: "file", label: "Файловий" },
  { value: "boolean", label: "Булевий (Так/Ні)" },
];

const applicationOptions = [
  { value: "general", label: "Загальний" },
  { value: "individual", label: "Індивідуальний" },
];

const form = reactive<{
  id: number | null;
  name: string;
  type: string;
  tender_type: "sales" | "procurement";
  application: string;
  is_required: boolean;
  options: {
    range_min?: number | null;
    range_max?: number | null;
    numeric_choices?: (number | null)[];
    text_choices?: string[];
    date_choices?: string[];
  };
}>({
  id: null,
  name: "",
  type: "numeric",
  tender_type: "sales",
  application: "individual",
  is_required: false,
  options: {},
});

function resetForm(tenderType: "sales" | "procurement") {
  form.id = null;
  form.name = "";
  form.type = "numeric";
  form.tender_type = tenderType;
  form.application = "individual";
  form.is_required = false;
  form.options = {
    range_min: null,
    range_max: null,
    numeric_choices: [],
    text_choices: [],
    date_choices: [],
  };
}

function openModal(item?: any, tenderType: "sales" | "procurement" = "sales") {
  editing.value = !!item;
  if (item) {
    form.id = item.id;
    form.name = item.name;
    form.type = item.type;
    form.tender_type = item.tender_type || tenderType;
    form.application = item.application ?? "individual";
    form.is_required = Boolean(item.is_required);
    const opt = item.options || {};
    form.options = {
      range_min: opt.range_min ?? null,
      range_max: opt.range_max ?? null,
      numeric_choices: Array.isArray(opt.numeric_choices)
        ? [...opt.numeric_choices]
        : [],
      text_choices: Array.isArray(opt.text_choices)
        ? [...opt.text_choices]
        : [],
      date_choices: Array.isArray(opt.date_choices)
        ? [...opt.date_choices]
        : [],
    };
  } else {
    resetForm(tenderType);
  }
  ensureOptionsArrays();
  showModal.value = true;
}

function ensureOptionsArrays() {
  if (!Array.isArray(form.options.numeric_choices))
    form.options.numeric_choices = [];
  if (!Array.isArray(form.options.text_choices)) form.options.text_choices = [];
  if (!Array.isArray(form.options.date_choices)) form.options.date_choices = [];
}

function optionsForType(type: string) {
  const base = {
    range_min: null as number | null,
    range_max: null as number | null,
    numeric_choices: [] as (number | null)[],
    text_choices: [] as string[],
    date_choices: [] as string[],
  };
  if (type === "numeric") return { ...base };
  if (type === "text") return { ...base, text_choices: [] };
  if (type === "date") return { ...base, date_choices: [] };
  return base;
}

watch(
  () => form.type,
  (newType) => {
    form.options = optionsForType(newType);
    ensureOptionsArrays();
  },
);

function selectCriterion(item: any) {
  selectedCriterion.value = item;
}

const tableColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "type_label", header: "Тип" },
  { accessorKey: "application_label", header: "Застосування" },
  { accessorKey: "is_required_label", header: "Обов'язковий" },
  { accessorKey: "options_summary", header: "Параметри" },
  { id: "actions", header: "Дії" },
];

const tableMeta = computed(() => ({
  class: {
    tr: (row: any) =>
      row.original?.id === selectedCriterion.value?.id
        ? "bg-blue-50 cursor-pointer"
        : "cursor-pointer",
  },
}));

const salesTableData = computed(() =>
  salesCriteria.value.map((c: any) => ({
    ...c,
    is_required_label: c.is_required ? "Так" : "Ні",
    options_summary: formatOptionsSummary(c),
  })),
);

const procurementTableData = computed(() =>
  procurementCriteria.value.map((c: any) => ({
    ...c,
    is_required_label: c.is_required ? "Так" : "Ні",
    options_summary: formatOptionsSummary(c),
  })),
);

const inactiveCriteriaFields = [
  { key: "name", label: "Назва" },
  { key: "type_label", label: "Тип" },
  { key: "application_label", label: "Застосування" },
];

function formatOptionsSummary(c: any): string {
  const opt = c.options || {};
  if (c.type === "numeric") {
    const parts = [];
    if (opt.range_min != null || opt.range_max != null) {
      parts.push(`Діапазон: ${opt.range_min ?? "-"} … ${opt.range_max ?? "-"}`);
    }
    if (opt.numeric_choices?.length) {
      parts.push(`Варіанти: ${opt.numeric_choices.join(", ")}`);
    }
    return parts.length ? parts.join("; ") : "-";
  }
  if (c.type === "text" && opt.text_choices?.length) {
    return opt.text_choices.join(", ");
  }
  if (c.type === "date" && opt.date_choices?.length) {
    return opt.date_choices.join(", ");
  }
  if (c.type === "file") return "Файл";
  if (c.type === "boolean") return "Так/Ні";
  return "-";
}

async function loadCriteria() {
  const [salesRes, procurementRes] = await Promise.all([
    fetch("/tender-criteria/?tender_type=sales", { headers: getAuthHeaders() }),
    fetch("/tender-criteria/?tender_type=procurement", {
      headers: getAuthHeaders(),
    }),
  ]);
  salesCriteria.value = Array.isArray(salesRes.data) ? salesRes.data : [];
  procurementCriteria.value = Array.isArray(procurementRes.data)
    ? procurementRes.data
    : [];
}

async function loadInactiveCriteria(tenderType: "sales" | "procurement") {
  loadingInactiveCriteria.value = true;
  const { data } = await fetch(
    `/tender-criteria/?tender_type=${tenderType}&inactive_only=1`,
    { headers: getAuthHeaders() },
  );
  inactiveCriteria.value = Array.isArray(data) ? data : [];
  loadingInactiveCriteria.value = false;
}

async function getCurrentCompanyId(): Promise<number | null> {
  const { data } = await fetch("/auth/me/", { headers: getAuthHeaders() });
  const m = data?.memberships?.[0];
  return m?.company?.id ?? null;
}

async function save() {
  if (!form.name.trim()) return;
  const companyId = await getCurrentCompanyId();
  if (!companyId) {
    logout();
    return;
  }

  saving.value = true;
  try {
    const options: Record<string, unknown> = {};
    if (form.type === "numeric") {
      if (form.options.range_min != null && form.options.range_min !== "") {
        options.range_min = Number(form.options.range_min);
      }
      if (form.options.range_max != null && form.options.range_max !== "") {
        options.range_max = Number(form.options.range_max);
      }
      const nums = (form.options.numeric_choices || [])
        .map((v) => (v === "" || v === null ? null : Number(v)))
        .filter((v) => v !== null && !Number.isNaN(v));
      if (nums.length) options.numeric_choices = nums;
    }
    if (form.type === "text") {
      const texts = (form.options.text_choices || [])
        .map((s) => String(s).trim())
        .filter(Boolean);
      if (texts.length) options.text_choices = texts;
    }
    if (form.type === "date") {
      const dates = (form.options.date_choices || [])
        .map((s) => String(s).trim())
        .filter(Boolean);
      if (dates.length) options.date_choices = dates;
    }

    const payload = {
      company: companyId,
      name: form.name.trim(),
      type: form.type,
      tender_type: form.tender_type,
      application: form.application || "individual",
      is_required: Boolean(form.is_required),
      options,
    };

    if (editing.value && form.id) {
      const { error } = await fetch(`/tender-criteria/${form.id}/`, {
        method: "PATCH",
        body: payload,
        headers: getAuthHeaders(),
      });
      if (error) {
        alert("Помилка збереження");
        return;
      }
    } else {
      const { error } = await fetch("/tender-criteria/", {
        method: "POST",
        body: payload,
        headers: getAuthHeaders(),
      });
      if (error) {
        alert("Помилка створення");
        return;
      }
    }
    showModal.value = false;
    await loadCriteria();
  } finally {
    saving.value = false;
  }
}

async function deleteCriterion(item: any) {
  if (!item?.id) return;
  if (!confirm(`Видалити критерій "${item.name}"?`)) return;
  const { error } = await fetch(`/tender-criteria/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Помилка видалення");
    return;
  }
  if (selectedCriterion.value?.id === item.id) selectedCriterion.value = null;
  await loadCriteria();
}

async function deactivateCriterion(item: any) {
  if (!item?.id) return;
  if (!confirm(`Деактивувати критерій "${item.name}"?`)) return;
  const { error } = await fetch(`/tender-criteria/${item.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося деактивувати критерій");
    return;
  }
  if (selectedCriterion.value?.id === item.id) selectedCriterion.value = null;
  await loadCriteria();
}

async function openInactiveCriteriaModal(tenderType: "sales" | "procurement") {
  inactiveTenderType.value = tenderType;
  showInactiveModal.value = true;
  await loadInactiveCriteria(tenderType);
}

async function restoreCriterion(item: any) {
  const { error } = await fetch(`/tender-criteria/${item.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося відновити критерій");
    return;
  }
  await Promise.all([loadCriteria(), loadInactiveCriteria(inactiveTenderType.value)]);
}

async function deleteInactiveCriterion(item: any) {
  if (!confirm(`Видалити критерій "${item.name}" остаточно?`)) return;
  const { error } = await fetch(`/tender-criteria/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося видалити критерій");
    return;
  }
  await Promise.all([loadCriteria(), loadInactiveCriteria(inactiveTenderType.value)]);
}

onMounted(() => loadCriteria());
</script>
