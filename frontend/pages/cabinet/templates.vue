<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Шаблони</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true">Створити шаблон</UButton>
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список шаблонів (MVP)</p>
      <!-- TODO: Додати таблицю з шаблонами -->
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Шаблони'
  }
})

const showAddModal = ref(false)
</script>
