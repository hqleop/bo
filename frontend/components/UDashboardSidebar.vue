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

function hasChildren(item: DashboardSidebarItem) {
  return (
    Array.isArray(item.children) &&
    item.children.length > 0
  );
}

function getItemKey(item: DashboardSidebarItem, index: number) {
  return String(item.id || item.to || item.label || `sidebar-item-${index}`);
}

function isItemActive(item: DashboardSidebarItem): boolean {
  if (Boolean(item.active)) return true;
  const children = Array.isArray(item.children) ? item.children : [];
  return children.some((child) => isItemActive(child as DashboardSidebarItem));
}

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
      header: 'px-0 h-14',
      body: 'p-0',
      content: 'w-[92vw] max-w-sm',
    }"
    @update:collapsed="onToggle"
  >
    <template #header="{ collapsed }">
      <div
        :class="[
          'h-full w-full flex-shrink-0 flex items-center',
          collapsed ? 'px-1.5 gap-1' : 'px-3 gap-2',
        ]"
      >
        <h2
          v-if="!collapsed"
          class="flex-1 text-lg font-bold text-gray-900 whitespace-nowrap"
        >
          {{ props.title }}
        </h2>
        <div v-else class="min-w-0 flex-1 flex justify-center">
          <span class="text-xs font-bold text-gray-900 truncate">{{
            props.compactTitle
          }}</span>
        </div>
        <UButton
          :icon="
            collapsed
              ? 'i-heroicons-chevron-double-right'
              : 'i-heroicons-chevron-double-left'
          "
          variant="ghost"
          color="neutral"
          size="xs"
          class="shrink-0"
          @click="onToggle"
        />
      </div>
    </template>

    <template #default="{ collapsed }">
      <nav
        :class="['flex-1 min-h-0 overflow-y-auto', collapsed ? 'p-2' : 'p-4']"
      >
        <div v-if="collapsed" class="flex flex-col items-center gap-1">
          <template v-for="(item, index) in props.items" :key="getItemKey(item, index)">
            <UPopover v-if="hasChildren(item)">
              <UButton
                :icon="item.icon as string | undefined"
                color="neutral"
                size="sm"
                :variant="isItemActive(item) ? 'soft' : 'ghost'"
                class="w-10 justify-center"
                :title="String(item.label || '')"
              />

              <template #content>
                <div class="w-80 max-h-[70vh] overflow-y-auto p-2">
                  <div class="px-2 py-1 text-sm font-semibold text-gray-900">
                    {{ item.label }}
                  </div>
                  <CollapsedSidebarTree :items="item.children as any[]" />
                </div>
              </template>
            </UPopover>

            <UButton
              v-else
              :to="item.to as string | undefined"
              :icon="item.icon as string | undefined"
              color="neutral"
              size="sm"
              :variant="isItemActive(item) ? 'soft' : 'ghost'"
              class="w-10 justify-center"
              :title="String(item.label || '')"
            />
          </template>
        </div>

        <UNavigationMenu
          v-else
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
