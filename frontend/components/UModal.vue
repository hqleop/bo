<script setup lang="ts">
import BaseModal from "@nuxt/ui/components/Modal.vue";

type ModalCloseConfig = boolean | Record<string, unknown>;
type ModalUiConfig = Record<string, unknown> & {
  content?: string;
};

const props = withDefaults(
  defineProps<{
    dismissible?: boolean;
    close?: ModalCloseConfig;
    ui?: ModalUiConfig;
  }>(),
  {
    dismissible: false,
    close: true,
  },
);

const emit = defineEmits<{
  (e: "after:leave"): void;
  (e: "after:enter"): void;
  (e: "close:prevent"): void;
  (e: "update:open", value: boolean): void;
}>();

const attrs = useAttrs();
</script>

<template>
  <BaseModal
    v-bind="attrs"
    :dismissible="props.dismissible"
    :close="props.close"
    :ui="props.ui"
    @after:leave="emit('after:leave')"
    @after:enter="emit('after:enter')"
    @close:prevent="emit('close:prevent')"
    @update:open="emit('update:open', $event)"
  >
    <template v-if="$slots.default" #default="slotProps">
      <slot v-bind="slotProps" />
    </template>

    <template v-if="$slots.content" #content="slotProps">
      <div class="relative">
        <slot name="content" v-bind="slotProps" />
        <UButton
          icon="i-heroicons-x-mark"
          color="neutral"
          variant="ghost"
          size="sm"
          class="absolute right-3 top-3 z-20"
          aria-label="Закрити модальне вікно"
          @click="slotProps.close()"
        />
      </div>
    </template>

    <template v-if="$slots.header" #header="slotProps">
      <slot name="header" v-bind="slotProps" />
    </template>
    <template v-if="$slots.title" #title="slotProps">
      <slot name="title" v-bind="slotProps" />
    </template>
    <template v-if="$slots.description" #description="slotProps">
      <slot name="description" v-bind="slotProps" />
    </template>
    <template v-if="$slots.actions" #actions="slotProps">
      <slot name="actions" v-bind="slotProps" />
    </template>
    <template v-if="$slots.body" #body="slotProps">
      <slot name="body" v-bind="slotProps" />
    </template>
    <template v-if="$slots.footer" #footer="slotProps">
      <slot name="footer" v-bind="slotProps" />
    </template>
    <template v-if="$slots.close" #close="slotProps">
      <slot name="close" v-bind="slotProps" />
    </template>
  </BaseModal>
</template>
