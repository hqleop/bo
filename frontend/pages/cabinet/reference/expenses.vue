<template>
  <div class="h-full flex gap-4">
    <!-- Область 1: Статті витрат -->
    <div class="flex-1 border-r border-gray-200 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Статті витрат</h3>
        <UButton icon="i-heroicons-plus" size="sm" @click="openExpenseModal()">
          Додати
        </UButton>
      </div>
      <div class="space-y-0 min-h-[200px]">
        <TreeItem
          v-for="exp in expenses"
          :key="exp.id"
          :item="exp"
          :level="0"
          :selected-id="selectedExpense?.id"
          @select="selectExpense"
          @edit="openExpenseModal"
          @delete="deleteExpense"
        />
        <div
          v-if="expenses.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Немає статей витрат
        </div>
      </div>
    </div>

    <!-- Область 2: Користувачі -->
    <div class="flex-1 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Користувачі</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-plus"
            size="sm"
            :disabled="!selectedExpense"
            @click="openAddUsersModal()"
          >
            Додати
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            size="sm"
            variant="outline"
            color="red"
            :disabled="!selectedExpense || selectedUsers.length === 0"
            @click="openRemoveUsersModal()"
          >
            Видалити
          </UButton>
        </div>
      </div>
      <div v-if="!selectedExpense" class="text-center text-gray-400 py-8">
        Оберіть статтю витрат
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

    <!-- Модальне вікно для статті витрат -->
    <UModal v-model="showExpenseModal">
      <UCard>
        <template #header>
          <h3>
            {{
              editingExpense
                ? "Редагувати статтю витрат"
                : "Додати статтю витрат"
            }}
          </h3>
        </template>
        <UForm :state="expenseForm" @submit="saveExpense" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="expenseForm.name" />
          </UFormGroup>
          <UFormGroup label="Код" name="code">
            <UInput v-model="expenseForm.code" />
          </UFormGroup>
          <UFormGroup label="Батьківська стаття" name="parent_id">
            <USelectMenu
              :model-value="expenseForm.parent_id"
              :options="expenseParentOptions"
              value-attribute="value"
              option-attribute="label"
              placeholder="Без батьківської статті"
              @update:model-value="
                (v) => {
                  expenseForm.parent_id = v ?? null;
                }
              "
            />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-4">
            <UFormGroup label="Рік початку дії" name="year_start">
              <UInput v-model="expenseForm.year_start" type="number" />
            </UFormGroup>
            <UFormGroup label="Рік завершення дії" name="year_end">
              <UInput v-model="expenseForm.year_end" type="number" />
            </UFormGroup>
          </div>
          <UFormGroup label="Опис" name="description">
            <UTextarea v-model="expenseForm.description" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showExpenseModal = false"
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
            >
              Скасувати
            </UButton>
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
            >
              Скасувати
            </UButton>
            <UButton
              class="flex-1"
              color="red"
              @click="removeUsers"
              :loading="saving"
            >
              Видалити
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
    title: "Статті витрат",
  },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const expenses = ref<any[]>([]);
const currentUsers = ref<any[]>([]);
const companyUsers = ref<any[]>([]);
const selectedExpense = ref<any>(null);
const selectedUsers = ref<number[]>([]);

const showExpenseModal = ref(false);
const showAddUsersModal = ref(false);
const showRemoveUsersModal = ref(false);
const saving = ref(false);

const editingExpense = ref<any>(null);
const currentYear = new Date().getFullYear();
const expenseForm = reactive({
  name: "",
  code: "",
  parent_id: null as number | null,
  year_start: currentYear,
  year_end: null as number | null,
  description: "",
});
const usersToAdd = ref<number[]>([]);
const usersToRemove = ref<number[]>([]);

// користувачі компанії, які ще не додані до поточної статті витрат
const availableCompanyUsers = computed(() => {
  const assignedIds = new Set<number>(
    currentUsers.value.map((u: any) => u.user.id),
  );
  return companyUsers.value.filter((u: any) => !assignedIds.has(u.id));
});

