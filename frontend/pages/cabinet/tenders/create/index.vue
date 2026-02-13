<template>
  <div />
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
});

onMounted(() => {
  navigateTo("/cabinet/tenders/create/purchase", { replace: true });
});
</script>
