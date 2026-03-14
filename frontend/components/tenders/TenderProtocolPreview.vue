<template>
  <div class="flex min-h-0 flex-1 flex-col bg-[#e5e7eb]">
    <div v-if="loading" class="flex min-h-[70vh] items-center justify-center">
      <UIcon name="i-heroicons-arrow-path" class="size-8 animate-spin text-slate-500" />
    </div>

    <div v-else-if="error" class="flex min-h-[70vh] items-center justify-center px-6">
      <div class="w-full max-w-md border border-red-200 bg-white p-6 text-center shadow-sm">
        <p class="text-base font-semibold text-slate-900">Не вдалося завантажити протокол</p>
        <p class="mt-2 text-sm text-slate-600">{{ error }}</p>
      </div>
    </div>

    <div v-else-if="!protocol" class="flex min-h-[70vh] items-center justify-center px-6">
      <div class="w-full max-w-md border border-slate-300 bg-white p-6 text-center shadow-sm">
        <p class="text-base font-semibold text-slate-900">Протокол недоступний</p>
      </div>
    </div>

    <div v-else class="min-h-0 flex-1 overflow-auto p-4 sm:p-6">
      <div class="mx-auto flex min-w-[794px] max-w-[794px] flex-col gap-6">
        <section class="protocol-sheet">
          <div class="flex items-start justify-between gap-6 text-[13px] leading-5">
            <div class="font-semibold">
              {{ display(protocol.company_name) }}
            </div>
            <div class="text-right">
              {{ display(protocol.generated_at) }}
            </div>
          </div>

          <div class="mt-2 border-b border-black pb-1 text-[13px] leading-5">
            {{ display(protocol.company_code) }}
          </div>

          <h2 class="mt-8 text-center text-[20px] font-semibold leading-6">
            Протокол проведення процедури
          </h2>

          <div class="mt-6 space-y-2 text-[14px] leading-6">
            <p>Тендер № {{ display(protocol.tender_number) }} {{ display(protocol.tender_name) }}</p>
            <p><span class="font-semibold">Рішення:</span> {{ display(protocol.decision_label) }}</p>
            <p><span class="font-semibold">Виконавець:</span> {{ display(protocol.author_name) }}</p>
            <p>
              <span class="font-semibold">Бюджет:</span>
              {{ budgetLine }}
              <span class="inline-block min-w-[140px]"></span>
              <span class="font-semibold">Валюта:</span>
              {{ display(protocol.currency_code) }}
            </p>
            <p><span class="font-semibold">Стаття бюджету:</span> {{ display(protocol.expense_article_name) }}</p>
            <p><span class="font-semibold">Філіал/Департамент:</span> {{ branchDepartmentLine }}</p>
            <p><span class="font-semibold">Підрозділ:</span> {{ display(protocol.department_name) }}</p>
          </div>

          <table class="protocol-table mt-6">
            <tbody>
              <tr>
                <td class="protocol-label-cell">Створення тендера</td>
                <td>{{ display(protocol.created_at) }}</td>
              </tr>
              <template v-for="tour in normalizedTours" :key="tour.key">
                <tr>
                  <td colspan="2" class="protocol-section-row">
                    Тур {{ tour.tour_number }} {{ tour.conduct_type_label }}
                  </td>
                </tr>
                <tr>
                  <td class="protocol-label-cell">Початок прийому пропозицій</td>
                  <td>{{ tour.start_at }}</td>
                </tr>
                <tr v-if="tour.timing_changed_at !== '—'">
                  <td class="protocol-label-cell">Зміна часу проведення тендера</td>
                  <td>{{ tour.timing_changed_at }}</td>
                </tr>
                <tr>
                  <td class="protocol-label-cell">Завершення прийому пропозицій</td>
                  <td>{{ tour.end_at }}</td>
                </tr>
              </template>
              <tr>
                <td class="protocol-label-cell">Завершення тендера</td>
                <td>{{ display(protocol.completed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="protocol-sheet">
          <table class="protocol-table">
            <tbody>
              <tr>
                <td class="protocol-label-cell">Прийняте рішення</td>
                <td>{{ display(protocol.decision_label) }}</td>
              </tr>
              <tr>
                <td class="protocol-label-cell">Дата рішення</td>
                <td>{{ display(protocol.decision_at) }}</td>
              </tr>
              <tr>
                <td class="protocol-label-cell">Параметри цінового критерію</td>
                <td>{{ display(protocol.price_criterion_label) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="mt-6">
            <h3 class="protocol-block-title">Переможці</h3>
            <table class="protocol-table mt-3">
              <thead>
                <tr>
                  <th>Контрагент</th>
                  <th>Позиція</th>
                  <th>Одиниці виміру</th>
                  <th>Кількість</th>
                  <th>Ціна</th>
                  <th>Вартість</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!winnerRows.length">
                  <td colspan="6">—</td>
                </tr>
                <tr v-for="(winner, index) in winnerRows" :key="`${winner.supplier_name}-${index}`">
                  <td>{{ display(winner.supplier_name) }}</td>
                  <td>{{ display(winner.position_name) }}</td>
                  <td>{{ display(winner.unit_name) }}</td>
                  <td>{{ display(winner.quantity) }}</td>
                  <td>{{ display(winner.price) }}</td>
                  <td>{{ display(winner.total) }}</td>
                </tr>
                <tr>
                  <td colspan="5" class="protocol-label-cell text-right">Разом</td>
                  <td>{{ display(protocol.winners_total) }}</td>
                </tr>
                <tr>
                  <td colspan="5" class="protocol-label-cell text-right">
                    {{ display(protocol.effect_label) }}
                  </td>
                  <td>{{ display(protocol.effect_amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-6">
            <h3 class="protocol-block-title">Критерії тендера</h3>
            <table class="protocol-table mt-3">
              <thead>
                <tr>
                  <th>Назва критерію</th>
                  <th>Тип</th>
                  <th>Значення</th>
                  <th>Застосування</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!criteriaRows.length">
                  <td colspan="4">—</td>
                </tr>
                <tr v-for="(criterion, index) in criteriaRows" :key="`${criterion.name}-${index}`">
                  <td>{{ display(criterion.name) }}</td>
                  <td>{{ display(criterion.type_label) }}</td>
                  <td>{{ display(criterion.value_display) }}</td>
                  <td>{{ display(criterion.application_label) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="protocol-sheet">
          <div>
            <h3 class="protocol-block-title">Запрошені учасники</h3>
            <table class="protocol-table mt-3">
              <thead>
                <tr>
                  <th>Контрагенти</th>
                  <th>Контактні особи / Агенти</th>
                  <th>Дата запрошення</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!participantRows.length">
                  <td colspan="3">—</td>
                </tr>
                <tr
                  v-for="(participant, index) in participantRows"
                  :key="`${participant.company_name}-${index}`"
                >
                  <td>{{ display(participant.company_name) }}</td>
                  <td class="whitespace-pre-line">{{ display(participant.contacts) }}</td>
                  <td>{{ display(participant.invited_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-6">
            <h3 class="protocol-block-title">Опис умов та вимог</h3>
            <div class="mt-3 border border-black px-4 py-3 text-[13px] leading-6">
              <p v-if="!generalTerms.length">—</p>
              <p v-for="(line, index) in generalTerms" :key="index">{{ line }}</p>
            </div>
          </div>

          <div class="mt-6">
            <h3 class="protocol-block-title">Журнал узгодження</h3>
            <table class="protocol-table mt-3">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Дія</th>
                  <th>Користувач</th>
                  <th>Коментар</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!journalRows.length">
                  <td colspan="4">—</td>
                </tr>
                <tr v-for="(entry, index) in journalRows" :key="`${entry.created_at}-${index}`">
                  <td>{{ display(entry.created_at) }}</td>
                  <td>{{ display(entry.action_label) }}</td>
                  <td>{{ display(entry.actor_name) }}</td>
                  <td class="whitespace-pre-line">{{ display(entry.comment) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-if="meaningfulDecisionComment"
            class="mt-6 border border-black px-4 py-3 text-[13px] leading-6"
          >
            <p class="font-semibold">Коментар до рішення</p>
            <p class="mt-2 whitespace-pre-line">{{ meaningfulDecisionComment }}</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TenderProtocolPreviewPayload } from '~/domains/tenders/tenders.types'

const props = defineProps<{
  protocol: TenderProtocolPreviewPayload | null
  loading?: boolean
  error?: string | null
}>()

const EMPTY_VALUE = '—'

const display = (value?: string | null) => {
  const prepared = `${value ?? ''}`.trim()
  return prepared && prepared !== '-' ? prepared : EMPTY_VALUE
}

const hasValue = (value?: string | null) => display(value) !== EMPTY_VALUE

const budgetLine = computed(() => display(props.protocol?.budget_amount))

const branchDepartmentLine = computed(() => {
  const values = [props.protocol?.branch_name, props.protocol?.department_name]
    .map((item) => display(item))
    .filter((item) => item !== EMPTY_VALUE)
  return values.length ? values.join(' / ') : EMPTY_VALUE
})

const normalizedTours = computed(() =>
  (props.protocol?.tours || []).map((tour, index) => ({
    key: `${tour.tour_number || index}-${tour.start_at || index}`,
    tour_number: display(String(tour.tour_number ?? index + 1)),
    conduct_type_label: display(tour.conduct_type_label),
    start_at: display(tour.start_at),
    end_at: display(tour.end_at),
    timing_changed_at: display(tour.timing_changed_at),
  })),
)

const winnerRows = computed(() => props.protocol?.winners || [])
const criteriaRows = computed(() => props.protocol?.criteria || [])
const participantRows = computed(() => props.protocol?.invited_participants || [])
const journalRows = computed(() => props.protocol?.approval_journal || [])
const generalTerms = computed(() => (props.protocol?.general_terms_lines || []).filter((line) => hasValue(line)))
const meaningfulDecisionComment = computed(() => {
  const comment = display(props.protocol?.decision_comment)
  return comment === EMPTY_VALUE ? '' : comment
})
</script>

<style scoped>
.protocol-sheet {
  width: 794px;
  min-height: 1123px;
  background: #fff;
  border: 1px solid #cfcfcf;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  padding: 48px 52px;
  color: #111827;
}

.protocol-block-title {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
}

.protocol-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
  line-height: 1.5;
}

.protocol-table th,
.protocol-table td {
  border: 1px solid #000;
  padding: 8px 10px;
  vertical-align: top;
  text-align: left;
  word-break: break-word;
}

.protocol-table thead th {
  font-weight: 700;
  background: #f4f4f4;
}

.protocol-label-cell {
  width: 36%;
  font-weight: 600;
}

.protocol-section-row {
  font-weight: 700;
  text-align: center;
  background: #f4f4f4;
}

@media (max-width: 960px) {
  .protocol-sheet {
    min-height: auto;
  }
}
</style>
