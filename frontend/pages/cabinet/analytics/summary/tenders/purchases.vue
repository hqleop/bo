<template>
  <AnalyticsDashboardPage
    :mode="page.mode"
    :page-title="page.pageTitle"
    :tabs="page.tabs"
    :fixed-tender-type="page.fixedTenderType"
  />
</template>

<script setup lang="ts">
import { getAnalyticsPageConfig } from "~/domains/analytics/analytics.navigation";

const page = getAnalyticsPageConfig("summary-tenders", "purchases");

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: page.metaTitle },
});
</script>
