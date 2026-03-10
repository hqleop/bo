<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Шаблони умов</h2>
      <UButton icon="i-heroicons-plus" @click="openCreateModal">
        Додати шаблон
      </UButton>
    </div>

    <UCard class="flex-1 min-h-0 overflow-hidden">
      <div
        v-if="loading"
        class="h-full min-h-[220px] flex items-center justify-center text-gray-500"
      >
        Завантаження шаблонів...
      </div>

      <div
        v-else-if="templates.length === 0"
        class="h-full min-h-[220px] flex items-center justify-center text-gray-500"
      >
        Немає жодного шаблону.
      </div>

      <UTable
        v-else
        :data="templates"
        :columns="columns"
        class="w-full"
      >
        <template #name-cell="{ row }">
          <UButton
            variant="link"
            color="neutral"
            class="px-0"
            @click="openEditModal(row.original)"
          >
            {{ row.original.name }}
          </UButton>
        </template>

        <template #actions-cell="{ row }">
          <UButton
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            @click="removeTemplate(row.original.id)"
          />
        </template>
      </UTable>
    </UCard>

    <UModal
      v-model:open="showEditorModal"
      :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-4xl' }"
    >
      <template #content>
        <UCard class="min-w-0">
          <template #header>
            <h3 class="text-lg font-semibold">
              {{ editingId ? "Редагування шаблону" : "Новий шаблон" }}
            </h3>
          </template>

          <div class="space-y-4">
            <UFormField label="Назва шаблону" required>
              <UInput
                v-model="form.name"
                placeholder="Вкажіть назву"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Текст шаблону">
              <div
                class="min-h-[320px] rounded-md border border-gray-200 bg-white overflow-hidden"
              >
                <UEditor
                  v-slot="{ editor }"
                  v-model="form.content"
                  content-type="html"
                  :extensions="[TextAlign.configure({ types: ['heading', 'paragraph'] })]"
                  :ui="{
                    root: 'flex flex-col min-h-[320px]',
                    content: 'flex-1 min-h-[280px] flex flex-col',
                    base: 'min-h-[280px] outline-none py-2 px-3 cursor-text',
                  }"
                >
                  <UEditorToolbar
                    :editor="editor"
                    :items="editorToolbarItems"
                    class="border-b border-gray-200 px-2 py-1 flex-shrink-0"
                  />
                </UEditor>
              </div>
            </UFormField>
          </div>

          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showEditorModal = false">
                Скасувати
              </UButton>
              <UButton :loading="saving" @click="saveTemplate">
                Зберегти
              </UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { TextAlign } from "@tiptap/extension-text-align";
import type { TenderConditionTemplate } from "~/domains/tenders/tenders.types";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Шаблони умов",
  },
});

const tendersUC = useTendersUseCases();
const { me } = useMe();

const loading = ref(false);
const saving = ref(false);
const templates = ref<TenderConditionTemplate[]>([]);
const showEditorModal = ref(false);
const editingId = ref<number | null>(null);
const form = reactive({
  name: "",
  content: "",
});

const companyId = computed(
  () => Number((me.value as any)?.memberships?.[0]?.company?.id || 0) || null,
);

const columns = [
  { accessorKey: "name", header: "Назва шаблону" },
  { accessorKey: "actions", header: "" },
];

const editorToolbarItems = [
  [
    { kind: "mark", mark: "bold", icon: "i-lucide-bold" },
    { kind: "mark", mark: "italic", icon: "i-lucide-italic" },
    { kind: "mark", mark: "underline", icon: "i-lucide-underline" },
  ],
  [
    {
      icon: "i-lucide-list",
      content: { align: "start" },
      items: [
        { kind: "bulletList", icon: "i-lucide-list", label: "Bullet List" },
        { kind: "orderedList", icon: "i-lucide-list-ordered", label: "Ordered List" },
      ],
    },
  ],
  [
    {
      icon: "i-lucide-align-justify",
      content: { align: "end" },
      items: [
        { kind: "textAlign", align: "left", icon: "i-lucide-align-left", label: "Align Left" },
        { kind: "textAlign", align: "center", icon: "i-lucide-align-center", label: "Align Center" },
        { kind: "textAlign", align: "right", icon: "i-lucide-align-right", label: "Align Right" },
        { kind: "textAlign", align: "justify", icon: "i-lucide-align-justify", label: "Align Justify" },
      ],
    },
  ],
];

function resetEditor() {
  editingId.value = null;
  form.name = "";
  form.content = "";
}

function openCreateModal() {
  resetEditor();
  showEditorModal.value = true;
}

function openEditModal(item: TenderConditionTemplate) {
  editingId.value = Number(item.id);
  form.name = String(item.name || "");
  form.content = String(item.content || "");
  showEditorModal.value = true;
}

async function loadTemplates() {
  if (!companyId.value) return;
  loading.value = true;
  try {
    const { data } = await tendersUC.getTenderConditionTemplates(companyId.value);
    templates.value = Array.isArray(data) ? data : [];
  } finally {
    loading.value = false;
  }
}

async function saveTemplate() {
  const normalizedName = String(form.name || "").trim();
  if (!normalizedName || !companyId.value) return;

  saving.value = true;
  try {
    if (editingId.value) {
      const { error } = await tendersUC.updateTenderConditionTemplate(editingId.value, {
        name: normalizedName,
        content: String(form.content || ""),
      });
      if (error) return;
    } else {
      const { error } = await tendersUC.createTenderConditionTemplate({
        company: companyId.value,
        name: normalizedName,
        content: String(form.content || ""),
      });
      if (error) return;
    }
    showEditorModal.value = false;
    await loadTemplates();
  } finally {
    saving.value = false;
  }
}

async function removeTemplate(id: number) {
  if (!confirm("Видалити шаблон?")) return;
  const { error } = await tendersUC.deleteTenderConditionTemplate(id);
  if (error) return;
  await loadTemplates();
}

watch(companyId, (id) => {
  if (id) {
    void loadTemplates();
  } else {
    templates.value = [];
  }
}, { immediate: true });
</script>
