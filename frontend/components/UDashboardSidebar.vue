<script setup lang="ts">
import BaseDashboardSidebar from "@nuxt/ui/components/DashboardSidebar.vue";

type DashboardSidebarItem = Record<string, unknown>;

const props = withDefaults(
  defineProps<{
    items?: DashboardSidebarItem[];
    collapsed?: boolean;
    title?: string;
    compactTitle?: string;
  }>(),
  {
    items: () => [],
    collapsed: true,
    title: "Bid Open",
    compactTitle: "BO",
  },
);

const emit = defineEmits<{
  (e: "toggle"): void;
}>();

function onToggle() {
  emit("toggle");
}
</script>

<template>
  <BaseDashboardSidebar
    :collapsed="props.collapsed"
    side="left"
    :collapsible="true"
    :resizable="false"
    :default-size="18"
    :min-size="14"
    :max-size="22"
    class="h-full"
    :ui="{
      root: 'h-full bg-white border-r border-gray-200 shadow-sm',
      body: 'p-0',
      content: 'w-[92vw] max-w-sm',
    }"
    @update:collapsed="onToggle"
  >
    <template #header="{ collapsed }">
      <div
        :class="[
          'h-14 flex-shrink-0 flex items-center justify-between',
          collapsed ? 'px-2' : 'px-3',
        ]"
      >
        <h2
          v-if="!collapsed"
          class="text-lg font-bold text-gray-900 whitespace-nowrap"
        >
          {{ props.title }}
        </h2>
        <div v-else class="w-full flex justify-center">
          <span class="text-sm font-bold text-gray-900">{{ props.compactTitle }}</span>
        </div>
        <UButton
          :icon="
            collapsed
              ? 'i-heroicons-chevron-double-right'
              : 'i-heroicons-chevron-double-left'
          "
          variant="ghost"
          color="neutral"
          size="sm"
          class="shrink-0"
          @click="onToggle"
        />
      </div>
    </template>

    <template #default="{ collapsed }">
      <nav :class="['flex-1 min-h-0 overflow-y-auto', collapsed ? 'p-2' : 'p-4']">
        <UNavigationMenu
          orientation="vertical"
          :items="props.items"
          :collapsed="collapsed"
          :tooltip="true"
          :popover="true"
          :ui="{
            content: 'p-2',
            childLabel: 'text-base font-semibold px-2 py-1',
            childIcon: 'text-lg',
          }"
          color="neutral"
          variant="link"
          highlight
          class="data-[orientation=vertical]:w-full data-[orientation=vertical]:flex-col data-[orientation=vertical]:gap-0.5"
        />
      </nav>
    </template>
  </BaseDashboardSidebar>
</template>
