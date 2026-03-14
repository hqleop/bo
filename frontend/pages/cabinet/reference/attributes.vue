<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Атрибути тендерів</h2>
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
              @click="openInactiveAttributesModal('sales')"
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
            @on-select="(_e, row) => selectAttribute(row.original)"
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
                  @click.stop="deactivateAttribute(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteAttribute(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div
            v-if="salesAttributes.length === 0"
            class="text-center text-gray-400 py-8"
          >
            Немає атрибутів для продажу.
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
              @click="openInactiveAttributesModal('procurement')"
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
            @on-select="(_e, row) => selectAttribute(row.original)"
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
                  @click.stop="deactivateAttribute(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteAttribute(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div
            v-if="procurementAttributes.length === 0"
            class="text-center text-gray-400 py-8"
          >
            Немає атрибутів для закупівлі.
          </div>
        </div>
      </UCard>
    </div>

    <UModal v-model:open="showModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{ editing ? "Редагувати атрибут" : "Додати атрибут" }} ({{
                form.tender_type === "sales" ? "Продаж" : "Закупівля"
              }})
            </h3>
          </template>
          <UForm :state="form" @submit="save" class="space-y-4">
            <UFormField label="Назва атрибута" name="name" required>
              <UInput
                v-model="form.name"
                placeholder="Наприклад: Термін придатності"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Тип атрибута" name="type" required>
              <USelectMenu
                v-model="form.type"
                :items="typeOptions"
                value-key="value"
                placeholder="Оберіть тип"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Категорія" name="category">
              <USelectMenu
                v-model="form.category"
                :items="categoryOptions"
                value-key="value"
                placeholder="Без прив'язки до категорії"
                class="w-full"
              />
            </UFormField>

            <UFormField>
              <UCheckbox
                v-model="form.is_required"
                label="Обов'язковий атрибут"
              />
            </UFormField>

            <template v-if="form.type === 'numeric'">
              <UFormField label="Варіанти числових значень">
                <div class="space-y-2">
                  <div
                    v-for="(_val, idx) in form.options.numeric_choices"
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
              <UFormField label="Варіанти текстових значень">
                <div class="space-y-2">
                  <div
                    v-for="(_val, idx) in form.options.text_choices"
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
                    v-for="(_val, idx) in form.options.date_choices"
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

            <div class="flex gap-4 pt-2">
              <UButton variant="outline" class="flex-1" @click="showModal = false">
                Скасувати
              </UButton>
              <UButton type="submit" class="flex-1" :loading="saving">
                {{ editing ? "Зберегти" : "Додати" }}
              </UButton>
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>

    <InactiveItemsModal
      :open="showInactiveModal"
      :title="
        inactiveTenderType === 'sales'
          ? 'Деактивовані атрибути продажу'
          : 'Деактивовані атрибути закупівлі'
      "
      :items="inactiveAttributes"
      :fields="inactiveAttributeFields"
      :loading="loadingInactiveAttributes"
      empty-text="Немає деактивованих атрибутів."
      @update:open="showInactiveModal = $event"
      @restore="restoreAttribute"
      @delete="deleteInactiveAttribute"
    />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Атрибути тендерів" },
});

const { getAuthHeaders, logout } = useAuth();
const { fetch } = useApi();

const salesAttributes = ref<any[]>([]);
const procurementAttributes = ref<any[]>([]);
const inactiveAttributes = ref<any[]>([]);
const selectedAttribute = ref<any | null>(null);
const showModal = ref(false);
const showInactiveModal = ref(false);
const saving = ref(false);
const loadingInactiveAttributes = ref(false);
const editing = ref(false);
const inactiveTenderType = ref<"sales" | "procurement">("sales");
const categoryOptions = ref<{ value: number | null; label: string }[]>([
  { value: null, label: "Без категорії" },
]);

const typeOptions = [
  { value: "numeric", label: "Числовий" },
  { value: "text", label: "Текстовий" },
  { value: "date", label: "Дата" },
];

