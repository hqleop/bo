<script setup lang="ts">
import { getAnalyticsDefaultRoute } from "~/domains/analytics/analytics.navigation";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Персональна аналітика організатора" },
});

await navigateTo(getAnalyticsDefaultRoute("personal-organizer"), { replace: true });
</script>
