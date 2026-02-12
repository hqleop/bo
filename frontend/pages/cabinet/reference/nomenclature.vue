<template>
  <div class="h-full flex gap-4">
    <!-- Ліва область: список номенклатури -->
    <div class="flex-[2] border-r border-gray-200 p-4 flex flex-col">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">Номенклатури</h2>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-plus"
            size="sm"
            @click="openNomenclatureModal()"
          >
            Додати номенклатуру
          </UButton>
          <UButton
            icon="i-heroicons-cog-6-tooth"
            size="sm"
            variant="outline"
            @click="openUnitsModal"
          >
            Одиниці виміру
          </UButton>
          <UButton
            icon="i-heroicons-check-circle"
            size="sm"
            variant="outline"
            color="green"
            :disabled="
              !selectedNomenclature || selectedNomenclature.is_active
            "
            @click="activateSelected"
          >
            Активувати
          </UButton>
          <UButton
            icon="i-heroicons-x-circle"
            size="sm"
            variant="outline"
            color="yellow"
            :disabled="
              !selectedNomenclature || !selectedNomenclature.is_active
            "
            @click="deactivateSelected"
          >
            Деактивувати
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            size="sm"
            variant="outline"
            color="red"
            :disabled="!selectedNomenclature"
            @click="deleteSelected"
          >
            Видалити
          </UButton>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto space-y-1">
        <div
          v-for="item in filteredNomenclatures"
          :key="item.id"
          class="flex items-center justify-between p-2 rounded-md cursor-pointer hover:bg-gray-50"
          :class="{
            'bg-blue-50 border border-blue-200':
              selectedNomenclature && selectedNomenclature.id === item.id,
          }"
          @click="selectNomenclature(item)"
        >
          <div class="flex flex-col">
            <span class="font-medium">
              {{ item.name }}
              <span
                v-if="!item.is_active"
                class="ml-2 text-xs text-red-500 font-normal"
              >
                (деактивована)
              </span>
            </span>
            <span v-if="item.code" class="text-xs text-gray-500">
              Код / Артикул: {{ item.code }}
            </span>
            <span v-if="item.external_number" class="text-xs text-gray-500">
              Зовнішній номер: {{ item.external_number }}
            </span>
            <span v-if="item.category_name" class="text-xs text-gray-500">
              Категорія: {{ item.category_name }}
            </span>
            <span
              v-else-if="item.cpv_label"
              class="text-xs text-gray-500"
            >
              Категорія CPV: {{ item.cpv_label }}
            </span>
          </div>
          <UButton
            icon="i-heroicons-pencil-square"
            size="xs"
            variant="ghost"
            @click.stop="openNomenclatureModal(item)"
          />
        </div>
        <div
          v-if="filteredNomenclatures.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Номенклатур не знайдено за вибраними фільтрами
        </div>
      </div>
    </div>

    <!-- Права область: фільтри -->
    <div class="flex-1 p-4 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold">Фільтри</h3>
        <UButton
          size="xs"
          variant="ghost"
          color="gray"
          icon="i-heroicons-x-mark"
          @click="clearFilters"
        >
          Очистити
        </UButton>
      </div>

      <UFormGroup label="Назва номенклатури">
        <UInput
          v-model="filters.name"
          placeholder="Пошук по назві номенклатури"
        />
      </UFormGroup>

      <UFormGroup label="Категорія">
        <USelectMenu
          :model-value="filters.categoryId"
          :options="categoryFilterOptions"
          value-attribute="value"
          option-attribute="label"
          placeholder="Оберіть категорію"
          :disabled="
            !!filters.cpvId || categoryFilterOptions.length === 0
          "
          @update:model-value="onCategoryFilterChange"
        />
      </UFormGroup>

      <UFormGroup label="Категорія CPV">
        <USelectMenu
          :model-value="filters.cpvId"
          :options="cpvFilterOptions"
          value-attribute="value"
          option-attribute="label"
          placeholder="Оберіть CPV-категорію"
          :disabled="!!filters.categoryId || cpvFilterOptions.length === 0"
          @update:model-value="onCpvFilterChange"
        />
      </UFormGroup>
    </div>

    <!-- Модальне вікно номенклатури -->
    <UModal v-model="showNomenclatureModal">
      <UCard>
        <template #header>
          <h3>
            {{
              editingNomenclature
                ? "Редагувати номенклатуру"
                : "Додати номенклатуру"
            }}
          </h3>
        </template>
        <UForm
          :state="nomenclatureForm"
          @submit="saveNomenclature"
          class="space-y-4"
        >
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="nomenclatureForm.name" />
          </UFormGroup>

          <UFormGroup label="Одиниця виміру" name="unit" required>
            <USelectMenu
              :model-value="nomenclatureForm.unit"
              :options="unitOptions"
              value-attribute="value"
              option-attribute="label"
              placeholder="Оберіть одиницю виміру"
              @update:model-value="
                (v) => {
                  nomenclatureForm.unit = v ?? null;
                }
              "
            />
          </UFormGroup>

          <div class="grid grid-cols-2 gap-4">
            <UFormGroup label="Код / Артикул" name="code">
              <UInput v-model="nomenclatureForm.code" />
            </UFormGroup>
            <UFormGroup label="Зовнішній номер" name="external_number">
              <UInput v-model="nomenclatureForm.external_number" />
            </UFormGroup>
          </div>

          <UFormGroup label="Опис" name="description">
            <UTextarea v-model="nomenclatureForm.description" />
          </UFormGroup>

          <div class="grid grid-cols-2 gap-4">
            <UFormGroup label="Специфікація (файл)" name="specification_file">
              <UInput
                v-model="nomenclatureForm.specification_file"
                placeholder="Назва або шлях до файлу"
              />
            </UFormGroup>
            <UFormGroup label="Зображення (файл)" name="image_file">
              <UInput
                v-model="nomenclatureForm.image_file"
                placeholder="Назва або шлях до файлу"
              />
            </UFormGroup>
          </div>

          <UFormGroup label="Категорія" name="category">
            <USelectMenu
              :model-value="nomenclatureForm.category"
              :options="categoryOptions"
              value-attribute="value"
              option-attribute="label"
              placeholder="Без категорії"
              :disabled="selectedCpvIds.length > 0"
              @update:model-value="onFormCategoryChange"
            />
          </UFormGroup>

          <UFormGroup
            label="Категорія CPV"
            name="cpv_category"
            help="Доступна, якщо не обрана звичайна категорія"
          >
            <UPopover v-model="showCpvPopover">
              <UButton
                block
                variant="outline"
                :disabled="!!nomenclatureForm.category"
              >
                <span v-if="selectedCpvLabels.length">
                  {{ selectedCpvLabels[0] }}
                </span>
                <span v-else>Оберіть CPV-категорію</span>
              </UButton>
              <template #panel>
                <div
                  class="p-2 w-96 max-h-80 overflow-y-auto space-y-2 bg-white dark:bg-gray-900 rounded-lg shadow"
                >
                  <UInput
                    v-model="cpvSearch"
                    size="sm"
                    placeholder="Пошук за кодом або назвою"
                  />
                  <div class="mt-2 space-y-1">
                    <CpvTreeItem
                      v-for="node in filteredCpvTree"
                      :key="node.id"
                      :item="node"
                      :selected-ids="selectedCpvIds"
                      @toggle="toggleCpvSingle"
                    />
                  </div>
                </div>
              </template>
            </UPopover>
          </UFormGroup>

          <div class="flex gap-4 mt-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showNomenclatureModal = false"
            >
              Скасувати
            </UButton>
            <UButton type="submit" class="flex-1" :loading="saving">
              Зберегти
            </UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>

    <!-- Модальне вікно одиниць виміру -->
    <UModal v-model="showUnitsModal">
      <UCard>
        <template #header>
          <h3>Одиниці виміру</h3>
        </template>
        <div class="space-y-4">
          <div class="flex gap-2">
            <UInput
              v-model="unitForm.name"
              placeholder="Назва одиниці (наприклад, шт., кг)"
              class="flex-1"
            />
            <UButton :loading="savingUnit" @click="addUnit">
              Додати
            </UButton>
          </div>
          <div class="max-h-80 overflow-y-auto divide-y divide-gray-100">
            <div
              v-for="u in units"
              :key="u.id"
              class="flex items-center justify-between py-1.5"
            >
              <span class="text-sm">
                {{ u.name }}
              </span>
              <UButton
                icon="i-heroicons-trash"
                size="xs"
                variant="ghost"
                color="red"
                @click="deleteUnit(u)"
              />
            </div>
            <div
              v-if="units.length === 0"
              class="text-center text-gray-400 py-4 text-sm"
            >
              Немає одиниць виміру
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end">
            <UButton
              variant="outline"
              @click="showUnitsModal = false"
            >
              Закрити
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Номенклатури",
  },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

