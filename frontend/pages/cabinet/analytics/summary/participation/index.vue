<script setup lang="ts">
import { getAnalyticsDefaultRoute } from "~/domains/analytics/analytics.navigation";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Зведена аналітика по участі" },
});

await navigateTo(getAnalyticsDefaultRoute("summary-participation"), { replace: true });
</script>
