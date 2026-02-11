<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Користувачі</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true"
        >Додати користувача</UButton
      >
    </div>

    <UTable :rows="memberships" :columns="columns" />

    <!-- Add User Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати користувача</h3>
        </template>
        <UForm :state="addForm" @submit="onAddUser" class="space-y-4">
          <UFormGroup label="Email" name="email" required>
            <UInput v-model="addForm.email" type="email" />
          </UFormGroup>
          <UFormGroup label="Роль" name="role_id" required>
            <USelect
              v-model="addForm.role_id"
              :options="roles"
              option-attribute="name"
              value-attribute="id"
            />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showAddModal = false"
              >Скасувати</UButton
            >
            <UButton type="submit" class="flex-1">Додати</UButton>
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
const showAddModal = ref(false);

const columns = [
  { key: "user.email", label: "Email" },
  { key: "user.first_name", label: "Ім'я" },
  { key: "user.last_name", label: "Прізвище" },
  { key: "role.name", label: "Роль" },
  { key: "status", label: "Статус" },
  { key: "actions", label: "Дії" },
];

const config = useRuntimeConfig();
const { getAuthHeaders } = useAuth();
const { data: membershipsData, refresh } = await useFetch(
  `${config.public.apiBase}/memberships/`,
  {
    headers: getAuthHeaders(),
  },
);
const memberships = computed(() => membershipsData.value || []);

const { data: rolesData } = await useFetch(`${config.public.apiBase}/roles/`, {
  headers: getAuthHeaders(),
});
const roles = computed(() => rolesData.value || []);

const addForm = reactive({
  email: "",
  role_id: null as number | null,
});

const onAddUser = async () => {
  // TODO: Implement add user logic
  alert("Функція додавання користувача буде реалізована");
  showAddModal.value = false;
};
</script>