const form = reactive<{
  id: number | null;
  name: string;
  type: string;
  tender_type: "sales" | "procurement";
  category: number | null;
  is_required: boolean;
  options: {
    numeric_choices?: (number | null)[];
    text_choices?: string[];
    date_choices?: string[];
  };
}>({
  id: null,
  name: "",
  type: "text",
  tender_type: "sales",
  category: null,
  is_required: false,
  options: {},
});

function optionsForType(type: string) {
  if (type === "numeric") return { numeric_choices: [] as (number | null)[] };
  if (type === "date") return { date_choices: [] as string[] };
  return { text_choices: [] as string[] };
}

function ensureOptionsArrays() {
  if (!Array.isArray(form.options.numeric_choices))
    form.options.numeric_choices = [];
  if (!Array.isArray(form.options.text_choices)) form.options.text_choices = [];
  if (!Array.isArray(form.options.date_choices)) form.options.date_choices = [];
}

watch(
  () => form.type,
  (newType) => {
    form.options = optionsForType(newType);
    ensureOptionsArrays();
  },
);

function resetForm(tenderType: "sales" | "procurement") {
  form.id = null;
  form.name = "";
  form.type = "text";
  form.tender_type = tenderType;
  form.category = null;
  form.is_required = false;
  form.options = optionsForType(form.type);
  ensureOptionsArrays();
}

function openModal(item?: any, tenderType: "sales" | "procurement" = "sales") {
  editing.value = !!item;
  if (item) {
    form.id = item.id;
    form.name = item.name;
    form.type = item.type;
    form.tender_type = item.tender_type || tenderType;
    form.category = item.category ?? null;
    form.is_required = Boolean(item.is_required);
    const opt = item.options || {};
    form.options = {
      numeric_choices: Array.isArray(opt.numeric_choices)
        ? [...opt.numeric_choices]
        : [],
      text_choices: Array.isArray(opt.text_choices) ? [...opt.text_choices] : [],
      date_choices: Array.isArray(opt.date_choices) ? [...opt.date_choices] : [],
    };
  } else {
    resetForm(tenderType);
  }
  ensureOptionsArrays();
  showModal.value = true;
}

function selectAttribute(item: any) {
  selectedAttribute.value = item;
}

const tableColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "type_label", header: "Тип" },
  { accessorKey: "category_name", header: "Категорія" },
  { accessorKey: "is_required_label", header: "Обов'язковий" },
  { accessorKey: "options_summary", header: "Варіанти значень" },
  { id: "actions", header: "Дії" },
];

const tableMeta = computed(() => ({
  class: {
    tr: (row: any) =>
      row.original?.id === selectedAttribute.value?.id
        ? "bg-blue-50 cursor-pointer"
        : "cursor-pointer",
  },
}));

const salesTableData = computed(() =>
  salesAttributes.value.map((a: any) => ({
    ...a,
    category_name: a.category_name || "—",
    is_required_label: a.is_required ? "Так" : "Ні",
    options_summary: formatOptionsSummary(a),
  })),
);

const procurementTableData = computed(() =>
  procurementAttributes.value.map((a: any) => ({
    ...a,
    category_name: a.category_name || "—",
    is_required_label: a.is_required ? "Так" : "Ні",
    options_summary: formatOptionsSummary(a),
  })),
);

const inactiveAttributeFields = [
  { key: "name", label: "Назва" },
  { key: "type_label", label: "Тип" },
  { key: "category_name", label: "Категорія" },
];

function formatOptionsSummary(a: any): string {
  const opt = a.options || {};
  if (a.type === "numeric" && opt.numeric_choices?.length) {
    return opt.numeric_choices.join(", ");
  }
  if (a.type === "text" && opt.text_choices?.length) {
    return opt.text_choices.join(", ");
  }
  if (a.type === "date" && opt.date_choices?.length) {
    return opt.date_choices.join(", ");
  }
  return "-";
}

