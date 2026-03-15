<template>
  <UModal :open="open" @update:open="emit('update:open', $event)" :ui="{ content: 'max-w-4xl' }">
    <template #content>
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">{{ title }}</h3>
        </template>

        <div v-if="loading" class="py-8 text-center text-sm text-gray-500">
          Завантаження...
        </div>

        <div v-else-if="items.length === 0" class="py-8 text-center text-sm text-gray-400">
          {{ emptyText }}
        </div>

        <div v-else class="max-h-[70vh] overflow-auto rounded-xl border border-gray-200">
          <table class="min-w-full text-sm">
            <thead class="bg-gray-50">
              <tr>
                <th
                  v-for="field in fields"
                  :key="field.key"
                  class="px-3 py-2 text-left font-medium text-gray-600"
                >
                  {{ field.label }}
                </th>
                <th class="px-3 py-2 text-right font-medium text-gray-600">Дії</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="getItemKey(item)"
                class="border-t border-gray-200"
              >
                <td
                  v-for="field in fields"
                  :key="field.key"
                  class="px-3 py-2 align-top text-gray-900"
                >
                  {{ formatValue(item, field.key) }}
                </td>
                <td class="px-3 py-2">
                  <div class="flex items-center justify-end gap-2">
                    <UButton
                      size="xs"
                      variant="outline"
                      color="primary"
                      icon="i-heroicons-arrow-path"
                      @click="emit('restore', item)"
                    >
                      Відновити
                    </UButton>
                    <UButton
                      size="xs"
                      variant="outline"
                      color="red"
                      icon="i-heroicons-trash"
                      @click="emit('delete', item)"
                    >
                      Видалити
                    </UButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <UButton variant="outline" @click="emit('update:open', false)">Закрити</UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
type ModalField = {
  key: string;
  label: string;
};

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    items: Record<string, any>[];
    fields: ModalField[];
    loading?: boolean;
    emptyText?: string;
    itemKey?: string;
  }>(),
  {
    loading: false,
    emptyText: "Немає деактивованих елементів.",
    itemKey: "id",
  },
);

const emit = defineEmits<{
  "update:open": [value: boolean];
  restore: [item: Record<string, any>];
  delete: [item: Record<string, any>];
}>();

function getItemKey(item: Record<string, any>) {
  return item?.[props.itemKey] ?? JSON.stringify(item);
}

function formatValue(item: Record<string, any>, key: string) {
  const value = item?.[key];
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "Так" : "Ні";
  }
  return String(value);
}
</script>