// Дані
const nomenclatures = ref<any[]>([]);
const selectedNomenclature = ref<any | null>(null);

const units = ref<any[]>([]);
const categories = ref<any[]>([]);
const cpvTree = ref<any[]>([]);

// Фільтри
const filters = reactive({
  name: "",
  categoryId: null as number | null,
  cpvId: null as number | null,
});

const defaultFilterInitialized = ref(false);

// Стан форм / модалок
const showNomenclatureModal = ref(false);
const showUnitsModal = ref(false);
const showCpvPopover = ref(false);
const saving = ref(false);
const savingUnit = ref(false);
const editingNomenclature = ref<any | null>(null);

const nomenclatureForm = reactive({
  id: null as number | null,
  name: "",
  unit: null as number | null,
  code: "",
  external_number: "",
  description: "",
  specification_file: "",
  image_file: "",
  category: null as number | null,
});

// Одиниці виміру
const unitForm = reactive({
  name: "",
});

// CPV для форми
const selectedCpvIds = ref<number[]>([]);
const cpvSearch = ref("");

// Допоміжні функції
const getCurrentCompany = async () => {
  const { data } = await fetch("/auth/me/", {
    headers: getAuthHeaders(),
  });
  if (data?.memberships?.[0]) {
    return data.memberships[0].company.id;
  }
  return null;
};