const loadExpenses = async () => {
  const { data } = await fetch("/expenses/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    expenses.value = data;
  }
};

const loadUsers = async () => {
  if (!selectedExpense.value) {
    currentUsers.value = [];
    return;
  }
  const { data } = await fetch(
    `/expense-users/?expense_id=${selectedExpense.value.id}`,
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

const selectExpense = (exp: any) => {
  selectedExpense.value = exp;
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

// Статті витрат
const openExpenseModal = (exp?: any) => {
  editingExpense.value = exp || null;
  if (exp) {
    expenseForm.name = exp.name;
    expenseForm.code = exp.code || "";
    expenseForm.parent_id = exp.parent || null;
    expenseForm.year_start = exp.year_start || currentYear;
    expenseForm.year_end = exp.year_end || null;
    expenseForm.description = exp.description || "";
  } else {
    expenseForm.name = "";
    expenseForm.code = "";
    expenseForm.parent_id = null;
    expenseForm.year_start = currentYear;
    expenseForm.year_end = null;
    expenseForm.description = "";
  }
  showExpenseModal.value = true;
};

const saveExpense = async () => {
  saving.value = true;
  const companyId = await getCurrentCompany();
  const payload: any = {
    name: expenseForm.name,
    code: expenseForm.code,
    company: companyId,
    year_start: expenseForm.year_start,
    year_end: expenseForm.year_end,
    description: expenseForm.description,
  };
  if (expenseForm.parent_id) {
    payload.parent = expenseForm.parent_id;
  }

  const endpoint = editingExpense.value
    ? `/expenses/${editingExpense.value.id}/`
    : "/expenses/";
  const method = editingExpense.value ? "PUT" : "POST";

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

  showExpenseModal.value = false;
  await loadExpenses();
};

const deleteExpense = async (exp: any) => {
  if (!confirm(`Видалити статтю витрат "${exp.name}"?`)) return;

  const { error } = await fetch(`/expenses/${exp.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert("Помилка видалення");
    return;
  }

  if (selectedExpense.value?.id === exp.id) {
    selectedExpense.value = null;
  }
  await loadExpenses();
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
  if (!selectedExpense.value || usersToAdd.value.length === 0) return;

  saving.value = true;
  const { error } = await fetch("/expense-users/", {
    method: "POST",
    body: {
      expense: selectedExpense.value.id,
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
  if (!selectedExpense.value || usersToRemove.value.length === 0) return;

  saving.value = true;
  // Видаляємо по одному
  for (const userId of usersToRemove.value) {
    const userItem = currentUsers.value.find((u) => u.user.id === userId);
    if (userItem) {
      await fetch(`/expense-users/${userItem.id}/`, {
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
function flattenExpenses(
  list: any[],
): { id: number; name: string; level: number }[] {
  const out: { id: number; name: string; level: number }[] = [];
  function walk(items: any[], level: number) {
    if (!items?.length) return;
    for (const item of items) {
      out.push({ id: item.id, name: item.name, level });
      walk(item.children || [], level + 1);
    }
  }
  walk(list, 0);
  return out;
}

function getExpenseDescendantIds(exp: any): number[] {
  const ids: number[] = [exp.id];
  for (const child of exp.children || []) {
    ids.push(...getExpenseDescendantIds(child));
  }
  return ids;
}

// Опції для батьківської статті: плоский список, без поточної та її нащадків
const expenseParentOptions = computed(() => {
  const flat = flattenExpenses(expenses.value);
  const excludeIds = new Set<number>();
  if (editingExpense.value) {
    getExpenseDescendantIds(editingExpense.value).forEach((id) =>
      excludeIds.add(id),
    );
  }
  const options = flat.filter((e) => !excludeIds.has(e.id));
  const withPrefix = options.map((e) => ({
    value: e.id,
    label: (e.level ? "  ".repeat(e.level) : "") + e.name,
  }));
  return [{ value: null, label: "Без батьківської статті" }, ...withPrefix];
});

onMounted(async () => {
  await loadExpenses();
  await loadCompanyUsers();
});
</script>
