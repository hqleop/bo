<template>
  <div class="h-full flex gap-4">
    <!-- Область 1: Категорії -->
    <div class="flex-1 border-r border-gray-200 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Категорії</h3>
        <UButton icon="i-heroicons-plus" size="sm" @click="openCategoryModal()"
          >Додати</UButton
        >
      </div>
      <div class="space-y-0 min-h-[200px]">
        <TreeItem
          v-for="cat in categories"
          :key="cat.id"
          :item="cat"
          :level="0"
          :selected-id="selectedCategory?.id"
          @select="selectCategory"
          @edit="openCategoryModal"
          @delete="deleteCategory"
        />
        <div
          v-if="categories.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Немає категорій
        </div>
      </div>
    </div>

    <!-- Область 2: Користувачі за категорією -->
    <div class="flex-1 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Користувачі за категорією</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-plus"
            size="sm"
            :disabled="!selectedCategory"
            @click="openAddUsersModal()"
          >
            Додати
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            size="sm"
            variant="outline"
            color="red"
            :disabled="!selectedCategory || selectedUsers.length === 0"
            @click="openRemoveUsersModal()"
          >
            Видалити
          </UButton>
        </div>
      </div>
      <div v-if="!selectedCategory" class="text-center text-gray-400 py-8">
        Оберіть категорію
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="user in currentUsers"
          :key="user.id"
          class="flex items-center justify-between p-2 rounded hover:bg-gray-100"
        >
          <div class="flex-1">
            <div class="font-medium">
              {{ user.user.first_name }} {{ user.user.last_name }}
            </div>
            <div class="text-sm text-gray-500">{{ user.user.email }}</div>
          </div>
          <UCheckbox
            :model-value="selectedUsers.includes(user.user.id)"
            @update:model-value="toggleUserSelection(user.user.id)"
          />
        </div>
        <div
          v-if="currentUsers.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Немає користувачів
        </div>
      </div>
    </div>

    <!-- Модальне вікно для категорії -->
    <UModal v-model="showCategoryModal">
      <UCard>
        <template #header>
          <h3>
            {{ editingCategory ? "Редагувати категорію" : "Додати категорію" }}
          </h3>
        </template>
        <UForm :state="categoryForm" @submit="saveCategory" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="categoryForm.name" />
          </UFormGroup>
          <UFormGroup label="Код" name="code">
            <UInput v-model="categoryForm.code" />
          </UFormGroup>
          <UFormGroup label="Батьківська категорія" name="parent_id">
            <USelectMenu
              :model-value="categoryForm.parent_id"
              :options="categoryParentOptions"
              value-attribute="value"
              option-attribute="label"
              placeholder="Без батьківської категорії"
              @update:model-value="
                (v) => {
                  categoryForm.parent_id = v ?? null;
                }
              "
            />
          </UFormGroup>
          <UFormGroup label="CPV" name="cpv">
            <UPopover v-model="showCpvPopover">
              <UButton class="flex-1" variant="outline">
                <span v-if="selectedCpvLabels.length">{{
                  selectedCpvLabels.join(", ")
                }}</span>
                <span v-else>Оберіть CPV</span>
              </UButton>
              <template #panel>
                <div class="p-2 w-96 max-h-80 overflow-y-auto space-y-2">
                  <UInput
                    v-model="cpvSearch"
                    size="sm"
                    placeholder="Пошук за кодом або назвою"
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    Введіть цифри — пошук по <code>cpv_code</code>, текст — по
                    назві українською.
                  </p>
                  <div class="mt-2 space-y-1">
                    <CpvTreeItem
                      v-for="node in filteredCpvTree"
                      :key="node.id"
                      :item="node"
                      :selected-ids="selectedCpvIds"
                      @toggle="toggleCpv"
                    />
                  </div>
                </div>
              </template>
            </UPopover>
          </UFormGroup>
          <UFormGroup label="Опис" name="description">
            <UTextarea v-model="categoryForm.description" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showCategoryModal = false"
              >Скасувати</UButton
            >
            <UButton type="submit" class="flex-1" :loading="saving"
              >Зберегти</UButton
            >
          </div>
        </UForm>
      </UCard>
    </UModal>

    <!-- Модальне вікно для додавання користувачів -->
    <UModal v-model="showAddUsersModal">
      <UCard>
        <template #header>
          <h3>Додати користувачів</h3>
        </template>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="user in availableCompanyUsers"
            :key="user.id"
            class="flex items-center p-2 rounded hover:bg-gray-50"
          >
            <UCheckbox
              :model-value="usersToAdd.includes(user.id)"
              @update:model-value="toggleUserToAdd(user.id)"
            />
            <div class="ml-3 flex-1">
              <div class="font-medium">
                {{ user.first_name }} {{ user.last_name }}
              </div>
              <div class="text-sm text-gray-500">{{ user.email }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showAddUsersModal = false"
              >Скасувати</UButton
            >
            <UButton class="flex-1" @click="addUsers" :loading="saving"
              >Додати</UButton
            >
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Модальне вікно для видалення користувачів -->
    <UModal v-model="showRemoveUsersModal">
      <UCard>
        <template #header>
          <h3>Видалити користувачів</h3>
        </template>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="user in currentUsers.filter((u) =>
              selectedUsers.includes(u.user.id),
            )"
            :key="user.id"
            class="flex items-center p-2 rounded hover:bg-gray-50"
          >
            <UCheckbox
              :model-value="usersToRemove.includes(user.user.id)"
              @update:model-value="toggleUserToRemove(user.user.id)"
            />
            <div class="ml-3 flex-1">
              <div class="font-medium">
                {{ user.user.first_name }} {{ user.user.last_name }}
              </div>
              <div class="text-sm text-gray-500">{{ user.user.email }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showRemoveUsersModal = false"
              >Скасувати</UButton
            >
            <UButton
              class="flex-1"
              color="red"
              @click="removeUsers"
              :loading="saving"
              >Видалити</UButton
            >
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
    title: "Категорії",
  },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const categories = ref<any[]>([]);
