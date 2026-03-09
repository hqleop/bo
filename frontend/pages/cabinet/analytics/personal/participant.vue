<template>
  <div class="h-full min-h-0 overflow-hidden">
    <div class="inline-flex rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
      <UButton
        v-for="tab in tabs"
        :key="tab.to"
        type="button"
        size="sm"
        class="px-3"
        :variant="route.path === tab.to ? 'solid' : 'ghost'"
        @click="navigateTo(tab.to)"
      >
        {{ tab.label }}
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Персональна аналітика" },
});

const route = useRoute();

const tabs = [
  {
    label: "Участь",
    to: "/cabinet/analytics/personal/participant",
  },
  {
    label: "Проведення",
    to: "/cabinet/analytics/personal/organizer",
  },
];
</script>
