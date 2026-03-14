<template>
  <div class="h-full grid grid-cols-1 xl:grid-cols-2 gap-4">
    <!-- Область 1: Статті бюджету -->
    <div class="min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Статті бюджету</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-archive-box"
            size="sm"
            variant="outline"
            @click="openInactiveExpensesModal"
          >
            Деактивовані елементи
          </UButton>
          <UButton icon="i-heroicons-plus" size="sm" @click="openExpenseModal()">
          Додати
        </UButton>
        </div>
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
          @deactivate="deactivateExpense"
          @delete="deleteExpense"
        />
        <div
          v-if="expenses.length === 0"
          class="text-center text-gray-400 py-8"
        >
          Немає статей бюджету
        </div>
      </div>
    </div>

    <!-- Область 2: Користувачі -->
    <div class="min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Користувачі</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-arrow-up-tray"
            size="sm"
            variant="outline"
            color="neutral"
            :disabled="!canCopyUsersToParent"
            title="Скопіювати користувачів у батьківську сутність"
            aria-label="Скопіювати користувачів у батьківську сутність"
            @click="copyUsers('parent')"
          />
          <UButton
            icon="i-heroicons-arrow-down-tray"
            size="sm"
            variant="outline"
            color="neutral"
            :disabled="!canCopyUsersToDescendants"
            title="Скопіювати користувачів у підлеглі сутності"
            aria-label="Скопіювати користувачів у підлеглі сутності"
            @click="copyUsers('descendants')"
          />
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
        Оберіть статтю бюджету
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

    <!-- Модальне вікно для статті бюджету -->
    <UModal v-model:open="showExpenseModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{
                editingExpense
                  ? "Редагувати статтю бюджету"
                  : "Додати статтю бюджету"
              }}
            </h3>
          </template>
          <UForm :state="expenseForm" @submit="saveExpense" class="space-y-4">
            <UFormField label="Назва" name="name" required>
              <UInput v-model="expenseForm.name" class="w-full" />
            </UFormField>
            <UFormField label="Код" name="code">
              <UInput v-model="expenseForm.code" class="w-full" />
            </UFormField>
            <UFormField label="Батьківська стаття" name="parent_id">
              <USelectMenu
                v-model="expenseForm.parent_id"
                :items="expenseParentOptions"
                value-key="value"
                placeholder="Без батьківської статті"
                class="w-full"
              />
            </UFormField>
            <div class="grid grid-cols-2 gap-4">
              <UFormField label="Рік початку дії" name="year_start">
                <UInput v-model="expenseForm.year_start" type="number" class="w-full" />
              </UFormField>
              <UFormField label="Рік завершення дії" name="year_end">
                <UInput v-model="expenseForm.year_end" type="number" class="w-full" />
              </UFormField>
            </div>
            <UFormField label="Опис" name="description">
              <UTextarea v-model="expenseForm.description" class="w-full" />
            </UFormField>
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
      </template>
    </UModal>

    <!-- Модальне вікно для додавання користувачів -->
    <UModal v-model:open="showAddUsersModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>Додати користувачів</h3>
          </template>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="user in availableCompanyUsers"
              :key="user.id"
              class="flex cursor-pointer items-center p-2 rounded hover:bg-gray-50"
              @click="toggleUserToAdd(user.id)"
            >
              <UCheckbox
                :model-value="usersToAdd.includes(user.id)"
                @update:model-value="toggleUserToAdd(user.id)"
                @click.stop
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
      </template>
    </UModal>

    <!-- Модальне вікно для видалення користувачів -->
    <UModal v-model:open="showRemoveUsersModal">
      <template #content>
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
              class="flex cursor-pointer items-center p-2 rounded hover:bg-gray-50"
              @click="toggleUserToRemove(user.user.id)"
            >
              <UCheckbox
                :model-value="usersToRemove.includes(user.user.id)"
                @update:model-value="toggleUserToRemove(user.user.id)"
                @click.stop
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
      </template>
    </UModal>

    <InactiveItemsModal
      :open="showInactiveExpensesModal"
      title="Деактивовані статті бюджету"
      :items="inactiveExpenses"
      :fields="inactiveExpenseFields"
      :loading="loadingInactiveExpenses"
      empty-text="Немає деактивованих статей бюджету."
      @update:open="showInactiveExpensesModal = $event"
      @restore="restoreExpense"
      @delete="deleteInactiveExpense"
    />
  </div>
</template>

