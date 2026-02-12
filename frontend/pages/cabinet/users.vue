<template>
  <div class="h-full flex gap-4">
    <!-- Ліва область: список користувачів -->
    <div class="flex-[2] border-r border-gray-200 p-4 flex flex-col">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">Користувачі</h2>
        <div class="flex gap-2">
          <UButton icon="i-heroicons-plus" size="sm" @click="openAddUserModal">
            Додати користувача
          </UButton>
          <UButton
            icon="i-heroicons-user-plus"
            size="sm"
            variant="outline"
            color="green"
            :disabled="
              !selectedMembership ||
              (selectedMembership && selectedMembership.user.is_active)
            "
            @click="activateSelected"
          >
            Активувати
          </UButton>
          <UButton
            icon="i-heroicons-user-minus"
            size="sm"
            variant="outline"
            color="red"
            :disabled="
              !selectedMembership ||
              (selectedMembership && !selectedMembership.user.is_active)
            "
            @click="deactivateSelected"
          >
            Деактивувати
          </UButton>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto space-y-1">
        <div
          v-for="m in filteredMemberships"
          :key="m.id"
          class="flex items-center justify-between p-2 rounded-md cursor-pointer hover:bg-gray-50"
          :class="{
            'bg-blue-50 border border-blue-200':
              selectedMembership && selectedMembership.id === m.id,
          }"
          @click="selectedMembership = m"
        >
          <div class="flex flex-col">
            <span class="font-medium">
              {{ fullName(m.user) }}
              <span
                v-if="!m.user.is_active"
                class="ml-2 text-xs text-red-500 font-normal"
              >
                (деактивований)
              </span>
            </span>
            <span class="text-sm text-gray-600">{{ m.user.email }}</span>
            <span v-if="m.user.phone" class="text-xs text-gray-500">
              {{ m.user.phone }}
            </span>
          </div>
          <UButton
            icon="i-heroicons-pencil-square"
            size="xs"
            variant="ghost"
            @click.stop="openEditUserModal(m)"
          />
        </div>
        <div
          v-if="filteredMemberships.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Немає користувачів за вибраними фільтрами
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
          @click="clearAllFilters"
        >
          Очистити
        </UButton>
      </div>

      <UFormGroup label="Користувач">
        <UInput
          v-model="filters.userSearch"
          placeholder="Пошук по імені та прізвищу"
        />
      </UFormGroup>

      <ContentSearch
        placeholder="Оберіть філіали"
        search-placeholder="Пошук філіалу"
        :tree="branchesTree"
        :selected-ids="filters.branchIds"
        :search-term="branchSearch"
        @toggle="toggleBranchFilter"
        @update:search-term="branchSearch = $event"
      />

      <ContentSearch
        placeholder="Оберіть підрозділи"
        search-placeholder="Пошук підрозділу"
        :disabled="filters.branchIds.length === 0"
        :tree="filters.branchIds.length === 0 ? [] : filteredDepartmentsTree"
        :selected-ids="filters.departmentIds"
        :search-term="departmentSearch"
        @toggle="toggleDepartmentFilter"
        @update:search-term="departmentSearch = $event"
      />

      <ContentSearch
        placeholder="Оберіть категорії"
        search-placeholder="Пошук категорії"
        :tree="categoriesTree"
        :selected-ids="filters.categoryIds"
        :search-term="categorySearch"
        @toggle="toggleCategoryFilter"
        @update:search-term="categorySearch = $event"
      />

      <ContentSearch
        placeholder="Оберіть статті витрат"
        search-placeholder="Пошук статті витрат"
        :tree="expensesTree"
        :selected-ids="filters.expenseIds"
        :search-term="expenseSearch"
        @toggle="toggleExpenseFilter"
        @update:search-term="expenseSearch = $event"
      />
    </div>

    <!-- Модальне вікно Додати користувача -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати користувача</h3>
        </template>
        <UForm :state="addForm" @submit="onAddUser" class="space-y-4">
          <UFormGroup label="Прізвище" name="last_name" required>
            <UInput v-model="addForm.last_name" />
          </UFormGroup>
          <UFormGroup label="Ім'я" name="first_name" required>
            <UInput v-model="addForm.first_name" />
          </UFormGroup>
          <UFormGroup label="Електронна пошта" name="email" required>
            <UInput v-model="addForm.email" type="email" />
          </UFormGroup>
          <UFormGroup label="Телефон" name="phone">
            <UInput v-model="addForm.phone" />
          </UFormGroup>
          <UFormGroup label="Пароль" name="password" required>
            <UInput v-model="addForm.password" type="password" />
          </UFormGroup>
          <UFormGroup
            label="Підтвердження пароля"
            name="password_confirm"
            required
          >
            <UInput v-model="addForm.password_confirm" type="password" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showAddModal = false"
            >
              Скасувати
            </UButton>
            <UButton type="submit" class="flex-1" :loading="savingUser">
              Додати
            </UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>

    <!-- Модальне вікно Редагувати користувача -->
    <UModal v-model="showEditModal">
      <UCard>
        <template #header>
          <h3>Редагувати користувача</h3>
        </template>
        <UForm :state="editForm" @submit="onEditUser" class="space-y-4">
          <UFormGroup label="Прізвище" name="last_name">
            <UInput v-model="editForm.last_name" />
          </UFormGroup>
          <UFormGroup label="Ім'я" name="first_name">
            <UInput v-model="editForm.first_name" />
          </UFormGroup>
          <UFormGroup label="Електронна пошта" name="email" required>
            <UInput v-model="editForm.email" type="email" />
          </UFormGroup>
          <UFormGroup label="Телефон" name="phone">
            <UInput v-model="editForm.phone" />
          </UFormGroup>
          <UFormGroup
            label="Новий пароль"
            name="password"
            help="Залиште порожнім, якщо не потрібно змінювати"
          >
            <UInput v-model="editForm.password" type="password" />
          </UFormGroup>
          <UFormGroup
            label="Підтвердження пароля"
            name="password_confirm"
            help="Заповніть, якщо вказали новий пароль"
          >
            <UInput v-model="editForm.password_confirm" type="password" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showEditModal = false"
            >
              Скасувати
            </UButton>
            <UButton type="submit" class="flex-1" :loading="savingUser">
              Зберегти
            </UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Користувачі",
  },
});

