<template>
  <div class="h-full min-h-0 flex items-center justify-center text-sm text-gray-500">
    Перенаправлення...
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Аналітика",
  },
});

const route = useRoute();
const target = computed(() =>
  route.query.view === "summary"
    ? "/cabinet/analytics/summary/participation"
    : "/cabinet/analytics/personal/participant",
);

await navigateTo(target.value, { replace: true });
</script>
