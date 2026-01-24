<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Загальна аналітика</h2>
    <p class="text-gray-600">Тут буде аналітика (MVP)</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Загальна аналітика'
  }
})
</script>