const { fetch } = useApi();
const config = useRuntimeConfig();
const { getAuthHeaders } = useAuth();

const showAddModal = ref(false);
const showEditModal = ref(false);
const selectedMembership = ref<any | null>(null);
const savingUser = ref(false);

// Дані
const membershipsData = ref<any[]>([]);
const branchesTree = ref<any[]>([]);
const departmentsByBranch = ref<Record<number, any[]>>({});
const categoriesTree = ref<any[]>([]);
const expensesTree = ref<any[]>([]);

// Фільтри
const filters = reactive({
  userSearch: "",
  branchIds: [] as number[],
  departmentIds: [] as number[],
  categoryIds: [] as number[],
  expenseIds: [] as number[],
});

// Пошук у деревах
const branchSearch = ref("");
const departmentSearch = ref("");
const categorySearch = ref("");
const expenseSearch = ref("");

// Мапи user_id -> належність (заповнюються по фільтрах)
const branchFilterUserIds = ref<Set<number>>(new Set());
const departmentFilterUserIds = ref<Set<number>>(new Set());
const categoryFilterUserIds = ref<Set<number>>(new Set());
const expenseFilterUserIds = ref<Set<number>>(new Set());

// --- Завантаження даних ---
const loadMemberships = async () => {
  const { data, error } = await fetch("/memberships/", {
    headers: getAuthHeaders(),
  });
  if (!error && data) {
    membershipsData.value = data;
  }
};

const loadBranches = async () => {
  const { data } = await fetch("/branches/", {
    headers: getAuthHeaders(),
  });
  if (data) branchesTree.value = data;
};

const loadCategories = async () => {
  const { data } = await fetch("/categories/", {
    headers: getAuthHeaders(),
  });
  if (data) categoriesTree.value = data;
};

const loadExpenses = async () => {
  const { data } = await fetch("/expenses/", {
    headers: getAuthHeaders(),
  });
  if (data) expensesTree.value = data;
};

const loadDepartmentsForBranch = async (branchId: number) => {
  if (departmentsByBranch.value[branchId]) return;
  const { data } = await fetch(`/departments/?branch_id=${branchId}`, {
    headers: getAuthHeaders(),
  });
  if (data) {
    departmentsByBranch.value[branchId] = data;
  } else {
    departmentsByBranch.value[branchId] = [];
  }
};