function flattenCategories(
  tree: any[],
  level = 0,
): { value: number; label: string }[] {
  const out: { value: number; label: string }[] = [];
  for (const node of tree || []) {
    if (!node?.id) continue;
    const prefix = level > 0 ? `${"  ".repeat(level)}↳ ` : "";
    out.push({ value: node.id, label: `${prefix}${node.name || `#${node.id}`}` });
    if (Array.isArray(node.children) && node.children.length) {
      out.push(...flattenCategories(node.children, level + 1));
    }
  }
  return out;
}

async function loadCategories() {
  const { data } = await fetch("/categories/", { headers: getAuthHeaders() });
  const flat = flattenCategories(Array.isArray(data) ? data : []);
  categoryOptions.value = [{ value: null, label: "Без категорії" }, ...flat];
}

async function loadAttributes() {
  const [salesRes, procurementRes] = await Promise.all([
    fetch("/tender-attributes/?tender_type=sales", { headers: getAuthHeaders() }),
    fetch("/tender-attributes/?tender_type=procurement", {
      headers: getAuthHeaders(),
    }),
  ]);
  salesAttributes.value = Array.isArray(salesRes.data) ? salesRes.data : [];
  procurementAttributes.value = Array.isArray(procurementRes.data)
    ? procurementRes.data
    : [];
}

async function loadInactiveAttributes(tenderType: "sales" | "procurement") {
  loadingInactiveAttributes.value = true;
  const { data } = await fetch(
    `/tender-attributes/?tender_type=${tenderType}&inactive_only=1`,
    { headers: getAuthHeaders() },
  );
  inactiveAttributes.value = Array.isArray(data) ? data : [];
  loadingInactiveAttributes.value = false;
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
      category: form.category,
      is_required: Boolean(form.is_required),
      options,
    };

    if (editing.value && form.id) {
      const { error } = await fetch(`/tender-attributes/${form.id}/`, {
        method: "PATCH",
        body: payload,
        headers: getAuthHeaders(),
      });
      if (error) {
        alert("Помилка збереження");
        return;
      }
    } else {
      const { error } = await fetch("/tender-attributes/", {
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
    await loadAttributes();
  } finally {
    saving.value = false;
  }
}

async function deleteAttribute(item: any) {
  if (!item?.id) return;
  if (!confirm(`Видалити атрибут "${item.name}"?`)) return;
  const { error } = await fetch(`/tender-attributes/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Помилка видалення");
    return;
  }
  if (selectedAttribute.value?.id === item.id) selectedAttribute.value = null;
  await loadAttributes();
}

async function deactivateAttribute(item: any) {
  if (!item?.id) return;
  if (!confirm(`Деактивувати атрибут "${item.name}"?`)) return;
  const { error } = await fetch(`/tender-attributes/${item.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося деактивувати атрибут");
    return;
  }
  if (selectedAttribute.value?.id === item.id) selectedAttribute.value = null;
  await loadAttributes();
}

async function openInactiveAttributesModal(tenderType: "sales" | "procurement") {
  inactiveTenderType.value = tenderType;
  showInactiveModal.value = true;
  await loadInactiveAttributes(tenderType);
}

async function restoreAttribute(item: any) {
  const { error } = await fetch(`/tender-attributes/${item.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося відновити атрибут");
    return;
  }
  await Promise.all([loadAttributes(), loadInactiveAttributes(inactiveTenderType.value)]);
}

async function deleteInactiveAttribute(item: any) {
  if (!confirm(`Видалити атрибут "${item.name}" остаточно?`)) return;
  const { error } = await fetch(`/tender-attributes/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Не вдалося видалити атрибут");
    return;
  }
  await Promise.all([loadAttributes(), loadInactiveAttributes(inactiveTenderType.value)]);
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadAttributes()]);
});
</script>
