<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Статті витрат</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">Додати статтю витрат</UButton>
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список статей витрат (MVP)</p>
      <!-- TODO: Додати таблицю зі статтями витрат -->
    </div>

    <!-- Add Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати статтю витрат</h3>
        </template>
        <UForm :state="addForm" @submit="onAdd" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormGroup>
          <UFormGroup label="Код" name="code">
            <UInput v-model="addForm.code" />
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
    title: 'Статті витрат'
  }
})

const showAddModal = ref(false)
const addForm = reactive({
  name: '',
  code: ''
})

const onAdd = () => {
  // TODO: Implement add expense article logic
  alert('Функція додавання статті витрат буде реалізована')
  showAddModal.value = false
}
</script>