// --- Хелпери для дерева фільтрів ---
function flattenTree(items: any[]): any[] {
  const out: any[] = [];
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      out.push(n);
      if (n.children?.length) walk(n.children);
    }
  };
  walk(items);
  return out;
}

const filteredBranchesTree = computed(() => {
  const term = branchSearch.value.trim().toLowerCase();
  if (!term) return branchesTree.value;
  const filterFn = (node: any) =>
    (node.name || "").toLowerCase().includes(term);
  return filterTree(branchesTree.value, filterFn);
});

const filteredDepartmentsTree = computed(() => {
  const term = departmentSearch.value.trim().toLowerCase();
  const roots: any[] = [];
  for (const branchId of filters.branchIds) {
    const depts = departmentsByBranch.value[branchId] || [];
    roots.push(...depts);
  }
  if (!term) return roots;
  const filterFn = (node: any) =>
    (node.name || "").toLowerCase().includes(term);
  return filterTree(roots, filterFn);
});

const filteredCategoriesTree = computed(() => {
  const term = categorySearch.value.trim().toLowerCase();
  if (!term) return categoriesTree.value;
  const filterFn = (node: any) =>
    (node.name || "").toLowerCase().includes(term);
  return filterTree(categoriesTree.value, filterFn);
});

const filteredExpensesTree = computed(() => {
  const term = expenseSearch.value.trim().toLowerCase();
  if (!term) return expensesTree.value;
  const filterFn = (node: any) =>
    (node.name || "").toLowerCase().includes(term);
  return filterTree(expensesTree.value, filterFn);
});

function filterTree(list: any[], predicate: (node: any) => boolean): any[] {
  const result: any[] = [];
  for (const node of list) {
    const children = node.children ? filterTree(node.children, predicate) : [];
    if (predicate(node) || children.length) {
      result.push({ ...node, children });
    }
  }
  return result;
}

// Лейбли обраних елементів
const selectedBranchLabels = computed(() => {
  const flat = flattenTree(branchesTree.value);
  return filters.branchIds
    .map((id) => flat.find((n) => n.id === id)?.name)
    .filter(Boolean) as string[];
});

const selectedDepartmentLabels = computed(() => {
  const flat: any[] = [];
  Object.values(departmentsByBranch.value).forEach((arr: any) => {
    flat.push(...flattenTree(arr as any[]));
  });
  return filters.departmentIds
    .map((id) => flat.find((n) => n.id === id)?.name)
    .filter(Boolean) as string[];
});

const selectedCategoryLabels = computed(() => {
  const flat = flattenTree(categoriesTree.value);
  return filters.categoryIds
    .map((id) => flat.find((n) => n.id === id)?.name)
    .filter(Boolean) as string[];
});

const selectedExpenseLabels = computed(() => {
  const flat = flattenTree(expensesTree.value);
  return filters.expenseIds
    .map((id) => flat.find((n) => n.id === id)?.name)
    .filter(Boolean) as string[];
});

// --- Оновлення userIds для фільтрів ---
const updateBranchFilterUserIds = async () => {
  const ids = new Set<number>();
  await Promise.all(
    filters.branchIds.map(async (branchId) => {
      const { data } = await fetch(`/branch-users/?branch_id=${branchId}`, {
        headers: getAuthHeaders(),
      });
      if (data) {
        (data as any[]).forEach((bu: any) => ids.add(bu.user.id));
      }
    }),
  );
  branchFilterUserIds.value = ids;
};

const updateDepartmentFilterUserIds = async () => {
  const ids = new Set<number>();
  await Promise.all(
    filters.departmentIds.map(async (deptId) => {
      const { data } = await fetch(
        `/department-users/?department_id=${deptId}`,
        { headers: getAuthHeaders() },
      );
      if (data) {
        (data as any[]).forEach((du: any) => ids.add(du.user.id));
      }
    }),
  );
  departmentFilterUserIds.value = ids;
};

const updateCategoryFilterUserIds = async () => {
  const ids = new Set<number>();
  await Promise.all(
    filters.categoryIds.map(async (catId) => {
      const { data } = await fetch(`/category-users/?category_id=${catId}`, {
        headers: getAuthHeaders(),
      });
      if (data) {
        (data as any[]).forEach((cu: any) => ids.add(cu.user.id));
      }
    }),
  );
  categoryFilterUserIds.value = ids;
};