const currentUsers = ref<any[]>([]);
const companyUsers = ref<any[]>([]);

const selectedCategory = ref<any>(null);
const selectedUsers = ref<number[]>([]);

const showCategoryModal = ref(false);
const showAddUsersModal = ref(false);
const showRemoveUsersModal = ref(false);
const saving = ref(false);

const editingCategory = ref<any>(null);
const categoryForm = reactive({
  name: "",
  code: "",
  description: "",
  parent_id: null as number | null,
});
const usersToAdd = ref<number[]>([]);
const usersToRemove = ref<number[]>([]);

// CPV
const cpvTree = ref<any[]>([]);
const cpvSearch = ref("");
const selectedCpvIds = ref<number[]>([]);
const showCpvPopover = ref(false);

// користувачі компанії, які ще не додані до поточної категорії
const availableCompanyUsers = computed(() => {
  const assignedIds = new Set<number>(
    currentUsers.value.map((u: any) => u.user.id),
  );
  return companyUsers.value.filter((u: any) => !assignedIds.has(u.id));
});

const loadCategories = async () => {
  const { data } = await fetch("/categories/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    categories.value = data;
  }
};

const loadCpvTree = async () => {
  const { data } = await fetch("/cpv/tree/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    cpvTree.value = data;
  }
};

const loadUsers = async () => {
  if (!selectedCategory.value) {
    currentUsers.value = [];
    return;
  }
  const { data } = await fetch(
    `/category-users/?category_id=${selectedCategory.value.id}`,
    {
      headers: getAuthHeaders(),
    },
  );
  currentUsers.value = data || [];
};

const loadCompanyUsers = async () => {
  const { data } = await fetch("/memberships/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    companyUsers.value = data
      .filter((m: any) => m.status === "approved")
      .map((m: any) => m.user);
  }
};

const selectCategory = (cat: any) => {
  selectedCategory.value = cat;
  selectedCpvIds.value = (cat.cpvs || []).map((c: any) => c.id);
  selectedUsers.value = [];
  loadUsers();
};

const toggleUserSelection = (userId: number) => {
  const index = selectedUsers.value.indexOf(userId);
  if (index > -1) {
    selectedUsers.value.splice(index, 1);
  } else {
    selectedUsers.value.push(userId);
  }
};

const getCurrentCompany = async () => {
  const { data } = await fetch("/auth/me/", {
    headers: getAuthHeaders(),
  });
  if (data?.memberships?.[0]) {
    return data.memberships[0].company.id;
  }
  return null;
};

// Категорії
const openCategoryModal = (cat?: any) => {
  editingCategory.value = cat || null;
  if (cat) {
    categoryForm.name = cat.name;
    categoryForm.code = cat.code || "";
    categoryForm.description = cat.description || "";
    categoryForm.parent_id = cat.parent || null;
    selectedCpvIds.value = (cat.cpvs || []).map((c: any) => c.id);
  } else {
    categoryForm.name = "";
    categoryForm.code = "";
    categoryForm.description = "";
    categoryForm.parent_id = null;
    selectedCpvIds.value = [];
  }
  showCategoryModal.value = true;
};

const saveCategory = async () => {
  saving.value = true;
  const companyId = await getCurrentCompany();
  const payload: any = {
    name: categoryForm.name,
    code: categoryForm.code,
    description: categoryForm.description,
    company: companyId,
  };
  if (categoryForm.parent_id) {
    payload.parent = categoryForm.parent_id;
  }
  if (selectedCpvIds.value.length) {
    payload.cpv_ids = selectedCpvIds.value;
  }

  const endpoint = editingCategory.value
    ? `/categories/${editingCategory.value.id}/`
    : "/categories/";
  const method = editingCategory.value ? "PUT" : "POST";

  const { error } = await fetch(endpoint, {
    method,
    body: payload,
    headers: getAuthHeaders(),
  });

  saving.value = false;
  if (error) {
    alert(error.detail || "Помилка збереження");
    return;
  }

  showCategoryModal.value = false;
  await loadCategories();
};

