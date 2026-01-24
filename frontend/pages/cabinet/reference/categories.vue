<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Категорії</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">Додати категорію</UButton>
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список категорій (MVP)</p>
      <!-- TODO: Додати таблицю з категоріями -->
    </div>

    <!-- Add Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати категорію</h3>
        </template>
        <UForm :state="addForm" @submit="onAdd" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormGroup>
          <UFormGroup label="Опис" name="description">
            <UTextarea v-model="addForm.description" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showAddModal = false">Скасувати</UButton>
            <UButton type="submit" block>Додати</UButton>
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
    title: 'Категорії'
  }
})

const showAddModal = ref(false)
const addForm = reactive({
  name: '',
  description: ''
})

const onAdd = () => {
  // TODO: Implement add category logic
  alert('Функція додавання категорії буде реалізована')
  showAddModal.value = false
}
</script>
