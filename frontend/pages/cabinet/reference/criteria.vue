<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Критерії тендерів</h2>
      <UButton icon="i-heroicons-plus" @click="openModal()">
        Додати критерій
      </UButton>
    </div>

    <div class="flex-1 min-h-0 overflow-auto">
      <UTable
        :data="tableData"
        :columns="tableColumns"
        :meta="tableMeta"
        class="w-full"
        @on-select="(_e, row) => selectCriterion(row.original)"
      >
        <template #actions-cell="{ row }">
          <div class="flex gap-1">
            <UButton
              icon="i-heroicons-pencil-square"
              size="xs"
              variant="ghost"
              aria-label="Редагувати"
              @click.stop="openModal(row.original)"
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
        v-if="criteria.length === 0"
        class="text-center text-gray-400 py-8"
      >
        Немає критеріїв. Додайте перший.
      </div>
    </div>

    <!-- Модальне вікно створення/редагування -->
    <UModal v-model:open="showModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>{{ editing ? 'Редагувати критерій' : 'Додати критерій' }}</h3>
          </template>
          <UForm :state="form" @submit="save" class="space-y-4">
            <UFormField label="Назва критерія" name="name" required>
              <UInput v-model="form.name" placeholder="Наприклад: Ціна за одиницю" />
            </UFormField>

            <UFormField label="Тип критерія" name="type" required>
              <USelectMenu
                v-model="form.type"
                :items="typeOptions"
                value-key="value"
                placeholder="Оберіть тип"
              />
            </UFormField>

            <!-- Числовий: діапазон + список значень -->
            <template v-if="form.type === 'numeric'">
              <div class="grid grid-cols-2 gap-4">
                <UFormField label="Мін. значення (діапазон)" name="range_min">
                  <UInput v-model.number="form.options.range_min" type="number" placeholder="Не обмежено" />
                </UFormField>
                <UFormField label="Макс. значення (діапазон)" name="range_max">
                  <UInput v-model.number="form.options.range_max" type="number" placeholder="Не обмежено" />
                </UFormField>
              </div>
              <UFormField
                label="Варіанти числових значень (список для вибору)"
                help="Додайте значення, які учасник зможе обрати. Порожньо — дозволено вводити будь-яке число в діапазоні."
              >
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

            <!-- Текстовий: список варіантів -->
            <template v-if="form.type === 'text'">
              <UFormField
                label="Текстові значення для вибору учасника"
                help="Додайте варіанти, які учасник зможе обрати."
              >
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

            <!-- Файловий та булевий — без додаткових полів -->
            <p v-if="form.type === 'file'" class="text-sm text-gray-500">
              Учасник завантажить файл у відповідь на цей критерій.
            </p>
            <p v-if="form.type === 'boolean'" class="text-sm text-gray-500">
              Учасник обере лише «Так» або «Ні».
            </p>

            <div class="flex gap-4 pt-2">
              <UButton variant="outline" class="flex-1" @click="showModal = false">
                Скасувати
              </UButton>
              <UButton type="submit" class="flex-1" :loading="saving">
                {{ editing ? 'Зберегти' : 'Додати' }}
              </UButton>
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Критерії тендерів" },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();
const config = useRuntimeConfig();

const criteria = ref<any[]>([]);
const selectedCriterion = ref<any | null>(null);
const showModal = ref(false);
const saving = ref(false);
const editing = ref(false);

const typeOptions = [
  { value: "numeric", label: "Числовий" },
  { value: "text", label: "Текстовий" },
  { value: "file", label: "Файловий" },
  { value: "boolean", label: "Булевий (Так/Ні)" },
];

const form = reactive<{
  id: number | null;
  name: string;
  type: string;
  options: {
    range_min?: number | null;
    range_max?: number | null;
    numeric_choices?: (number | null)[];
    text_choices?: string[];
  };
}>({
  id: null,
  name: "",
  type: "numeric",
  options: {},
});

function resetForm() {
  form.id = null;
  form.name = "";
  form.type = "numeric";
  form.options = {
    range_min: null,
    range_max: null,
    numeric_choices: [],
    text_choices: [],
  };
}

function openModal(item?: any) {
  editing.value = !!item;
  if (item) {
    form.id = item.id;
    form.name = item.name;
    form.type = item.type;
    const opt = item.options || {};
    form.options = {
      range_min: opt.range_min ?? null,
      range_max: opt.range_max ?? null,
      numeric_choices: Array.isArray(opt.numeric_choices) ? [...opt.numeric_choices] : [],
      text_choices: Array.isArray(opt.text_choices) ? [...opt.text_choices] : [],
    };
  } else {
    resetForm();
  }
  ensureOptionsArrays();
  showModal.value = true;
}

function ensureOptionsArrays() {
  if (!Array.isArray(form.options.numeric_choices)) form.options.numeric_choices = [];
  if (!Array.isArray(form.options.text_choices)) form.options.text_choices = [];
}

function optionsForType(type: string) {
  const base = {
    range_min: null as number | null,
    range_max: null as number | null,
    numeric_choices: [] as (number | null)[],
    text_choices: [] as string[],
  };
  if (type === "numeric") return { ...base };
  if (type === "text") return { ...base, text_choices: [] };
  return base;
}

watch(
  () => form.type,
  (newType) => {
    form.options = optionsForType(newType);
    ensureOptionsArrays();
  }
);

function selectCriterion(item: any) {
  selectedCriterion.value = item;
}

const tableColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "type_label", header: "Тип" },
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

const tableData = computed(() =>
  criteria.value.map((c: any) => ({
    ...c,
    options_summary: formatOptionsSummary(c),
  }))
);

function formatOptionsSummary(c: any): string {
  const opt = c.options || {};
  if (c.type === "numeric") {
    const parts = [];
    if (opt.range_min != null || opt.range_max != null) {
      parts.push(`Діапазон: ${opt.range_min ?? "—"} … ${opt.range_max ?? "—"}`);
    }
    if (opt.numeric_choices?.length) {
      parts.push(`Варіанти: ${opt.numeric_choices.join(", ")}`);
    }
    return parts.length ? parts.join("; ") : "—";
  }
  if (c.type === "text" && opt.text_choices?.length) {
    return opt.text_choices.join(", ");
  }
  if (c.type === "file") return "Файл";
  if (c.type === "boolean") return "Так/Ні";
  return "—";
}

async function loadCriteria() {
  const { data } = await fetch("/tender-criteria/", { headers: getAuthHeaders() });
  criteria.value = data ?? [];
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
    alert("Неможливо визначити компанію");
    return;
  }

  saving.value = true;
  try {
    const options: Record<string, unknown> = {};
    if (form.type === "numeric") {
      if (form.options.range_min != null && form.options.range_min !== "") options.range_min = Number(form.options.range_min);
      if (form.options.range_max != null && form.options.range_max !== "") options.range_max = Number(form.options.range_max);
      const nums = (form.options.numeric_choices || [])
        .map((v) => (v === "" || v === null ? null : Number(v)))
        .filter((v) => v !== null && !Number.isNaN(v));
      if (nums.length) options.numeric_choices = nums;
    }
    if (form.type === "text") {
      const texts = (form.options.text_choices || []).map((s) => String(s).trim()).filter(Boolean);
      if (texts.length) options.text_choices = texts;
    }

    const payload = {
      company: companyId,
      name: form.name.trim(),
      type: form.type,
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
  if (!confirm(`Видалити критерій «${item.name}»?`)) return;
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

onMounted(() => loadCriteria());
</script>
