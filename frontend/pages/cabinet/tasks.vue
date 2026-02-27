<template>
  <div class="h-full min-h-0 flex flex-col">
    <h2 class="text-2xl font-bold mb-4">Завдання користувача</h2>
    <div
      class="flex-1 min-h-0 bg-white rounded-lg shadow p-6 text-gray-500 flex items-center justify-center"
    >
      Тут буде відображатись список завдань.
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Завдання користувача",
  },
});
</script>
