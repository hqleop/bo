<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="container mx-auto px-4 py-4 flex justify-between items-center">
        <div class="flex items-center">
          <NuxtLink to="/">
            <h1 class="text-2xl font-bold text-gray-900">Bid Open</h1>
          </NuxtLink>
        </div>
        <div class="flex gap-4">
          <template v-if="isAuthenticated">
            <UButton to="/cabinet/dashboard" color="primary">Кабінет</UButton>
            <UButton variant="ghost" color="gray" @click="handleLogout">Вийти</UButton>
          </template>
          <template v-else>
            <UButton to="/login" variant="ghost" color="gray">Вхід</UButton>
            <UButton to="/register" color="primary">Реєстрація</UButton>
          </template>
        </div>
      </div>
    </header>

    <!-- Body -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="bg-gray-100 py-8 mt-auto">
      <div class="container mx-auto px-4 text-center text-gray-600">
        <p>&copy; 2024 Bid Open. Всі права захищені.</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const { isAuthenticated, checkAuth, logout } = useAuth()

// Перевірка автентифікації при завантаженні
await checkAuth()

const handleLogout = () => {
  logout()
}
</script>
