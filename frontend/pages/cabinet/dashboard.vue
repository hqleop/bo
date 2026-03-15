<template>
  <div class="h-full min-h-0 flex items-center justify-center text-sm text-gray-500">
    Перенаправлення...
  </div>
</template>

<script setup lang="ts">
import { getAnalyticsDefaultRoute } from "~/domains/analytics/analytics.navigation";

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
    ? getAnalyticsDefaultRoute("summary-participation")
    : getAnalyticsDefaultRoute("personal-participant"),
);

await navigateTo(target.value, { replace: true });
</script>
