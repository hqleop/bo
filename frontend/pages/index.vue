<template>
  <div class="container mx-auto px-4 py-16 text-center">
    <h1 class="text-4xl font-bold text-gray-900 mb-4">Bid Open</h1>
    <p class="text-xl text-gray-600 mb-8">Система для проведення тендерів</p>
    <div class="flex gap-4 justify-center">
      <template v-if="isAuthenticated">
        <UButton to="/cabinet/dashboard" size="lg" color="primary">Перейти в кабінет</UButton>
      </template>
      <template v-else>
        <UButton to="/login" size="lg">Вхід</UButton>
        <UButton to="/register" size="lg" color="primary">Реєстрація</UButton>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'site'
})

const { isAuthenticated, checkAuth } = useAuth()
await checkAuth()
</script>
