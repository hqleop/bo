<script setup lang="ts">
import { getAnalyticsDefaultRoute } from "~/domains/analytics/analytics.navigation";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Персональна аналітика учасника" },
});

await navigateTo(getAnalyticsDefaultRoute("personal-participant"), { replace: true });
</script>