const updateExpenseFilterUserIds = async () => {
  const ids = new Set<number>();
  await Promise.all(
    filters.expenseIds.map(async (expId) => {
      const { data } = await fetch(`/expense-users/?expense_id=${expId}`, {
        headers: getAuthHeaders(),
      });
      if (data) {
        (data as any[]).forEach((eu: any) => ids.add(eu.user.id));
      }
    }),
  );
  expenseFilterUserIds.value = ids;
};

// Обробники перемикання фільтрів
const toggleBranchFilter = async (id: number) => {
  const idx = filters.branchIds.indexOf(id);
  if (idx > -1) {
    filters.branchIds.splice(idx, 1);
    // Якщо видаляємо філіал, очищаємо підрозділи цього філіалу з фільтрів
    const branchDepts = departmentsByBranch.value[id] || [];
    const branchDeptIds = flattenTree(branchDepts).map((d: any) => d.id);
    filters.departmentIds = filters.departmentIds.filter(
      (deptId) => !branchDeptIds.includes(deptId),
    );
    await updateDepartmentFilterUserIds();
  } else {
    filters.branchIds.push(id);
    // Підвантажуємо департаменти для обраної гілки
    await loadDepartmentsForBranch(id);
  }
  await updateBranchFilterUserIds();
};

const toggleDepartmentFilter = async (id: number) => {
  const idx = filters.departmentIds.indexOf(id);
  if (idx > -1) filters.departmentIds.splice(idx, 1);
  else filters.departmentIds.push(id);
  await updateDepartmentFilterUserIds();
};

const toggleCategoryFilter = async (id: number) => {
  const idx = filters.categoryIds.indexOf(id);
  if (idx > -1) filters.categoryIds.splice(idx, 1);
  else filters.categoryIds.push(id);
  await updateCategoryFilterUserIds();
};

const toggleExpenseFilter = async (id: number) => {
  const idx = filters.expenseIds.indexOf(id);
  if (idx > -1) filters.expenseIds.splice(idx, 1);
  else filters.expenseIds.push(id);
  await updateExpenseFilterUserIds();
};

// Автоматичне оновлення userIds при зміні фільтрів
watch(
  () => [...filters.branchIds],
  async () => {
    if (filters.branchIds.length > 0) {
      await updateBranchFilterUserIds();
    } else {
      branchFilterUserIds.value = new Set();
    }
  },
  { deep: true },
);

watch(
  () => [...filters.departmentIds],
  async () => {
    if (filters.departmentIds.length > 0) {
      await updateDepartmentFilterUserIds();
    } else {
      departmentFilterUserIds.value = new Set();
    }
  },
  { deep: true },
);

watch(
  () => [...filters.categoryIds],
  async () => {
    if (filters.categoryIds.length > 0) {
      await updateCategoryFilterUserIds();
    } else {
      categoryFilterUserIds.value = new Set();
    }
  },
  { deep: true },
);

watch(
  () => [...filters.expenseIds],
  async () => {
    if (filters.expenseIds.length > 0) {
      await updateExpenseFilterUserIds();
    } else {
      expenseFilterUserIds.value = new Set();
    }
  },
  { deep: true },
);

// --- Обчислення відфільтрованого списку ---
const memberships = computed(() => membershipsData.value || []);

const filteredMemberships = computed(() => {
  let list = memberships.value as any[];

  // Пошук по ПІБ
  const term = filters.userSearch.trim().toLowerCase();
  if (term) {
    list = list.filter((m) => fullName(m.user).toLowerCase().includes(term));
  }

  // Фільтр по філіалах (об'єднання - користувачі з будь-якого обраного філіалу)
  if (filters.branchIds.length > 0) {
    if (branchFilterUserIds.value.size === 0) {
      // Якщо ще не завантажені дані, повертаємо порожній список
      return [];
    }
    list = list.filter((m) => branchFilterUserIds.value.has(m.user.id));
  }

  // Фільтр по підрозділах (об'єднання - користувачі з будь-якого обраного підрозділу)
  if (filters.departmentIds.length > 0) {
    if (departmentFilterUserIds.value.size === 0) {
      return [];
    }
    list = list.filter((m) => departmentFilterUserIds.value.has(m.user.id));
  }

  // Фільтр по категоріях (об'єднання - користувачі з будь-якої обраної категорії)
  if (filters.categoryIds.length > 0) {
    if (categoryFilterUserIds.value.size === 0) {
      return [];
    }
    list = list.filter((m) => categoryFilterUserIds.value.has(m.user.id));
  }

  // Фільтр по статтях витрат (об'єднання - користувачі з будь-якої обраної статті)
  if (filters.expenseIds.length > 0) {
    if (expenseFilterUserIds.value.size === 0) {
      return [];
    }
    list = list.filter((m) => expenseFilterUserIds.value.has(m.user.id));
  }

  return list;
});

