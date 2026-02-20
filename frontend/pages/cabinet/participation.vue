<template>
  <div class="h-full flex flex-col min-h-0">
    <h2 class="text-2xl font-bold mb-4">
      {{ type === 'purchase' ? 'Тендери на закупівлю' : 'Тендери на продаж' }}
    </h2>

    <UTabs v-model="activeTab" :items="tabItems" class="flex-shrink-0 mb-4" />

    <div class="flex-1 min-h-0 overflow-auto">
      <UTable
        v-if="tableData.length > 0"
        :data="tableData"
        :columns="tableColumns"
        class="w-full"
      >
        <template #number-cell="{ row }">
          <button
            type="button"
            class="text-primary hover:underline font-medium text-left"
            @click="openModal(row.original)"
          >
            №{{ row.original.number }}{{ row.original.tour_number > 1 ? ` (тур ${row.original.tour_number})` : '' }}
          </button>
        </template>
        <template #name-cell="{ row }">
          <button
            type="button"
            class="text-primary hover:underline text-left"
            @click="openModal(row.original)"
          >
            {{ row.original.name }}
          </button>
        </template>
      </UTable>

      <div v-else class="text-center text-gray-400 py-12">
        Немає тендерів у цій категорії.
      </div>
    </div>

    <UModal
      :open="modalOpen"
      :ui="{ width: 'max-w-4xl' }"
      @update:open="(v: boolean) => (modalOpen = v)"
    >
      <template #content>
        <div class="p-4 flex flex-col max-h-[85vh]">
          <h3 class="text-lg font-semibold mb-4">
            {{ selectedTender?.name }} - умови проведення
          </h3>

          <div class="flex gap-4 flex-1 min-h-0">
            <div class="flex-1 flex flex-col min-w-0">
              <h4 class="text-sm font-medium text-gray-600 mb-2">Загальні умови</h4>
              <div class="border rounded p-3 overflow-y-auto bg-gray-50 flex-1 min-h-[200px] max-h-[50vh]">
                <div
                  v-if="selectedTender?.general_terms"
                  class="text-sm prose prose-sm max-w-none"
                  v-html="formattedGeneralTerms"
                />
                <p v-else class="whitespace-pre-wrap text-sm">Опис умов не додано.</p>
              </div>
            </div>

            <div class="flex-1 flex flex-col min-w-0 gap-4">
              <div class="flex flex-col min-h-0">
                <h4 class="text-sm font-medium text-gray-600 mb-2">Позиції тендера</h4>
                <div class="border rounded overflow-y-auto flex-1 min-h-[120px] max-h-[34vh]">
                  <table class="w-full text-sm">
                    <thead class="bg-gray-100 sticky top-0">
                      <tr>
                        <th class="text-left p-2">Назва</th>
                        <th class="text-right p-2">Кількість</th>
                        <th class="text-left p-2">Од. вим.</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="pos in tenderPositionsForModal" :key="pos.id" class="border-t">
                        <td class="p-2">{{ pos.name }}</td>
                        <td class="p-2 text-right">{{ pos.quantity }}</td>
                        <td class="p-2">{{ pos.unit_name ?? '-' }}</td>
                      </tr>
                      <tr v-if="!tenderPositionsForModal.length">
                        <td colspan="3" class="p-3 text-gray-500">Позиції у цьому тендері відсутні.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="flex flex-col min-h-0">
                <h4 class="text-sm font-medium text-gray-600 mb-2">Загальні критерії</h4>
                <div class="border rounded p-3 overflow-y-auto bg-gray-50 min-h-[120px] max-h-[16vh]">
                  <ul v-if="tenderCriteriaForModal.length" class="space-y-2 text-sm">
                    <li v-for="criterion in tenderCriteriaForModal" :key="criterion.id">
                      <span class="font-medium">{{ criterion.name }}</span>
                      <span v-if="criterion.application_label" class="text-gray-500">
                        ({{ criterion.application_label }})
                      </span>
                    </li>
                  </ul>
                  <p v-else class="text-sm text-gray-500">Критерії не додано.</p>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-4 pt-4 border-t">
            <UButton variant="outline" @click="modalOpen = false">Вийти</UButton>

            <template v-if="checkingParticipation">
              <UButton disabled :loading="true">Перевірка...</UButton>
            </template>

            <template v-else-if="participationAlreadyConfirmed">
              <UButton @click="goToProposalsPage">Перейти до пропозиції</UButton>
            </template>

            <UButton v-else :loading="confirmLoading" @click="onConfirmParticipation">
              Підтвердити участь
            </UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: { title: 'Участь в тендерах' }
})

const route = useRoute()
const type = computed(() => (route.query.type === 'sales' ? 'sales' : 'purchase'))
const isSales = computed(() => type.value === 'sales')

const tabItems = [
  { label: 'Активні', value: 'active' },
  { label: 'Опрацьовуються', value: 'processing' },
  { label: 'Завершені', value: 'completed' }
]

