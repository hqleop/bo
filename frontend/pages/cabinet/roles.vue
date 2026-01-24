<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Ролі</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">Створити роль</UButton>
    </div>

    <UTable :rows="roles" :columns="columns" />

    <!-- Add Role Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Створити роль</h3>
        </template>
        <UForm :state="addForm" @submit="onAddRole" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormGroup>
          <UFormGroup label="Права доступу" name="permission_ids">
            <USelectMenu
              v-model="addForm.permission_ids"
              :options="permissions"
              option-attribute="label"
              value-attribute="id"
              multiple
            />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showAddModal = false">Скасувати</UButton>
            <UButton type="submit" block>Створити</UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Ролі'
  }
})

const { fetch } = useApi()
const showAddModal = ref(false)

const columns = [
  { key: 'name', label: 'Назва' },
  { key: 'is_system', label: 'Системна' },
  { key: 'permissions', label: 'Права' },
  { key: 'actions', label: 'Дії' }
]

const config = useRuntimeConfig()
const { getAuthHeaders } = useAuth()
const { data: rolesData, refresh } = await useFetch(`${config.public.apiBase}/roles/`, {
  headers: getAuthHeaders()
})
const roles = computed(() => rolesData.value || [])

const { data: permissionsData } = await useFetch(`${config.public.apiBase}/permissions/`, {
  headers: getAuthHeaders()
})
const permissions = computed(() => permissionsData.value || [])

const addForm = reactive({
  name: '',
  permission_ids: [] as number[]
})

const onAddRole = async () => {
  // TODO: Implement add role logic
  alert('Функція створення ролі буде реалізована')
  showAddModal.value = false
}
</script>