const loadNomenclatures = async () => {
  const { data } = await fetch("/nomenclatures/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    nomenclatures.value = data;
  } else {
    nomenclatures.value = [];
  }
};

const loadUnits = async () => {
  const { data } = await fetch("/units/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    units.value = data;
  } else {
    units.value = [];
  }
};

const loadCategories = async () => {
  const { data } = await fetch("/categories/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    categories.value = data;
  } else {
    categories.value = [];
  }
};

const loadCpvTree = async () => {
  const { data } = await fetch("/cpv/tree/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    cpvTree.value = data;
  } else {
    cpvTree.value = [];
  }
};

// Опції для селектів
const unitOptions = computed(() =>
  units.value.map((u: any) => ({ value: u.id, label: u.name })),
);

// Сплощення дерева категорій для форми
function flattenCategoriesTree(
  list: any[],
): { id: number; name: string; level: number }[] {
  const out: { id: number; name: string; level: number }[] = [];
  const walk = (nodes: any[], level: number) => {
    if (!nodes?.length) return;
    for (const n of nodes) {
      out.push({ id: n.id, name: n.name, level });
      if (n.children?.length) {
        walk(n.children, level + 1);
      }
    }
  };
  walk(list, 0);
  return out;
}

const categoryOptions = computed(() => {
  const flat = flattenCategoriesTree(categories.value);
  return [
    { value: null, label: "Без категорії" },
    ...flat.map((c) => ({
      value: c.id,
      label: (c.level ? "  ".repeat(c.level) : "") + c.name,
    })),
  ];
});

// Опції фільтрів на основі вже існуючої номенклатури
const categoryFilterOptions = computed(() => {
  const map = new Map<number, string>();
  for (const n of nomenclatures.value) {
    if (n.category && n.category_name) {
      map.set(n.category, n.category_name);
    }
  }
  const arr = Array.from(map.entries()).map(([id, name]) => ({
    value: id,
    label: name,
  }));
  arr.sort((a, b) => a.label.localeCompare(b.label, "uk"));
  return arr;
});

const cpvFilterOptions = computed(() => {
  const map = new Map<number, string>();
  for (const n of nomenclatures.value) {
    if (n.cpv_category && n.cpv_label) {
      map.set(n.cpv_category, n.cpv_label);
    }
  }
  const arr = Array.from(map.entries()).map(([id, label]) => ({
    value: id,
    label,
  }));
  // за умовою: якщо використовуємо CPV, беремо найменший id
  arr.sort((a, b) => a.value - b.value);
  return arr;
});

