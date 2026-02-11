<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Номенклатури</h2>
      <UButton icon="i-heroicons-plus" @click="showAddModal = true"
        >Додати номенклатуру</UButton
      >
    </div>

    <div class="bg-white rounded-lg shadow p-6">
      <p class="text-gray-600">Тут буде список номенклатур (MVP)</p>
      <!-- TODO: Додати таблицю з номенклатурами -->
    </div>

    <!-- Add Modal -->
    <UModal v-model="showAddModal">
      <UCard>
        <template #header>
          <h3>Додати номенклатуру</h3>
        </template>
        <UForm :state="addForm" @submit="onAdd" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="addForm.name" />
          </UFormGroup>
          <UFormGroup label="Код" name="code">
            <UInput v-model="addForm.code" />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton
              variant="outline"
              class="flex-1"
              @click="showAddModal = false"
              >Скасувати</UButton
            >
            <UButton type="submit" class="flex-1">Додати</UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Номенклатури",
  },
});

const showAddModal = ref(false);
const addForm = reactive({
  name: "",
  code: "",
});

const onAdd = () => {
  // TODO: Implement add nomenclature logic
  alert("Функція додавання номенклатури буде реалізована");
  showAddModal.value = false;
};
</script>
