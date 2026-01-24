<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Тендери</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список тендерів (MVP)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Тендери'
  }
})
</script>
