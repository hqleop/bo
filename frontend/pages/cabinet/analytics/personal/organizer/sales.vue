<template>
  <AnalyticsDashboardPage
    :mode="page.mode"
    :page-title="page.pageTitle"
    :fixed-tender-type="page.fixedTenderType"
  />
</template>

<script setup lang="ts">
import { getAnalyticsPageConfig } from "~/domains/analytics/analytics.navigation";

const page = getAnalyticsPageConfig("personal-organizer", "sales");

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: page.metaTitle },
});
</script>
