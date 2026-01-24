<template>
  <NuxtLayout :name="layout">
    <slot />
  </NuxtLayout>
</template>

<script setup lang="ts">
const route = useRoute()
const layout = computed(() => {
  if (route.path.startsWith('/cabinet')) {
    return 'cabinet'
  }
  return 'site'
})
</script>