// Ініціалізація фільтрів за замовчуванням
const initDefaultFilter = () => {
  if (defaultFilterInitialized.value || !nomenclatures.value.length) return;

  if (categoryFilterOptions.value.length > 0) {
    // Беремо першу категорію за алфавітом
    filters.categoryId = categoryFilterOptions.value[0].value as number;
    filters.cpvId = null;
    defaultFilterInitialized.value = true;
    return;
  }

  if (cpvFilterOptions.value.length > 0) {
    // Якщо немає звичайних категорій, але є CPV — беремо з найменшим id
    filters.cpvId = cpvFilterOptions.value[0].value as number;
    filters.categoryId = null;
    defaultFilterInitialized.value = true;
  }
};

// Обробники фільтрів
const onCategoryFilterChange = (value: number | null) => {
  filters.categoryId = value ?? null;
  if (filters.categoryId) {
    filters.cpvId = null;
  }
};

const onCpvFilterChange = (value: number | null) => {
  filters.cpvId = value ?? null;
  if (filters.cpvId) {
    filters.categoryId = null;
  }
};

const clearFilters = () => {
  filters.name = "";
  filters.categoryId = null;
  filters.cpvId = null;
  defaultFilterInitialized.value = false;
  initDefaultFilter();
};

// Обчислення відфільтрованого списку
const filteredNomenclatures = computed(() => {
  let list = nomenclatures.value.slice();

  const term = filters.name.trim().toLowerCase();
  if (term) {
    list = list.filter((n: any) =>
      (n.name || "").toLowerCase().includes(term),
    );
  }

  if (filters.categoryId) {
    list = list.filter((n: any) => n.category === filters.categoryId);
  } else if (filters.cpvId) {
    list = list.filter((n: any) => n.cpv_category === filters.cpvId);
  }

  return list;
});

// Вибір номенклатури
const selectNomenclature = (item: any) => {
  selectedNomenclature.value = item;
};

// Модалка номенклатури
const openNomenclatureModal = (item?: any) => {
  editingNomenclature.value = item || null;

  if (item) {
    nomenclatureForm.id = item.id;
    nomenclatureForm.name = item.name || "";
    nomenclatureForm.unit = item.unit || null;
    nomenclatureForm.code = item.code || "";
    nomenclatureForm.external_number = item.external_number || "";
    nomenclatureForm.description = item.description || "";
    nomenclatureForm.specification_file = item.specification_file || "";
    nomenclatureForm.image_file = item.image_file || "";
    nomenclatureForm.category = item.category || null;
    selectedCpvIds.value = item.cpv_category ? [item.cpv_category] : [];
  } else {
    nomenclatureForm.id = null;
    nomenclatureForm.name = "";
    nomenclatureForm.unit = null;
    nomenclatureForm.code = "";
    nomenclatureForm.external_number = "";
    nomenclatureForm.description = "";
    nomenclatureForm.specification_file = "";
    nomenclatureForm.image_file = "";
    nomenclatureForm.category = null;
    selectedCpvIds.value = [];
  }

  showNomenclatureModal.value = true;
};

const onFormCategoryChange = (value: number | null) => {
  nomenclatureForm.category = value ?? null;
  if (nomenclatureForm.category) {
    selectedCpvIds.value = [];
  }
};

// CPV дерево для форми
function filterCpvTree(list: any[], predicate: (node: any) => boolean): any[] {
  const result: any[] = [];
  for (const node of list) {
    const children = node.children ? filterCpvTree(node.children, predicate) : [];
    if (predicate(node) || children.length) {
      result.push({ ...node, children });
    }
  }
  return result;
}

const filteredCpvTree = computed(() => {
  const term = cpvSearch.value.trim();
  if (!term) return cpvTree.value;
  const lower = term.toLowerCase();
  const isDigit = /^[0-9]/.test(lower);
  const predicate = (node: any) => {
    if (isDigit) {
      return (node.cpv_code || "").toLowerCase().includes(lower);
    }
    return (node.name_ua || "").toLowerCase().includes(lower);
  };
  return filterCpvTree(cpvTree.value, predicate);
});

const selectedCpvLabels = computed(() => {
  if (!selectedCpvIds.value.length) return [];
  const all: any[] = [];
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      all.push(n);
      if (n.children?.length) walk(n.children);
    }
  };
  walk(cpvTree.value);
  return selectedCpvIds.value
    .map((id) => {
      const node = all.find((n) => n.id === id);
      return node ? `${node.cpv_code} - ${node.name_ua}` : "";
    })
    .filter(Boolean);
});

const toggleCpvSingle = (id: number) => {
  if (selectedCpvIds.value.includes(id)) {
    selectedCpvIds.value = [];
  } else {
    selectedCpvIds.value = [id];
    // якщо обрано CPV — очищаємо звичайну категорію
    nomenclatureForm.category = null;
  }
};