<script setup lang="ts">
import { getApiErrorMessage } from "~/shared/api/error";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Статті бюджету",
  },
});

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();
const { getCurrentCompanyId } = useCurrentCompanyId();
const toast = useToast();

const expenses = ref<any[]>([]);
const inactiveExpenses = ref<any[]>([]);
const currentUsers = ref<any[]>([]);
const companyUsers = ref<any[]>([]);
const selectedExpense = ref<any>(null);
const selectedUsers = ref<number[]>([]);

const showExpenseModal = ref(false);
const showAddUsersModal = ref(false);
const showRemoveUsersModal = ref(false);
const showInactiveExpensesModal = ref(false);
const saving = ref(false);
const loadingInactiveExpenses = ref(false);

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

// користувачі компанії, які ще не додані до поточної статті бюджету
const availableCompanyUsers = computed(() => {
  const assignedIds = new Set<number>(
    currentUsers.value.map((u: any) => u.user.id),
  );
  return companyUsers.value.filter((u: any) => !assignedIds.has(u.id));
});

const canCopyUsersToParent = computed(
  () => Boolean(selectedExpense.value?.parent) && currentUsers.value.length > 0,
);
const canCopyUsersToDescendants = computed(
  () =>
    Array.isArray(selectedExpense.value?.children) &&
    selectedExpense.value.children.length > 0 &&
    currentUsers.value.length > 0,
);

const inactiveExpenseFields = [
  { key: "name", label: "Назва" },
  { key: "code", label: "Код" },
  { key: "year_start", label: "Рік з" },
  { key: "year_end", label: "Рік по" },
];

const loadExpenses = async () => {
  const { data } = await fetch("/expenses/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    expenses.value = data;
  }
};

const loadInactiveExpenses = async () => {
  loadingInactiveExpenses.value = true;
  const { data } = await fetch("/expenses/?inactive_only=1&flat=1", {
    headers: getAuthHeaders(),
  });
  inactiveExpenses.value = Array.isArray(data) ? data : [];
  loadingInactiveExpenses.value = false;
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

// Статті бюджету
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
  const companyId = await getCurrentCompanyId();
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
    alert(getApiErrorMessage(error, "Помилка збереження"));
    return;
  }

  showExpenseModal.value = false;
  await loadExpenses();
};

const deleteExpense = async (exp: any) => {
  if (!confirm(`Видалити статтю бюджету "${exp.name}"?`)) return;

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

const deactivateExpense = async (exp: any) => {
  if (!confirm(`Деактивувати статтю бюджету "${exp.name}"?`)) return;

  const { error } = await fetch(`/expenses/${exp.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося деактивувати статтю бюджету"));
    return;
  }

  if (selectedExpense.value?.id === exp.id) {
    selectedExpense.value = null;
    currentUsers.value = [];
    selectedUsers.value = [];
  }

  await loadExpenses();
};

const openInactiveExpensesModal = async () => {
  showInactiveExpensesModal.value = true;
  await loadInactiveExpenses();
};

const restoreExpense = async (exp: any) => {
  const { error } = await fetch(`/expenses/${exp.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося відновити статтю бюджету"));
    return;
  }

  await Promise.all([loadExpenses(), loadInactiveExpenses()]);
};

const deleteInactiveExpense = async (exp: any) => {
  if (!confirm(`Видалити статтю бюджету "${exp.name}" остаточно?`)) return;

  const { error } = await fetch(`/expenses/${exp.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося видалити статтю бюджету"));
    return;
  }

  await Promise.all([loadExpenses(), loadInactiveExpenses()]);
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
    alert(getApiErrorMessage(error, "Помилка додавання"));
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

const copyUsers = async (direction: "parent" | "descendants") => {
  if (!selectedExpense.value) return;

  saving.value = true;
  const endpoint =
    direction === "parent"
      ? "/expense-users/copy-parent/"
      : "/expense-users/copy-descendants/";
  const { data, error } = await fetch(endpoint, {
    method: "POST",
    body: { expense: selectedExpense.value.id },
    headers: getAuthHeaders(),
  });
  saving.value = false;

  if (error) {
    toast.add({
      title: getApiErrorMessage(error, "Не вдалося скопіювати користувачів"),
      color: "error",
    });
    return;
  }

  toast.add({
    title:
      Number((data as any)?.created_count || 0) > 0
        ? `Скопійовано користувачів: ${(data as any)?.created_count || 0}`
        : "Нових користувачів для копіювання не знайдено",
    color: "success",
  });
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
