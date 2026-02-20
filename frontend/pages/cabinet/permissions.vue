<template>
  <div>
    <h2 class="text-2xl font-bold mb-4">Права доступу</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <UTable :data="permissions" :columns="columns" />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Права доступу",
  },
});

const usersUC = useUsersUseCases();
const permissions = ref<any[]>([]);

const columns = [
  { accessorKey: "code", header: "Код" },
  { accessorKey: "label", header: "Назва" },
];

onMounted(async () => {
  const { data } = await usersUC.getPermissions();
  permissions.value = data ?? [];
});
</script>
