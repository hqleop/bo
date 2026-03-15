<template>
  <UModal
    v-model:open="protocolModalOpen"
    :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-[96vw]' }"
  >
    <template #content>
      <UCard class="flex max-h-[92vh] flex-col overflow-hidden">
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-lg font-semibold">Протокол процедури</h3>
            <UButton
              icon="i-heroicons-arrow-down-tray"
              variant="outline"
              @click="props.downloadProtocolPdf"
            >
              Завантажити PDF
            </UButton>
          </div>
        </template>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <TenderProtocolPreview
            :protocol="props.protocolPreview"
            :loading="props.protocolPreviewLoading"
            :error="props.protocolPreviewError"
          />
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="proposalsModalOpen"
    :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
  >
    <template #content>
      <UCard class="flex max-h-[90vh] flex-col overflow-hidden">
        <template #header>
          <h3 class="text-lg font-semibold">Усі пропозиції</h3>
        </template>
        <div
          class="min-h-[300px] min-h-0 flex-1 resize-y overflow-auto"
          style="resize: vertical"
        >
          <table
            v-if="
              props.proposalComparisonPositions.length &&
              props.submittedDecisionProposals.length
            "
            class="w-full border-collapse text-sm"
          >
            <thead>
              <tr class="border-b border-gray-200 bg-gray-100">
                <th class="bg-gray-100 p-2 text-left font-medium whitespace-nowrap">
                  Назва позиції
                </th>
                <th class="bg-gray-100 p-2 text-left font-medium whitespace-nowrap">
                  Кількість
                </th>
                <template
                  v-for="proposal in props.submittedDecisionProposals"
                  :key="proposal.id"
                >
                  <th
                    :colspan="3 + (props.tender?.criteria?.length ?? 0)"
                    class="border-l border-gray-300 bg-gray-200 p-2 text-left font-medium"
                  >
                    {{
                      proposal.supplier_company?.name ||
                      proposal.supplier_name ||
                      "—"
                    }}
                    <span
                      v-if="proposal.supplier_company?.edrpou"
                      class="font-normal text-gray-600"
                    >
                      ({{ proposal.supplier_company.edrpou }})
                    </span>
                  </th>
                </template>
              </tr>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th class="bg-gray-50 p-2"></th>
                <th class="bg-gray-50 p-2"></th>
                <template
                  v-for="proposal in props.submittedDecisionProposals"
                  :key="proposal.id"
                >
                  <th
                    class="border-l border-gray-200 p-2 text-left font-medium whitespace-nowrap"
                  >
                    {{ props.proposalComparisonPriceHeader }}
                  </th>
                  <th
                    class="border-l border-gray-200 p-2 text-left font-medium whitespace-nowrap"
                  >
                    Ціна без ПДВ
                  </th>
                  <th
                    class="border-l border-gray-200 p-2 text-left font-medium whitespace-nowrap"
                  >
                    Сума
                  </th>
                  <th
                    v-for="criterion in props.tender?.criteria ?? []"
                    :key="criterion.id"
                    class="border-l border-gray-200 p-2 text-left font-medium"
                  >
                    {{ criterion.name }}
                  </th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="position in props.proposalComparisonPositions"
                :key="position.id"
                class="border-b border-gray-200 hover:bg-gray-50/50"
              >
                <td class="bg-white p-2 whitespace-nowrap">{{ position.name }}</td>
                <td class="bg-white p-2 whitespace-nowrap">
                  {{ props.formatDecimalDisplay(position.quantity) }}
                  {{ position.unit_name || "" }}
                </td>
                <template
                  v-for="proposal in props.submittedDecisionProposals"
                  :key="proposal.id"
                >
                  <td
                    class="border-l border-gray-200 p-2"
                    :class="
                      (props.proposalComparisonByPosition[position.id]?.bestId ===
                        proposal.id &&
                        'bg-green-500/20') ||
                      (props.proposalComparisonByPosition[position.id]?.worstId ===
                        proposal.id &&
                        props.proposalComparisonByPosition[position.id]?.worstId !==
                          props.proposalComparisonByPosition[position.id]?.bestId &&
                        'bg-red-500/20')
                    "
                  >
                    {{
                      props.formatNumericOrDash(
                        props.getProposalPositionValue(proposal, position.id)?.price,
                      )
                    }}
                  </td>
                  <td class="border-l border-gray-200 p-2">
                    {{
                      props.formatNumericOrDash(
                        props.getProposalPositionValue(proposal, position.id)
                          ?.price_without_vat,
                      )
                    }}
                  </td>
                  <td
                    class="border-l border-gray-200 p-2"
                    :class="
                      (props.proposalComparisonByPosition[position.id]?.bestId ===
                        proposal.id &&
                        'bg-green-500/20') ||
                      (props.proposalComparisonByPosition[position.id]?.worstId ===
                        proposal.id &&
                        props.proposalComparisonByPosition[position.id]?.worstId !==
                          props.proposalComparisonByPosition[position.id]?.bestId &&
                        'bg-red-500/20')
                    "
                  >
                    {{ props.getProposalPositionSum(proposal, position) ?? "—" }}
                  </td>
                  <td
                    v-for="criterion in props.tender?.criteria ?? []"
                    :key="criterion.id"
                    class="border-l border-gray-200 p-2"
                  >
                    {{
                      props.getProposalCriterionValue(
                        proposal,
                        position.id,
                        criterion.id,
                      ) ?? "—"
                    }}
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
          <p v-else class="py-8 text-center text-gray-500">
            Немає позицій або пропозицій для порівняння.
          </p>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="participantProposalModalOpen"
    :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
  >
    <template #content>
      <UCard class="flex max-h-[90vh] flex-col overflow-hidden">
        <template #header>
          <h3 class="text-lg font-semibold">
            Пропозиція:
            {{
              props.selectedParticipantProposal?.supplier_company?.name ||
              props.selectedParticipantProposal?.supplier_name ||
              "—"
            }}
          </h3>
        </template>
        <div class="min-h-0 flex-1 overflow-auto">
          <table class="w-full border-collapse text-sm">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-100">
                <th class="p-2 text-left font-medium">Позиція</th>
                <th class="p-2 text-left font-medium">Кількість</th>
                <th class="p-2 text-left font-medium">
                  {{ props.proposalComparisonPriceHeader }}
                </th>
                <th class="p-2 text-left font-medium">Ціна без ПДВ</th>
                <th
                  v-for="criterion in props.tender?.criteria ?? []"
                  :key="criterion.id"
                  class="p-2 text-left font-medium"
                >
                  {{ criterion.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="position in props.displayTenderPositions"
                :key="position.id"
                class="border-b border-gray-200 hover:bg-gray-50/50"
              >
                <td class="p-2">{{ position.name }}</td>
                <td class="p-2">
                  {{ props.formatDecimalDisplay(position.quantity) }}
                  {{ position.unit_name || "" }}
                </td>
                <td class="p-2">
                  {{
                    props.formatNumericOrDash(
                      props.getProposalPositionValue(
                        props.selectedParticipantProposal,
                        position.id,
                      )?.price,
                    )
                  }}
                </td>
                <td class="p-2">
                  {{
                    props.formatNumericOrDash(
                      props.getProposalPositionValue(
                        props.selectedParticipantProposal,
                        position.id,
                      )?.price_without_vat,
                    )
                  }}
                </td>
                <td
                  v-for="criterion in props.tender?.criteria ?? []"
                  :key="criterion.id"
                  class="p-2"
                >
                  {{
                    props.getProposalCriterionValue(
                      props.selectedParticipantProposal,
                      position.id,
                      criterion.id,
                    ) ?? "—"
                  }}
                </td>
              </tr>
              <tr v-if="!props.displayTenderPositions.length">
                <td colspan="100" class="p-4 text-center text-gray-500">
                  Немає позицій тендера.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="participantChatModalOpen"
    :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-2xl' }"
  >
    <template #content>
      <UCard class="min-w-0 max-h-[88vh] overflow-hidden">
        <template #header><h3>Чат із організатором</h3></template>
        <div class="flex max-h-[calc(88vh-5rem)] flex-col space-y-4">
          <div class="min-h-0 flex-1 overflow-auto rounded border border-gray-200 p-3">
            <div v-if="props.chatMessages.length" class="space-y-3">
              <div
                v-for="message in props.chatMessages"
                :key="message.id"
                class="rounded border border-gray-100 p-3"
              >
                <p class="font-medium text-gray-900">
                  {{ message.author_display || "—" }}
                </p>
                <p class="text-xs text-gray-500">
                  {{ props.formatDateTime(message.created_at) }}
                </p>
                <p class="mt-2 whitespace-pre-wrap text-sm text-gray-700">
                  {{ message.body }}
                </p>
              </div>
            </div>
            <p v-else class="py-6 text-center text-gray-500">
              Історія повідомлень порожня.
            </p>
          </div>
          <UTextarea
            v-model="chatDraftModel"
            :rows="4"
            placeholder="Введіть текст повідомлення"
          />
          <div class="flex justify-end gap-2">
            <UButton variant="outline" @click="props.closeChatModals">
              Скасувати
            </UButton>
            <UButton
              :loading="props.chatSending"
              @click="props.submitParticipantChatMessage"
            >
              Надіслати
            </UButton>
          </div>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="organizerChatModalOpen"
    :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-3xl' }"
  >
    <template #content>
      <UCard class="min-w-0 max-h-[88vh] overflow-hidden">
        <template #header><h3>Чат із контрагентами</h3></template>
        <div
          class="grid max-h-[calc(88vh-5rem)] gap-4 md:grid-cols-[220px_minmax(0,1fr)]"
        >
          <div class="rounded border border-gray-200">
            <div class="max-h-[72vh] overflow-auto p-2">
              <button
                v-for="thread in props.chatThreads"
                :key="thread.id"
                type="button"
                class="w-full rounded px-3 py-2 text-left text-sm hover:bg-gray-50"
                :class="
                  props.selectedChatSupplierId === thread.supplier_company
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700'
                "
                @click="props.selectOrganizerChatThread(thread.supplier_company)"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="font-medium">
                    {{ thread.supplier_company_name || "—" }}
                  </div>
                  <span
                    v-if="Number(thread.unread_count || 0) > 0"
                    class="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-warning"
                    aria-label="Є непрочитані повідомлення"
                  />
                </div>
                <div class="text-xs text-gray-500">
                  {{ thread.supplier_company_edrpou || "—" }}
                </div>
              </button>
              <p v-if="!props.chatThreads.length" class="p-3 text-sm text-gray-500">
                Питань від учасників ще немає.
              </p>
            </div>
          </div>
          <div class="flex min-h-0 flex-col space-y-4">
            <div class="min-h-0 flex-1 overflow-auto rounded border border-gray-200 p-3">
              <div v-if="props.chatMessages.length" class="space-y-3">
                <div
                  v-for="message in props.chatMessages"
                  :key="message.id"
                  class="rounded border border-gray-100 p-3"
                >
                  <p class="font-medium text-gray-900">
                    {{ message.author_display || "—" }}
                  </p>
                  <p class="text-xs text-gray-500">
                    {{ props.formatDateTime(message.created_at) }}
                  </p>
                  <p class="mt-2 whitespace-pre-wrap text-sm text-gray-700">
                    {{ message.body }}
                  </p>
                </div>
              </div>
              <p v-else class="py-6 text-center text-gray-500">
                Оберіть контрагента або дочекайтеся першого питання.
              </p>
            </div>
            <UTextarea
              v-model="chatDraftModel"
              :rows="4"
              :disabled="!props.selectedChatSupplierId"
              placeholder="Введіть текст відповіді"
            />
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="props.closeChatModals">
                Скасувати
              </UButton>
              <UButton
                :loading="props.chatSending"
                :disabled="!props.selectedChatSupplierId"
                @click="props.submitOrganizerChatMessage"
              >
                Зберегти
              </UButton>
            </div>
          </div>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="proposalChangeReportModalOpen"
    :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-6xl' }"
  >
    <template #content>
      <UCard class="min-w-0">
        <template #header><h3>Звіт по змінам в КП</h3></template>
        <div class="overflow-auto">
          <table
            v-if="props.proposalChangeReport.length"
            class="w-full border-collapse text-sm"
          >
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th class="p-2 text-left font-medium">Контрагент</th>
                <th class="p-2 text-left font-medium">Позиція</th>
                <th class="p-2 text-left font-medium">Було</th>
                <th class="p-2 text-left font-medium">Стало</th>
                <th class="p-2 text-left font-medium">Змінено</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in props.proposalChangeReport"
                :key="item.id"
                class="border-b border-gray-200 align-top"
              >
                <td class="p-2">{{ item.supplier_company_name || "—" }}</td>
                <td class="p-2">{{ item.position_name || "—" }}</td>
                <td class="p-2">
                  <div>Ціна: {{ props.formatNumericOrDash(item.original_price) }}</div>
                  <div class="mt-1 text-xs text-gray-500">
                    {{
                      props.formatCriterionSummary(item.original_criterion_values)
                    }}
                  </div>
                </td>
                <td class="p-2">
                  <div>Ціна: {{ props.formatNumericOrDash(item.current_price) }}</div>
                  <div class="mt-1 text-xs text-gray-500">
                    {{
                      props.formatCriterionSummary(item.current_criterion_values)
                    }}
                  </div>
                </td>
                <td class="p-2">
                  <div>{{ item.updated_by_display || "—" }}</div>
                  <div class="text-xs text-gray-500">
                    {{ props.formatDateTime(item.updated_at) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="py-8 text-center text-gray-500">
            {{
              props.proposalChangeReportLoading
                ? "Завантаження звіту..."
                : "Змін КП не зафіксовано."
            }}
          </p>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal v-model:open="disqualificationModalOpen">
    <template #content>
      <UCard>
        <template #header><h3>Дискваліфікація учасників</h3></template>
        <div class="space-y-4">
          <div
            v-for="row in props.disqualificationRows"
            :key="row.proposal_id"
            class="rounded border border-gray-200 p-3"
          >
            <label class="flex items-start gap-3">
              <input v-model="row.disqualify" type="checkbox" class="mt-1" />
              <span class="font-medium text-gray-900">
                {{ row.supplier_name }}
              </span>
            </label>
            <UTextarea
              v-model="row.comment"
              class="mt-3"
              :rows="3"
              :disabled="!row.disqualify"
              placeholder="Коментар до дискваліфікації"
            />
          </div>
          <div class="flex justify-end gap-2">
            <UButton variant="outline" @click="disqualificationModalOpen = false">
              Скасувати
            </UButton>
            <UButton
              :loading="props.disqualificationSaving"
              @click="props.submitDisqualifications"
            >
              Зберегти
            </UButton>
          </div>
        </div>
      </UCard>
    </template>
  </UModal>

  <UModal
    v-model:open="attachedFilesModalOpen"
    :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-4xl' }"
  >
    <template #content>
      <UCard class="min-w-0">
        <template #header><h3>Прикріплені файли</h3></template>
        <div class="min-w-0 space-y-4">
          <div v-if="!props.isReadOnlyApprover">
            <input
              ref="attachedFilesInput"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,image/*"
              class="hidden"
              @change="props.onAttachedFilesInputChange"
            />
            <UButton
              variant="outline"
              icon="i-heroicons-arrow-up-tray"
              :loading="props.attachedFilesUploading"
              @click="attachedFilesInput?.click()"
            >
              Обрати файли
            </UButton>
          </div>
          <div v-if="props.attachedFilesLoading" class="flex justify-center py-4">
            <UIcon
              name="i-heroicons-arrow-path"
              class="size-6 animate-spin text-gray-400"
            />
          </div>
          <div
            v-else-if="props.attachedFilesList.length"
            class="min-w-0 overflow-hidden"
          >
            <table class="w-full min-w-0 table-fixed border-collapse text-sm">
              <thead>
                <tr class="border-b border-gray-200 bg-gray-50">
                  <th
                    class="w-32 p-2 text-left font-medium text-gray-700 whitespace-nowrap"
                  >
                    Видимість
                  </th>
                  <th class="p-2 text-left font-medium text-gray-700">Файл</th>
                  <th class="w-36 p-2 text-left font-medium text-gray-700">
                    Дата
                  </th>
                  <th class="p-2 text-left font-medium text-gray-700">
                    Користувач
                  </th>
                  <th class="w-24" />
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="file in props.attachedFilesList"
                  :key="file.id"
                  class="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td class="w-32 p-2 whitespace-nowrap">
                    <UCheckbox
                      :model-value="file.visible_to_participants"
                      :disabled="props.isReadOnlyApprover"
                      @update:model-value="
                        props.toggleFileVisibility(file.id, $event)
                      "
                    />
                  </td>
                  <td class="min-w-0 truncate p-2" :title="file.name">
                    {{ file.name }}
                  </td>
                  <td class="w-36 truncate p-2 text-gray-600">
                    {{ props.formatFileDate(file.uploaded_at) }}
                  </td>
                  <td class="min-w-0 truncate p-2 text-gray-600">
                    {{ file.uploaded_by_display || "—" }}
                  </td>
                  <td class="w-24 p-2">
                    <div class="flex items-center gap-1">
                      <UButton
                        variant="ghost"
                        size="xs"
                        icon="i-heroicons-arrow-down-tray"
                        :to="file.file_url"
                        target="_blank"
                        rel="noopener"
                        title="Скачати"
                      />
                      <UButton
                        v-if="!props.isReadOnlyApprover"
                        variant="ghost"
                        size="xs"
                        icon="i-heroicons-trash"
                        color="error"
                        title="Видалити"
                        @click="props.deleteAttachedFile(file.id)"
                      />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="py-2 text-sm text-gray-500">
            Немає прикріплених файлів.
          </div>
        </div>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import TenderProtocolPreview from "~/components/tenders/TenderProtocolPreview.vue";

type ValueFormatter = (value: unknown) => string;
type ProposalValueGetter = (proposal: any, positionId: number) => any;
type ProposalCriterionGetter = (
  proposal: any,
  positionId: number,
  criterionId: number,
) => unknown;
type ProposalPositionSumGetter = (
  proposal: any,
  position: { id: number; quantity: number },
) => string | null;
type ThreadSelector = (supplierCompanyId: number) => void | Promise<void>;
type FileVisibilityToggle = (
  fileId: number,
  visible: boolean,
) => void | Promise<void>;
type FileDelete = (fileId: number) => void | Promise<void>;
type InputChangeHandler = (event: Event) => void | Promise<void>;
type VoidHandler = () => void | Promise<void>;

interface Props {
  showProtocolModal: boolean;
  showProposalsModal: boolean;
  showParticipantProposalModal: boolean;
  showParticipantChatModal: boolean;
  showOrganizerChatModal: boolean;
  showProposalChangeReportModal: boolean;
  showDisqualificationModal: boolean;
  showAttachedFilesModal: boolean;
  protocolPreview: any;
  protocolPreviewLoading: boolean;
  protocolPreviewError: string;
  downloadProtocolPdf: VoidHandler;
  proposalComparisonPositions: any[];
  submittedDecisionProposals: any[];
  tender: any;
  proposalComparisonPriceHeader: string;
  proposalComparisonByPosition: Record<
    number,
    { bestId: number | null; worstId: number | null }
  >;
  formatNumericOrDash: ValueFormatter;
  getProposalPositionValue: ProposalValueGetter;
  getProposalPositionSum: ProposalPositionSumGetter;
  getProposalCriterionValue: ProposalCriterionGetter;
  formatDecimalDisplay: ValueFormatter;
  selectedParticipantProposal: any;
  displayTenderPositions: any[];
  chatMessages: any[];
  chatDraft: string;
  chatSending: boolean;
  closeChatModals: VoidHandler;
  submitParticipantChatMessage: VoidHandler;
  chatThreads: any[];
  selectedChatSupplierId: number | null;
  selectOrganizerChatThread: ThreadSelector;
  submitOrganizerChatMessage: VoidHandler;
  formatDateTime: ValueFormatter;
  proposalChangeReport: any[];
  proposalChangeReportLoading: boolean;
  formatCriterionSummary: ValueFormatter;
  disqualificationRows: any[];
  disqualificationSaving: boolean;
  submitDisqualifications: VoidHandler;
  isReadOnlyApprover: boolean;
  attachedFilesUploading: boolean;
  attachedFilesLoading: boolean;
  attachedFilesList: any[];
  onAttachedFilesInputChange: InputChangeHandler;
  toggleFileVisibility: FileVisibilityToggle;
  formatFileDate: ValueFormatter;
  deleteAttachedFile: FileDelete;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  "update:showProtocolModal": [value: boolean];
  "update:showProposalsModal": [value: boolean];
  "update:showParticipantProposalModal": [value: boolean];
  "update:showParticipantChatModal": [value: boolean];
  "update:showOrganizerChatModal": [value: boolean];
  "update:showProposalChangeReportModal": [value: boolean];
  "update:showDisqualificationModal": [value: boolean];
  "update:showAttachedFilesModal": [value: boolean];
  "update:chatDraft": [value: string];
}>();

const attachedFilesInput = ref<HTMLInputElement | null>(null);

const protocolModalOpen = computed({
  get: () => props.showProtocolModal,
  set: (value: boolean) => emit("update:showProtocolModal", value),
});

const proposalsModalOpen = computed({
  get: () => props.showProposalsModal,
  set: (value: boolean) => emit("update:showProposalsModal", value),
});

const participantProposalModalOpen = computed({
  get: () => props.showParticipantProposalModal,
  set: (value: boolean) => emit("update:showParticipantProposalModal", value),
});

const participantChatModalOpen = computed({
  get: () => props.showParticipantChatModal,
  set: (value: boolean) => emit("update:showParticipantChatModal", value),
});

const organizerChatModalOpen = computed({
  get: () => props.showOrganizerChatModal,
  set: (value: boolean) => emit("update:showOrganizerChatModal", value),
});

const proposalChangeReportModalOpen = computed({
  get: () => props.showProposalChangeReportModal,
  set: (value: boolean) =>
    emit("update:showProposalChangeReportModal", value),
});

const disqualificationModalOpen = computed({
  get: () => props.showDisqualificationModal,
  set: (value: boolean) => emit("update:showDisqualificationModal", value),
});

const attachedFilesModalOpen = computed({
  get: () => props.showAttachedFilesModal,
  set: (value: boolean) => emit("update:showAttachedFilesModal", value),
});

const chatDraftModel = computed({
  get: () => props.chatDraft,
  set: (value: string) => emit("update:chatDraft", value),
});
</script>
