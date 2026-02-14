<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage :key="route.fullPath" />
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
const route = useRoute();
</script>
