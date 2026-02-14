<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Атрибути тендерів</h2>
    </div>
    <div class="bg-white rounded-lg border p-6">
      <p class="text-gray-600">Розділ «Атрибути тендерів» буде реалізовано пізніше.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Атрибути тендерів" },
});
</script>
