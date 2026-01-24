<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Права доступу</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <UTable :rows="permissions" :columns="columns" />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Права доступу'
  }
})

const config = useRuntimeConfig()
const { getAuthHeaders } = useAuth()

const columns = [
  { key: 'code', label: 'Код' },
  { key: 'label', label: 'Назва' }
]

const { data: permissionsData } = await useFetch(`${config.public.apiBase}/permissions/`, {
  headers: getAuthHeaders()
})
const permissions = computed(() => permissionsData.value || [])
</script>
