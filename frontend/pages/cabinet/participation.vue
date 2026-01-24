<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Участь в тендерах</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список участі в тендерах (MVP)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Участь в тендерах'
  }
})
</script>