const activeTab = ref<'active' | 'processing' | 'completed'>('active')
const tenders = ref<any[]>([])
const modalOpen = ref(false)
const selectedTender = ref<any>(null)
const confirmLoading = ref(false)

const tendersUC = useTendersUseCases()

const participationAlreadyConfirmed = ref(false)
const checkingParticipation = ref(false)
const confirmedTenderIds = ref<number[]>([])

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const formattedGeneralTerms = computed(() => {
  const terms = String(selectedTender.value?.general_terms ?? '').trim()
  if (!terms) return ''
  const looksLikeHtml = /<[^>]+>/.test(terms)
  if (looksLikeHtml) return terms
  return escapeHtml(terms).replace(/\r?\n/g, '<br>')
})

const tenderPositionsForModal = computed(() => {
  const positions = selectedTender.value?.positions
  return Array.isArray(positions) ? positions : []
})

const tenderCriteriaForModal = computed(() => {
  const criteria = selectedTender.value?.criteria
  return Array.isArray(criteria) ? criteria : []
})

const tableColumns = [
  { accessorKey: 'number', header: 'Номер' },
  { accessorKey: 'name', header: 'Назва' },
  { accessorKey: 'stage_label', header: 'Етап' },
  { accessorKey: 'conduct_type_label', header: 'Тип проведення' },
  { accessorKey: 'created_at', header: 'Створено' }
]

const tableData = computed(() => tenders.value)

async function loadList() {
  const { data } = await tendersUC.getTendersForParticipation(isSales.value, activeTab.value)
  tenders.value = data ?? []
}

async function openModal(tender: any) {
  const tenderId = tender?.id != null ? Number(tender.id) : null
  if (tenderId == null) return

  checkingParticipation.value = true
  modalOpen.value = false
  selectedTender.value = tender
  participationAlreadyConfirmed.value = false

  try {
    await loadList()

    const freshTender = tenders.value.find((t: any) => Number(t.id) === tenderId)
    if (freshTender) selectedTender.value = freshTender

    if (freshTender?.current_user_has_proposal === true) {
      participationAlreadyConfirmed.value = true
    }

    const { data: detail } = await tendersUC.getTender(tenderId, isSales.value)
    if (detail) {
      selectedTender.value = { ...selectedTender.value, ...detail }
    }

    if (detail?.current_user_has_proposal === true) {
      participationAlreadyConfirmed.value = true
    }

    if (confirmedTenderIds.value.includes(tenderId)) {
      participationAlreadyConfirmed.value = true
      selectedTender.value = {
        ...(selectedTender.value || {}),
        current_user_has_proposal: true
      }
    }

    if (participationAlreadyConfirmed.value) {
      if (!confirmedTenderIds.value.includes(tenderId)) {
        confirmedTenderIds.value = [...confirmedTenderIds.value, tenderId]
      }
      goToProposalsPage()
      return
    }

    modalOpen.value = true
  } finally {
    checkingParticipation.value = false
  }
}

function goToProposalsPage() {
  if (!selectedTender.value?.id) return
  const tenderId = selectedTender.value.id
  modalOpen.value = false
  selectedTender.value = null

  if (isSales.value) {
    navigateTo(`/cabinet/tenders/sales/proposals/${tenderId}`)
  } else {
    navigateTo(`/cabinet/tenders/proposals/${tenderId}`)
  }
}

async function onConfirmParticipation() {
  if (!selectedTender.value?.id) return
  const tenderId = selectedTender.value.id
  confirmLoading.value = true

  try {
    const { error } = await tendersUC.confirmParticipation(tenderId, isSales.value)
    if (error) {
      const msg = error || 'Не вдалося підтвердити участь.'
      useToast().add({ title: msg, color: 'error' })
      return
    }

    participationAlreadyConfirmed.value = true
    if (!confirmedTenderIds.value.includes(tenderId)) {
      confirmedTenderIds.value = [...confirmedTenderIds.value, tenderId]
    }
    selectedTender.value = {
      ...(selectedTender.value || {}),
      current_user_has_proposal: true
    }

    tenders.value = tenders.value.map((t: any) =>
      Number(t?.id) === Number(tenderId) ? { ...t, current_user_has_proposal: true } : t
    )

    await loadList()
    modalOpen.value = false
    selectedTender.value = null

    if (isSales.value) {
      await navigateTo(`/cabinet/tenders/sales/proposals/${tenderId}`)
    } else {
      await navigateTo(`/cabinet/tenders/proposals/${tenderId}`)
    }
  } catch (e: any) {
    const msg = e?.data?.detail || e?.message || 'Не вдалося підтвердити участь.'
    useToast().add({ title: msg, color: 'error' })
    console.error(msg)
  } finally {
    confirmLoading.value = false
  }
}

onMounted(() => {
  if (!route.query.type) {
    navigateTo({ path: '/cabinet/participation', query: { type: 'purchase' } })
    return
  }
  loadList()
})

onActivated(() => {
  if (route.query.type) loadList()
})

watch([activeTab, type], () => {
  if (route.query.type) loadList()
})
</script>