const deleteCategory = async (cat: any) => {
  if (!confirm(`Видалити категорію "${cat.name}"?`)) return;

  const { error } = await fetch(`/categories/${cat.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert("Помилка видалення");
    return;
  }

  if (selectedCategory.value?.id === cat.id) {
    selectedCategory.value = null;
  }
  await loadCategories();
};

// Користувачі
const openAddUsersModal = async () => {
  usersToAdd.value = [];
  await loadCompanyUsers();
  showAddUsersModal.value = true;
};

const toggleUserToAdd = (userId: number) => {
  const index = usersToAdd.value.indexOf(userId);
  if (index > -1) {
    usersToAdd.value.splice(index, 1);
  } else {
    usersToAdd.value.push(userId);
  }
};

const addUsers = async () => {
  if (!selectedCategory.value || usersToAdd.value.length === 0) return;

  saving.value = true;
  const { error } = await fetch("/category-users/", {
    method: "POST",
    body: {
      category: selectedCategory.value.id,
      user_ids: usersToAdd.value,
    },
    headers: getAuthHeaders(),
  });

  saving.value = false;
  if (error) {
    alert(error.detail || "Помилка додавання");
    return;
  }

  showAddUsersModal.value = false;
  await loadUsers();
};

const openRemoveUsersModal = () => {
  usersToRemove.value = [...selectedUsers.value];
  showRemoveUsersModal.value = true;
};

const toggleUserToRemove = (userId: number) => {
  const index = usersToRemove.value.indexOf(userId);
  if (index > -1) {
    usersToRemove.value.splice(index, 1);
  } else {
    usersToRemove.value.push(userId);
  }
};

const removeUsers = async () => {
  if (!selectedCategory.value || usersToRemove.value.length === 0) return;

  saving.value = true;
  // Видаляємо по одному
  for (const userId of usersToRemove.value) {
    const userItem = currentUsers.value.find((u) => u.user.id === userId);
    if (userItem) {
      await fetch(`/category-users/${userItem.id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
    }
  }

  saving.value = false;
  showRemoveUsersModal.value = false;
  selectedUsers.value = [];
  await loadUsers();
};

// Допоміжні: сплощення дерева та збір id нащадків
function flattenCategories(
  catList: any[],
): { id: number; name: string; level: number }[] {
  const out: { id: number; name: string; level: number }[] = [];
  function walk(items: any[], level: number) {
    if (!items?.length) return;
    for (const item of items) {
      out.push({ id: item.id, name: item.name, level });
      walk(item.children || [], level + 1);
    }
  }
  walk(catList, 0);
  return out;
}

function getCategoryDescendantIds(cat: any): number[] {
  const ids: number[] = [cat.id];
  for (const child of cat.children || []) {
    ids.push(...getCategoryDescendantIds(child));
  }
  return ids;
}

// Опції для батьківської категорії: плоский список, без поточного та його нащадків
const categoryParentOptions = computed(() => {
  const flat = flattenCategories(categories.value);
  const excludeIds = new Set<number>();
  if (editingCategory.value) {
    getCategoryDescendantIds(editingCategory.value).forEach((id) =>
      excludeIds.add(id),
    );
  }
  const options = flat.filter((c) => !excludeIds.has(c.id));
  const withPrefix = options.map((c) => ({
    value: c.id,
    label: (c.level ? "  ".repeat(c.level) : "") + c.name,
  }));
  return [{ value: null, label: "Без батьківської категорії" }, ...withPrefix];
});

// Фільтрація дерева CPV по введеному рядку
function filterCpvTree(list: any[], predicate: (node: any) => boolean): any[] {
  const result: any[] = [];
  for (const node of list) {
    const children = node.children
      ? filterCpvTree(node.children, predicate)
      : [];
    if (predicate(node) || children.length) {
      result.push({
        ...node,
        children,
      });
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
  const labels: string[] = [];
  const allNodes: any[] = [];
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      allNodes.push(n);
      if (n.children?.length) walk(n.children);
    }
  };
  walk(cpvTree.value);
  for (const id of selectedCpvIds.value) {
    const node = allNodes.find((n) => n.id === id);
    if (node) {
      labels.push(`${node.cpv_code} - ${node.name_ua}`);
    }
  }
  return labels;
});

const toggleCpv = (id: number) => {
  const idx = selectedCpvIds.value.indexOf(id);
  if (idx > -1) {
    selectedCpvIds.value.splice(idx, 1);
  } else {
    selectedCpvIds.value.push(id);
  }
};

onMounted(async () => {
  await loadCategories();
  await loadCompanyUsers();
  await loadCpvTree();
});
</script>
