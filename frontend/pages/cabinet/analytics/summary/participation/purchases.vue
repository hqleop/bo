<template>
  <AnalyticsDashboardPage
    :mode="page.mode"
    :page-title="page.pageTitle"
    :fixed-tender-type="page.fixedTenderType"
  />
</template>

<script setup lang="ts">
import { getAnalyticsPageConfig } from "~/domains/analytics/analytics.navigation";

const page = getAnalyticsPageConfig("summary-participation", "purchases");

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: page.metaTitle },
});
</script>
