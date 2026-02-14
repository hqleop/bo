<template>
  <div class="container mx-auto px-4 py-16 text-center">
    <h1 class="text-4xl font-bold text-gray-900 mb-4">Bid Open</h1>
    <p class="text-xl text-gray-600 mb-8">Система для проведення тендерів</p>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "site",
});

const { isAuthenticated, checkAuth } = useAuth();
await checkAuth();
</script>
