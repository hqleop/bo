<script setup lang="ts">
import { getAnalyticsDefaultRoute } from "~/domains/analytics/analytics.navigation";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Зведена аналітика по проведенню" },
});

await navigateTo(getAnalyticsDefaultRoute("summary-tenders"), { replace: true });
</script>
