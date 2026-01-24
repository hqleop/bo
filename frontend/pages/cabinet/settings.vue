<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Налаштування</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут будуть налаштування системи (MVP)</p>
      <!-- TODO: Додати форму налаштувань -->
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Налаштування'
  }
})
</script>
