<template>
  <UApp>
    <SystemAlerts />
    <NuxtLayout>
      <NuxtPage :key="route.fullPath" />
    </NuxtLayout>
    <div
      v-if="isLoading"
      class="fixed inset-0 z-[3000] bg-white/70 backdrop-blur-[1px] flex items-center justify-center"
    >
      <div class="flex flex-col items-center gap-3 rounded-lg bg-white px-6 py-4 shadow-lg border border-gray-200">
        <UIcon name="i-heroicons-arrow-path" class="size-7 animate-spin text-primary" />
        <p class="text-sm text-gray-700">Завантаження...</p>
      </div>
    </div>
  </UApp>
</template>

<script setup lang="ts">
import { useGlobalLoader } from "~/composables/useGlobalLoader";

const route = useRoute();
const { isLoading } = useGlobalLoader();
</script>
