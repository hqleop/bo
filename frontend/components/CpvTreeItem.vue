<template>
  <ul class="relative isolate w-full list-none p-0 m-0">
    <li class="w-full">
      <div
        class="relative group w-full flex items-center gap-2 py-1.5 px-2.5 text-sm rounded-md select-none cursor-pointer min-h-9 before:absolute before:inset-y-px before:inset-x-0 before:z-[-1] before:rounded-md before:transition-colors hover:before:bg-gray-100 dark:hover:before:bg-gray-800/50"
        @click.stop="toggleSelf"
      >
        <!-- Чекбокс -->
        <UCheckbox
          :model-value="isChecked"
          @update:model-value="toggleSelf"
          class="shrink-0"
        />

        <!-- Шеврон для розгортання, якщо є діти -->
        <span
          v-if="hasChildren"
          class="shrink-0 w-5 h-5 flex items-center justify-center rounded transition-transform duration-200"
          :class="{ '-rotate-90': !isExpanded }"
          @click.stop="isExpanded = !isExpanded"
        >
          <UIcon name="i-heroicons-chevron-down" class="size-4 text-gray-500" />
        </span>
        <span v-else class="shrink-0 w-5" />

        <!-- Текст: код + назва -->
        <div class="flex-1 min-w-0 truncate">
          <div class="font-medium truncate">
            {{ item.cpv_code }} - {{ item.name_ua }}
          </div>
        </div>
      </div>

      <!-- Діти -->
      <div
        v-if="hasChildren && isExpanded"
        class="border-s border-gray-200 dark:border-gray-700 ms-5 ps-1.5 -ms-px"
      >
        <CpvTreeItem
          v-for="child in item.children"
          :key="child.id"
          :item="child"
          :selected-ids="selectedIds"
          @toggle="$emit('toggle', $event)"
        />
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
const props = defineProps<{
  item: any
  selectedIds: number[]
}>()

const emit = defineEmits<{
  toggle: [id: number]
}>()

const hasChildren = computed(
  () => Array.isArray(props.item.children) && props.item.children.length > 0
)
const isExpanded = ref(true)
const isChecked = computed(() => props.selectedIds.includes(props.item.id))

const toggleSelf = () => {
  emit('toggle', props.item.id)
}
</script>

