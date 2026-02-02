<template>
  <ul class="relative isolate w-full list-none p-0 m-0">
    <li class="w-full">
      <!-- Рядок елемента в стилі Nuxt UI Tree -->
      <div
        class="relative group w-full flex items-center gap-2 py-1.5 px-2.5 text-sm rounded-md select-none cursor-pointer min-h-9 before:absolute before:inset-y-px before:inset-x-0 before:z-[-1] before:rounded-md before:transition-colors focus:outline-none"
        :class="[
          isSelected
            ? 'before:bg-primary-100 text-primary-700 dark:before:bg-primary-900/30 dark:text-primary-400'
            : 'hover:before:bg-gray-100 dark:hover:before:bg-gray-800/50',
        ]"
        @click="$emit('select', item)"
      >
        <!-- Шеврон для розгортання (якщо є діти) -->
        <span
          v-if="hasChildren"
          class="shrink-0 w-5 h-5 flex items-center justify-center rounded transition-transform duration-200"
          :class="{ 'rotate-[-90deg]': !isExpanded }"
          @click.stop="isExpanded = !isExpanded"
        >
          <UIcon name="i-heroicons-chevron-down" class="size-4 text-gray-500" />
        </span>
        <span v-else class="shrink-0 w-5" />
        <!-- Контент -->
        <div class="flex-1 min-w-0 truncate">
          <div class="font-medium truncate">{{ item.name }}</div>
          <div
            v-if="item.code"
            class="text-xs text-gray-500 dark:text-gray-400 truncate"
          >
            {{ item.code }}
          </div>
          <div
            v-if="item.user_count > 0"
            class="text-xs text-gray-400 dark:text-gray-500"
          >
            {{ item.user_count }} користувачів
          </div>
        </div>
        <!-- Кнопки дій (trailing) -->
        <div
          class="shrink-0 flex gap-0.5 ms-auto opacity-0 group-hover:opacity-100 transition-opacity"
          @click.stop
        >
          <UButton
            icon="i-heroicons-pencil"
            size="xs"
            variant="ghost"
            class="!p-1"
            @click="$emit('edit', item)"
          />
          <UButton
            icon="i-heroicons-trash"
            size="xs"
            variant="ghost"
            color="red"
            class="!p-1"
            @click="$emit('delete', item)"
          />
        </div>
      </div>
      <!-- Вкладені дочірні елементи (як у Nuxt UI: border-s, відступ) -->
      <div
        v-if="hasChildren && isExpanded"
        class="border-s border-gray-200 dark:border-gray-700 ms-5 ps-1.5 -ms-px"
      >
        <TreeItem
          v-for="child in item.children"
          :key="child.id"
          :item="child"
          :level="level + 1"
          :selected-id="selectedId"
          @select="$emit('select', $event)"
          @edit="$emit('edit', $event)"
          @delete="$emit('delete', $event)"
        />
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
const props = defineProps<{
  item: any;
  level?: number;
  selectedId?: number | null;
  defaultExpanded?: boolean;
}>();

defineEmits<{
  select: [item: any];
  edit: [item: any];
  delete: [item: any];
}>();

const isSelected = computed(() => props.item.id === props.selectedId);
const hasChildren = computed(
  () => Array.isArray(props.item.children) && props.item.children.length > 0,
);
const isExpanded = ref(props.defaultExpanded !== false);
</script>