// --- Додавання / редагування / деактивація ---
const addForm = reactive({
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  password: "",
  password_confirm: "",
});

const editForm = reactive({
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  password: "",
  password_confirm: "",
});

const fullName = (user: any) =>
  `${user.last_name || ""} ${user.first_name || ""}`.trim() || user.email;

const openAddUserModal = () => {
  addForm.first_name = "";
  addForm.last_name = "";
  addForm.email = "";
  addForm.phone = "";
  addForm.password = "";
  addForm.password_confirm = "";
  showAddModal.value = true;
};

const openEditUserModal = (m: any) => {
  selectedMembership.value = m;
  editForm.first_name = m.user.first_name || "";
  editForm.last_name = m.user.last_name || "";
  editForm.email = m.user.email || "";
  editForm.phone = m.user.phone || "";
  editForm.password = "";
  editForm.password_confirm = "";
  showEditModal.value = true;
};

const onAddUser = async () => {
  if (addForm.password !== addForm.password_confirm) {
    alert("Паролі не співпадають");
    return;
  }
  savingUser.value = true;
  const payload = {
    first_name: addForm.first_name,
    last_name: addForm.last_name,
    middle_name: "",
    phone: addForm.phone,
    email: addForm.email,
    password: addForm.password,
  };
  const { error } = await fetch("/memberships/create-user/", {
    method: "POST",
    body: payload,
    headers: getAuthHeaders(),
  });
  savingUser.value = false;
  if (error) {
    alert("Помилка створення користувача");
    return;
  }
  showAddModal.value = false;
  await loadMemberships();
};

const onEditUser = async () => {
  if (!selectedMembership.value) return;
  if (editForm.password && editForm.password !== editForm.password_confirm) {
    alert("Паролі не співпадають");
    return;
  }
  savingUser.value = true;
  const body: Record<string, string> = {
    first_name: editForm.first_name,
    last_name: editForm.last_name,
    email: editForm.email,
    phone: editForm.phone,
  };
  if (editForm.password) {
    body.password = editForm.password;
    body.password_confirm = editForm.password_confirm;
  }
  const { error } = await fetch(
    `/memberships/${selectedMembership.value.id}/update-user/`,
    {
      method: "PATCH",
      body,
      headers: getAuthHeaders(),
    },
  );
  savingUser.value = false;
  if (error) {
    alert("Помилка оновлення даних користувача");
    return;
  }
  showEditModal.value = false;
  await loadMemberships();
};

const activateSelected = async () => {
  if (!selectedMembership.value) return;
  if (
    !confirm(
      `Активувати користувача ${fullName(
        selectedMembership.value.user,
      )}? Він зможе входити в систему.`,
    )
  ) {
    return;
  }
  const { error } = await fetch(
    `/memberships/${selectedMembership.value.id}/activate/`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );
  if (error) {
    alert("Помилка активації користувача");
    return;
  }
  await loadMemberships();
};

const deactivateSelected = async () => {
  if (!selectedMembership.value) return;
  if (
    !confirm(
      `Деактивувати користувача ${fullName(
        selectedMembership.value.user,
      )}? Він більше не зможе входити в систему.`,
    )
  ) {
    return;
  }
  const { error } = await fetch(
    `/memberships/${selectedMembership.value.id}/deactivate/`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    },
  );
  if (error) {
    alert("Помилка деактивації користувача");
    return;
  }
  await loadMemberships();
};

onMounted(async () => {
  await loadMemberships();
  await loadBranches();
  await loadCategories();
  await loadExpenses();
});

const clearAllFilters = () => {
  filters.userSearch = "";

  filters.branchIds = [];
  filters.departmentIds = [];
  filters.categoryIds = [];
  filters.expenseIds = [];

  branchSearch.value = "";
  departmentSearch.value = "";
  categorySearch.value = "";
  expenseSearch.value = "";

  branchFilterUserIds.value = new Set();
  departmentFilterUserIds.value = new Set();
  categoryFilterUserIds.value = new Set();
  expenseFilterUserIds.value = new Set();
};
</script>