// Збереження номенклатури
const saveNomenclature = async () => {
  if (!nomenclatureForm.name.trim() || !nomenclatureForm.unit) {
    alert("Назва та одиниця виміру є обов'язковими");
    return;
  }

  saving.value = true;
  try {
    let companyId = null;
    if (editingNomenclature.value) {
      companyId = editingNomenclature.value.company;
    } else {
      companyId = await getCurrentCompany();
    }

    const payload: any = {
      company: companyId,
      name: nomenclatureForm.name,
      unit: nomenclatureForm.unit,
      code: nomenclatureForm.code,
      external_number: nomenclatureForm.external_number,
      description: nomenclatureForm.description,
      specification_file: nomenclatureForm.specification_file,
      image_file: nomenclatureForm.image_file,
      category: nomenclatureForm.category,
      cpv_category:
        !nomenclatureForm.category && selectedCpvIds.value.length
          ? selectedCpvIds.value[0]
          : null,
    };

    let endpoint = "/nomenclatures/";
    let method: "POST" | "PATCH" = "POST";

    if (editingNomenclature.value && nomenclatureForm.id) {
      endpoint = `/nomenclatures/${nomenclatureForm.id}/`;
      method = "PATCH";
    }

    const { error } = await fetch(endpoint, {
      method,
      body: payload,
      headers: getAuthHeaders(),
    });

    if (error) {
      alert("Помилка збереження номенклатури");
      saving.value = false;
      return;
    }

    showNomenclatureModal.value = false;
    await loadNomenclatures();
    initDefaultFilter();
  } finally {
    saving.value = false;
  }
};

// Активувати / деактивувати / видалити
const deactivateSelected = async () => {
  if (!selectedNomenclature.value) return;
  const { id, name } = selectedNomenclature.value;
  if (
    !confirm(
      `Деактивувати номенклатуру "${name}"? Вона не буде доступна для вибору.`,
    )
  ) {
    return;
  }
  const { error } = await fetch(`/nomenclatures/${id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Помилка деактивації номенклатури");
    return;
  }
  await loadNomenclatures();
};

const activateSelected = async () => {
  if (!selectedNomenclature.value) return;
  const { id, name } = selectedNomenclature.value;
  if (
    !confirm(
      `Активувати номенклатуру "${name}"? Вона буде доступна для вибору.`,
    )
  ) {
    return;
  }
  const { error } = await fetch(`/nomenclatures/${id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Помилка активації номенклатури");
    return;
  }
  await loadNomenclatures();
};

const deleteSelected = async () => {
  if (!selectedNomenclature.value) return;
  const { id, name } = selectedNomenclature.value;
  if (
    !confirm(
      `Видалити номенклатуру "${name}"? Цю дію не можна буде скасувати.`,
    )
  ) {
    return;
  }
  const { error } = await fetch(`/nomenclatures/${id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert("Помилка видалення номенклатури");
    return;
  }
  selectedNomenclature.value = null;
  await loadNomenclatures();
  initDefaultFilter();
};

// Одиниці виміру
const openUnitsModal = async () => {
  unitForm.name = "";
  await loadUnits();
  showUnitsModal.value = true;
};

const addUnit = async () => {
  const name = unitForm.name.trim();
  if (!name) return;
  savingUnit.value = true;
  try {
    const companyId = await getCurrentCompany();
    const { error } = await fetch("/units/", {
      method: "POST",
      body: {
        company: companyId,
        name,
        is_active: true,
      },
      headers: getAuthHeaders(),
    });
    if (error) {
      alert("Помилка додавання одиниці виміру");
      savingUnit.value = false;
      return;
    }
    unitForm.name = "";
    await loadUnits();
  } finally {
    savingUnit.value = false;
  }
};

const deleteUnit = async (unit: any) => {
  if (!confirm(`Видалити одиницю "${unit.name}"?`)) return;
  const { error } = await fetch(`/units/${unit.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert(
      "Не вдалося видалити одиницю. Можливо, вона використовується в номенклатурі.",
    );
    return;
  }
  await loadUnits();
};

onMounted(async () => {
  await Promise.all([
    loadNomenclatures(),
    loadUnits(),
    loadCategories(),
    loadCpvTree(),
  ]);
  initDefaultFilter();
});
</script>
