<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Ролі</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true"
        >Створити роль</UButton
      >
    </div>

    <UTable :rows="roles" :columns="columns" />

    <!-- Add Role Modal -->
    <UModal v-model:open="showAddModal">
      <template #content>
      <UCard>
        <template #header>
          <h3>Створити роль</h3>
        </template>
        <UForm :state="addForm" @submit="onAddRole" class="space-y-4">
          <UFormField label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormField>
          <UFormField label="Права доступу" name="permission_ids">
            <USelectMenu
              v-model="addForm.permission_ids"
              :items="permissionItems"
              value-key="id"
              label-key="label"
              multiple
            />
          </UFormField>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showAddModal = false"
              >Скасувати</UButton
            >
            <UButton type="submit" class="flex-1">Створити</UButton>
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
  meta: {
    title: "Ролі",
  },
});

const { fetch } = useApi();
const showAddModal = ref(false);

const columns = [
  { key: "name", label: "Назва" },
  { key: "is_system", label: "Системна" },
  { key: "permissions", label: "Права" },
  { key: "actions", label: "Дії" },
];

const config = useRuntimeConfig();
const { getAuthHeaders } = useAuth();
const { data: rolesData, refresh } = await useFetch(
  `${config.public.apiBase}/roles/`,
  {
    headers: getAuthHeaders(),
  },
);
const roles = computed(() => rolesData.value || []);

const { data: permissionsData } = await useFetch(
  `${config.public.apiBase}/permissions/`,
  {
    headers: getAuthHeaders(),
  },
);
const permissions = computed(() => permissionsData.value || []);
const permissionItems = computed(() =>
  (permissions.value as any[]).map((p) => ({
    id: p.id,
    label: p.label ?? p.name ?? String(p.id),
  }))
);

const addForm = reactive({
  name: "",
  permission_ids: [] as number[],
});

const onAddRole = async () => {
  // TODO: Implement add role logic
  alert("Функція створення ролі буде реалізована");
  showAddModal.value = false;
};
</script>
