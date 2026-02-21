<template>
  <div class="pointer-events-none fixed right-4 top-4 z-[100] w-full max-w-md space-y-2">
    <UAlert
      v-for="item in alerts"
      :key="item.id"
      :title="item.title"
      :color="item.color"
      variant="soft"
      class="pointer-events-auto"
    />
  </div>
</template>

<script setup lang="ts">
const { alerts } = useSystemAlerts();
</script>
