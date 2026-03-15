<template>
  <UModal :open="open" @update:open="emit('update:open', $event)">
    <template #content>
      <UCard>
        <template #header>
          <h3>{{ title }}</h3>
        </template>

        <div class="space-y-4">
          <UInput
            v-model="search"
            placeholder="Пошук складу"
            size="sm"
            class="w-full"
          />

          <div class="h-[420px] overflow-auto rounded-lg border border-gray-200 p-3">
            <div v-if="loading" class="py-4 text-center text-sm text-gray-500">
              Завантаження складів...
            </div>
            <div
              v-else-if="!filteredGroups.length"
              class="py-4 text-center text-sm text-gray-500"
            >
              Немає доступних складів.
            </div>
            <div v-else class="space-y-4">
              <section
                v-for="group in filteredGroups"
                :key="group.region"
                class="space-y-2"
              >
                <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {{ group.region }}
                </div>
                <button
                  v-for="warehouse in group.items"
                  :key="warehouse.id"
                  type="button"
                  class="w-full rounded-lg border px-3 py-2 text-left transition"
                  :class="
                    warehouse.id === selectedWarehouseId
                      ? 'border-primary bg-primary-50'
                      : 'border-gray-200 hover:border-primary/50 hover:bg-gray-50'
                  "
                  @click="emit('select', warehouse)"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="font-medium text-gray-900">{{ warehouse.name }}</div>
                      <div class="text-xs text-gray-500">
                        {{ warehouse.warehouse_type_label || "Склад" }}
                      </div>
                      <div class="mt-1 text-sm text-gray-600">
                        {{ warehouse.full_address || "Адреса не заповнена" }}
                      </div>
                    </div>
                    <UIcon
                      v-if="warehouse.id === selectedWarehouseId"
                      name="i-heroicons-check-circle"
                      class="size-5 shrink-0 text-primary"
                    />
                  </div>
                </button>
              </section>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <UButton variant="outline" @click="emit('update:open', false)">
              Закрити
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean;
    title?: string;
    items: Array<Record<string, any>>;
    loading?: boolean;
    selectedWarehouseId?: number | null;
  }>(),
  {
    title: "Обрати склад",
    loading: false,
    selectedWarehouseId: null,
  },
);

const emit = defineEmits<{
  "update:open": [value: boolean];
  select: [warehouse: Record<string, any>];
}>();

const search = ref("");

const filteredGroups = computed(() => {
  const term = search.value.trim().toLowerCase();
  const grouped = new Map<string, Array<Record<string, any>>>();

  for (const warehouse of props.items || []) {
    const haystack = [
      warehouse?.name,
      warehouse?.region,
      warehouse?.full_address,
      warehouse?.warehouse_type_label,
    ]
      .map((part) => String(part || "").toLowerCase())
      .join(" ");

    if (term && !haystack.includes(term)) continue;

    const region = String(warehouse?.region || "").trim() || "Без області";
    const current = grouped.get(region) || [];
    current.push(warehouse);
    grouped.set(region, current);
  }

  return Array.from(grouped.entries())
    .sort(([left], [right]) => left.localeCompare(right, "uk"))
    .map(([region, items]) => ({
      region,
      items: items.sort((left, right) =>
        String(left?.name || "").localeCompare(String(right?.name || ""), "uk"),
      ),
    }));
});

watch(
  () => props.open,
  (open) => {
    if (open) search.value = "";
  },
);
</script>
