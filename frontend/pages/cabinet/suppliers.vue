<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Постачальники</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">Додати постачальника</UButton>
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список постачальників (MVP)</p>
      <!-- TODO: Додати таблицю з постачальниками -->
    </div>

    <!-- Add Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати постачальника</h3>
        </template>
        <UForm :state="addForm" @submit="onAdd" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormGroup>
          <UFormGroup label="ЄДРПОУ" name="edrpou">
            <UInput v-model="addForm.edrpou" />
          </UFormGroup>
          <UFormGroup label="Контактна особа" name="contact_person">
            <UInput v-model="addForm.contact_person" />
          </UFormGroup>
          <UFormGroup label="Телефон" name="phone">
            <UInput v-model="addForm.phone" type="tel" />
          </UFormGroup>
          <UFormGroup label="Email" name="email">
            <UInput v-model="addForm.email" type="email" />
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
    title: 'Постачальники'
  }
})

const showAddModal = ref(false)
const addForm = reactive({
  name: '',
  edrpou: '',
  contact_person: '',
  phone: '',
  email: ''
})

const onAdd = () => {
  // TODO: Implement add supplier logic
  alert('Функція додавання постачальника буде реалізована')
  showAddModal.value = false
}
</script>
