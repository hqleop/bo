<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <UIcon
      name="i-heroicons-arrow-path"
      class="animate-spin size-8 text-gray-400"
    />
  </div>
  <div v-else-if="!tender" class="text-center py-12 text-gray-500">
    Тендер не знайдено.
  </div>
  <div v-else class="h-full flex flex-col">
    <div class="mb-4">
      <h1
        v-if="tender.number"
        class="text-xl font-semibold text-gray-900 truncate"
      >
        № {{ tender.number }}
        <span class="font-normal text-gray-700">{{ tender.name }}</span>
      </h1>
    </div>
    <div v-if="tourOptions.length" class="mb-3 flex items-center gap-2">
      <span class="text-sm text-gray-600">Тур:</span>
      <USelectMenu
        :model-value="tenderId"
        :items="tourOptions"
        value-key="value"
        class="min-w-[100px]"
        @update:model-value="onTourSelect"
      />
    </div>
    <div class="tender-stepper tender-stepper--compact mb-6">
      <UStepper
        v-model="currentStepValue"
        :items="stepperItems"
        value-key="value"
        size="sm"
      />
    </div>

    <div class="flex flex-1 min-h-0 gap-6">
      <div
        class="flex-1 min-w-0 min-h-0"
        :class="displayStage === 'preparation' ? '' : 'overflow-y-auto'"
      >
        <template v-if="displayStage === 'passport'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Паспорт тендера</h3>
            </template>
            <UForm :state="form" class="space-y-4">
              <UFormField label="Назва тендера" required>
                <UInput v-model="form.name" placeholder="Назва тендера" />
              </UFormField>
              <ContentSearch
                label="Категорія"
                placeholder="Оберіть категорію"
                search-placeholder="Пошук категорії"
                :disabled="(form.cpv_ids?.length ?? 0) > 0"
                :tree="categoryTree"
                :selected-ids="selectedCategoryIds"
                :search-term="categorySearch"
                @toggle="toggleCategory"
                @update:search-term="categorySearch = $event"
              />
              <CpvLazyMultiSearch
                label="Категорія CPV"
                placeholder="Оберіть CPV"
                :disabled="!!form.category"
                :selected-ids="form.cpv_ids"
                :selected-labels="tenderCpvLabels"
                @update:selected-ids="form.cpv_ids = $event"
                @update:selected-labels="tenderCpvLabels = $event"
              />
              <UFormField label="Стаття бюджету">
                <USelectMenu
                  v-model="form.expense_article"
                  :items="expenseOptions"
                  value-key="value"
                  placeholder="Оберіть статтю"
                />
              </UFormField>
              <UFormField label="Орієнтовний бюджет">
                <UInput
                  v-model.number="form.estimated_budget"
                  type="number"
                  step="0.01"
                  placeholder="0"
                />
              </UFormField>
              <UFormField label="Філіал">
                <USelectMenu
                  v-model="form.branch"
                  :items="branchOptions"
                  value-key="value"
                  placeholder="Оберіть філіал"
                  @update:model-value="onBranchChange"
                />
              </UFormField>
              <UFormField label="Підрозділ">
                <USelectMenu
                  v-model="form.department"
                  :items="departmentOptions"
                  value-key="value"
                  placeholder="Оберіть підрозділ"
                />
              </UFormField>
              <UFormField label="Тип проведення" required>
                <USelectMenu
                  v-model="form.conduct_type"
                  :items="conductTypeOptions"
                  value-key="value"
                  placeholder="Оберіть тип"
                />
              </UFormField>
              <UFormField label="Тип публікації" required>
                <USelectMenu
                  v-model="form.publication_type"
                  :items="publicationTypeOptions"
                  value-key="value"
                  placeholder="Оберіть тип"
                />
              </UFormField>
              <UFormField label="Валюта тендера" required>
                <USelectMenu
                  v-model="form.currency"
                  :items="currencyOptions"
                  value-key="value"
                  placeholder="Оберіть валюту"
                />
              </UFormField>
              <UFormField label="Загальні умови">
                <UTextarea
                  v-model="form.general_terms"
                  :rows="6"
                  placeholder="Опис загальних умов"
                />
              </UFormField>
            </UForm>
          </UCard>
        </template>

        <template v-else-if="tender.stage === 'preparation'">
          <div
            class="h-full min-h-0 flex flex-col border rounded-lg p-4 bg-white"
          >
            <h3 class="text-lg font-semibold mb-3">Підготовка процедури</h3>
            <UTabs
              v-model="prepTab"
              :items="prepTabs"
              value-key="value"
              class="mb-4"
              content
            >
              <template #content="{ item }">
                <div
                  v-if="item.value === 'positions'"
                  class="h-full min-h-0 flex flex-col gap-3"
                >
                  <div class="flex items-end gap-3">
                    <div class="w-full max-w-xl">
                      <ContentSearch
                        label="Пошук і додавання номенклатури"
                        placeholder="Номенклатура"
                        search-placeholder="Пошук номенклатури"
                        :tree="nomenclatureSearchTree"
                        :selected-ids="selectedNomenclatureIds"
                        :search-term="nomenclatureSearch"
                        @toggle="toggleTenderPosition"
                        @update:search-term="nomenclatureSearch = $event"
                      />
                    </div>
                  </div>

                  <div
                    v-if="loadingNomenclatures"
                    class="text-sm text-gray-500 py-2"
                  >
                    Завантаження номенклатур...
                  </div>
                  <div
                    v-else-if="!nomenclatureSearchTree.length"
                    class="text-sm text-gray-500 py-2"
                  >
                    Немає доступних номенклатур для обраної категорії/CPV.
                  </div>

                  <div class="flex-1 min-h-0 overflow-auto">
                    <UTable
                      :data="tenderPositions"
                      :columns="positionsColumns"
                      class="w-full"
                    >
                      <template #quantity-cell="{ row }">
                        <UInput
                          type="number"
                          min="0"
                          step="0.01"
                          v-model.number="row.original.quantity"
                          size="sm"
                        />
                      </template>
                      <template #description-cell="{ row }">
                        <UInput v-model="row.original.description" size="sm" />
                      </template>
                      <template #vat-cell>
                        <UInput value="" disabled size="sm" />
                      </template>
                    </UTable>
                  </div>
                </div>

                <div v-else class="space-y-6">
                  <!-- Параметри цінового критерія -->
                  <div class="border rounded-lg p-4 bg-gray-50/50">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3">
                      Параметри цінового критерія
                    </h4>
                    <div class="flex flex-wrap gap-6">
                      <UFormField label="ПДВ" class="min-w-[200px]">
                        <USelectMenu
                          v-model="priceCriterionVat"
                          :items="vatOptions"
                          value-key="value"
                          placeholder="Оберіть варіант"
                        />
                      </UFormField>
                      <UFormField label="Доставка" class="min-w-[260px]">
                        <USelectMenu
                          v-model="priceCriterionDelivery"
                          :items="deliveryOptions"
                          value-key="value"
                          placeholder="Оберіть варіант"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <!-- Інші критерії тендера -->
                  <div class="border rounded-lg p-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3">
                      Інші критерії тендера
                    </h4>
                    <p class="text-sm text-gray-600 mb-3">
                      Додайте критерії з довідника. Учасники заповнюватимуть їх
                      у пропозиціях.
                    </p>
                    <div class="flex items-end gap-3 mb-3">
                      <div class="w-full max-w-xl">
                        <ContentSearch
                          label="Пошук і додавання критеріїв"
                          placeholder="Критерії з довідника"
                          search-placeholder="Пошук критеріїв"
                          :tree="criteriaSearchTree"
                          :selected-ids="selectedCriteriaIds"
                          :search-term="criteriaSearch"
                          @toggle="toggleTenderCriterion"
                          @update:search-term="criteriaSearch = $event"
                        />
                      </div>
                    </div>
                    <ul
                      v-if="tenderCriteria.length > 0"
                      class="space-y-2 text-sm"
                    >
                      <li
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="flex items-center justify-between gap-2 py-2 px-3 rounded-md bg-gray-50 border border-gray-200"
                      >
                        <span class="font-medium">{{ c.name }}</span>
                        <span class="text-gray-500 text-xs">{{
                          criterionTypeLabel(c.type)
                        }}</span>
                        <UButton
                          icon="i-heroicons-trash"
                          size="xs"
                          variant="ghost"
                          color="error"
                          aria-label="Видалити з тендера"
                          @click="removeCriterionFromTender(c)"
                        />
                      </li>
                    </ul>
                    <p v-else class="text-sm text-gray-500 py-2">
                      Критерії не додано. Оберіть критерії з довідника вище.
                    </p>
                  </div>
                </div>
              </template>
            </UTabs>
          </div>
        </template>

        <template v-else-if="displayStage === 'acceptance'">
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Прийом пропозицій</h3>
            </template>
            <p class="text-sm text-gray-600">
              На цьому етапі відображаються пропозиції учасників по позиціях.
            </p>
            <p class="text-xs text-gray-500 mt-2">
              Якщо час завершення минув, етап автоматично переведеться на «Вибір
              рішення».
            </p>
          </UCard>
        </template>

        <template v-else-if="displayStage === 'decision'">
          <div class="space-y-6">
            <!-- Верхня область: орієнтовна ринкова та рішення -->
            <div class="border rounded-lg p-4 bg-gray-50/50">
              <div class="flex flex-wrap items-end gap-6">
                <UFormField label="Орієнтовна ринкова" class="min-w-[220px]">
                  <USelectMenu
                    v-model="estimatedMarketMethod"
                    :items="estimatedMarketOptions"
                    value-key="value"
                    placeholder="Оберіть"
                  />
                </UFormField>
                <UFormField label="Рішення" class="min-w-[200px]">
                  <UInput placeholder="—" disabled />
                </UFormField>
              </div>
            </div>

            <!-- Таблиця позицій (стиль як на підготовці) -->
            <div class="border rounded-lg p-4 bg-white">
              <h4 class="text-sm font-semibold text-gray-700 mb-3">
                Позиції тендера
              </h4>
              <div class="min-h-0 overflow-auto">
                <UTable
                  :data="decisionTableRows"
                  :columns="decisionTableColumns"
                  class="w-full"
                >
                  <template #best_counterparty-cell="{ row }">
                    <span
                      class="inline-block w-full py-1 -my-1 px-2 -mx-2 rounded bg-green-50 text-gray-700"
                      >{{ row.original.best_counterparty }}</span
                    >
                  </template>
                  <template #best_price-cell="{ row }">
                    <span
                      class="inline-block w-full py-1 -my-1 px-2 -mx-2 rounded bg-green-50 text-gray-700"
                      >{{ row.original.best_price }}</span
                    >
                  </template>
                  <template #selected_counterparty-cell="{ row }">
                    <span
                      class="inline-block w-full py-1 -my-1 px-2 -mx-2 rounded bg-amber-50 text-gray-700"
                      >{{ row.original.selected_counterparty }}</span
                    >
                  </template>
                  <template #selected_price-cell="{ row }">
                    <span
                      class="inline-block w-full py-1 -my-1 px-2 -mx-2 rounded bg-amber-50 text-gray-700"
                      >{{ row.original.selected_price }}</span
                    >
                  </template>
                </UTable>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="displayStage === 'approval'">
          <div class="space-y-4">
            <UCard>
              <template #header>
                <h3 class="text-lg font-semibold">Затвердження</h3>
              </template>
              <p class="text-sm text-gray-600 mb-4">
                Перегляньте переможців по позиціях та підтвердьте рішення для завершення тендера.
              </p>
              <div class="border rounded-lg overflow-hidden">
                <table class="w-full text-sm border-collapse">
                  <thead>
                    <tr class="border-b bg-gray-50">
                      <th class="text-left p-2 font-medium">Позиція</th>
                      <th class="text-left p-2 font-medium">Кількість</th>
                      <th class="text-left p-2 font-medium">Переможець</th>
                      <th class="text-left p-2 font-medium">Ціна</th>
                      <th
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="text-left p-2 font-medium"
                      >
                        {{ c.name }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="pos in tender.value?.positions ?? []"
                      :key="pos.id"
                      class="border-b hover:bg-gray-50/50"
                    >
                      <td class="p-2">{{ pos.name }}</td>
                      <td class="p-2">{{ pos.quantity }} {{ pos.unit_name ?? '' }}</td>
                      <td class="p-2">{{ pos.winner_supplier_name ?? '—' }}</td>
                      <td class="p-2">{{ pos.winner_price ?? '—' }}</td>
                      <td
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="p-2"
                      >
                        {{ (pos.winner_criterion_values && (pos.winner_criterion_values[c.id] ?? pos.winner_criterion_values[String(c.id)])) ?? '—' }}
                      </td>
                    </tr>
                    <tr v-if="!(tender.value?.positions?.length)">
                      <td colspan="100" class="p-4 text-center text-gray-500">Немає позицій.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </UCard>
          </div>
        </template>

        <template v-else>
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">Завершений</h3>
            </template>
            <p class="text-sm text-gray-600">Тендер завершено.</p>
          </UCard>
        </template>
      </div>

      <aside class="w-56 flex-shrink-0 space-y-3">
        <template v-if="displayStage === 'passport'">
          <UButton class="w-full" :loading="saving" @click="savePassport"
            >Зберегти</UButton
          >
        </template>

        <template v-else-if="displayStage === 'preparation'">
          <template v-if="form.conduct_type === 'registration'">
            <p v-if="isViewingPreviousTour" class="text-xs text-gray-500 mb-2">
              Перегляд попереднього туру. Зміни пропозицій заборонені.
            </p>
            <UButton
              class="w-full"
              :disabled="isViewingPreviousTour"
              @click="openSubmitProposal"
              :loading="saving"
            >
              Подати пропозицію
            </UButton>
          </template>
          <template v-else>
            <UButton class="w-full" @click="openPublishModal"
              >Опублікувати</UButton
            >
            <UButton
              class="w-full"
              variant="outline"
              @click="
                alert(
                  'Модальне вікно запрошення учасників буде додано наступним кроком.',
                )
              "
              >Запросити учасників</UButton
            >
          </template>
          <UButton class="w-full" variant="outline" @click="goToProposalsPage">
            Прикріплені файли
          </UButton>
        </template>

        <template v-else-if="displayStage === 'acceptance'">
          <UButton class="w-full" @click="openTimingModal"
            >Змінити час проведення</UButton
          >
        </template>

        <template v-else-if="displayStage === 'decision'">
          <UButton
            class="w-full"
            variant="outline"
            @click="showWinnerModal = true"
          >
            Ручний вибір переможця
          </UButton>
          <UButton class="w-full" @click="showDecisionModal = true">
            Зафіксувати рішення
          </UButton>
        </template>

        <template v-else-if="displayStage === 'approval'">
          <UButton class="w-full" @click="approveTender">Затвердити</UButton>
        </template>
      </aside>
    </div>

    <UModal v-model:open="showPublishModal">
      <template #content>
        <UCard>
          <template #header><h3>Період проведення</h3></template>
          <div class="space-y-4">
            <UFormField label="Початок">
              <UInput v-model="timingForm.start_at" type="datetime-local" />
            </UFormField>
            <UFormField label="Завершення">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="publishTender"
                >Підтвердити</UButton
              >
              <UButton
                class="flex-1"
                variant="outline"
                @click="showPublishModal = false"
                >Скасувати</UButton
              >
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showTimingModal">
      <template #content>
        <UCard>
          <template #header><h3>Змінити час проведення</h3></template>
          <div class="space-y-4">
            <UFormField
              label="Початок"
              :help="
                canEditStart
                  ? ''
                  : 'Після старту час початку змінювати не можна'
              "
            >
              <UInput
                v-model="timingForm.start_at"
                type="datetime-local"
                :disabled="!canEditStart"
              />
            </UFormField>
            <UFormField label="Завершення">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="saveTiming">Зберегти</UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showTimingModal = false"
                >Скасувати</UButton
              >
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showWinnerModal">
      <template #content>
        <UCard>
          <template #header><h3>Ручний вибір переможця</h3></template>
          <p class="text-sm text-gray-600 mb-4">
            Оберіть переможця по кожній позиції з контрагентів, які подали
            пропозиції.
          </p>
          <div class="space-y-3 max-h-[60vh] overflow-auto">
            <div
              v-for="pos in tenderPositions"
              :key="pos.id"
              class="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-3"
            >
              <span class="text-sm font-medium min-w-[140px]">{{
                pos.name
              }}</span>
              <USelectMenu
                :model-value="selectedWinnerByPosition[pos.id] ?? null"
                :items="decisionWinnerOptionsForPosition(pos.id)"
                value-key="value"
                placeholder="Оберіть контрагента"
                class="flex-1 min-w-[200px]"
                @update:model-value="(v) => setDecisionWinner(pos.id, v)"
              />
            </div>
          </div>
          <template #footer>
            <UButton @click="showWinnerModal = false">Закрити</UButton>
          </template>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showDecisionModal">
      <template #content>
        <UCard>
          <template #header><h3>Зафіксувати рішення</h3></template>
          <div class="space-y-2">
            <UButton class="w-full" @click="fixDecision('winner')">
              Закрити із переможцями
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="fixDecision('next_round')"
            >
              Перенести на наступний тур
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="fixDecision('cancel')"
            >
              Скасувати
            </UButton>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Тендер на закупівлю" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));
const { getAuthHeaders } = useAuth();
const { fetch } = useApi();

const tender = ref<any | null>(null);
const loading = ref(true);
const saving = ref(false);
const tourOptions = ref<{ value: number; label: string }[]>([]);
const prepTab = ref<"positions" | "criteria">("positions");
const prepTabs = [
  { label: "Позиції", value: "positions" },
  { label: "Критерії", value: "criteria" },
];

// Параметри цінового критерія (значення value з опцій)
const priceCriterionVat = ref<string | undefined>(undefined);
const priceCriterionDelivery = ref<string | undefined>(undefined);
const vatOptions = [
  { value: "with_vat", label: "з ПДВ" },
  { value: "without_vat", label: "без ПДВ" },
];
const deliveryOptions = [
  { value: "with_delivery", label: "із урахуванням доставки" },
  { value: "without_delivery", label: "без урахування доставки" },
];

// Критерії з довідника та додані до тендера
const referenceCriteria = ref<any[]>([]);
const tenderCriteria = ref<any[]>([]);
const criteriaSearch = ref("");
const categorySearch = ref("");
const nomenclatureSearch = ref("");
const loadingNomenclatures = ref(false);
const tenderPositions = ref<any[]>([]);
const availableNomenclatures = ref<any[]>([]);

const showPublishModal = ref(false);
const showTimingModal = ref(false);
const showDecisionModal = ref(false);
const showWinnerModal = ref(false);
const timingForm = reactive({ start_at: "", end_at: "" });

const decisionProposals = ref<any[]>([]);
const estimatedMarketMethod = ref("arithmetic_mean");
const estimatedMarketOptions = [
  { value: "arithmetic_mean", label: "Середня арифметична" },
];
const selectedWinnerByPosition = ref<Record<number, number>>({});

const stageItems = [
  {
    value: "passport",
    title: "Паспорт тендера",
    icon: "i-heroicons-document-text",
  },
  {
    value: "preparation",
    title: "Підготовка процедури",
    icon: "i-heroicons-clipboard-document-list",
  },
  {
    value: "acceptance",
    title: "Прийом пропозицій",
    icon: "i-heroicons-envelope",
  },
  { value: "decision", title: "Вибір рішення", icon: "i-heroicons-scale" },
  {
    value: "approval",
    title: "Затвердження",
    icon: "i-heroicons-check-circle",
  },
  { value: "completed", title: "Завершений", icon: "i-heroicons-flag" },
];

const isRegistration = computed(
  () => (tender.value?.conduct_type ?? form.conduct_type) === "registration",
);
const isViewingPreviousTour = computed(
  () => tender.value && tender.value.is_latest_tour === false,
);

const visibleStageItems = computed(() => {
  if (isRegistration.value) {
    return stageItems.filter((s) => s.value !== "acceptance");
  }
  return stageItems;
});

const STAGE_ORDER = computed(() => visibleStageItems.value.map((s) => s.value));

const displayStage = ref<string>("passport");

const stepperItems = computed(() => {
  const currentStage = tender.value?.stage ?? "passport";
  const progressIndex = STAGE_ORDER.value.indexOf(currentStage);
  return visibleStageItems.value.map((s, index) => ({
    ...s,
    description: "",
    class: [
      index < progressIndex ? "tender-step-done" : "",
      index === progressIndex ? "tender-step-progress-current" : "",
      s.value === displayStage.value ? "tender-step-viewing" : "",
    ]
      .filter(Boolean)
      .join(" "),
  }));
});

const currentStepValue = computed({
  get: () => displayStage.value,
  set: (value: string) => {
    const currentStage = tender.value?.stage ?? "passport";
    const currentIndex = STAGE_ORDER.value.indexOf(currentStage);
    const targetIndex = STAGE_ORDER.value.indexOf(value);
    if (targetIndex !== -1 && targetIndex <= currentIndex) {
      displayStage.value = value;
    }
  },
});

const tenderCpvLabels = ref<string[]>([]);
const form = reactive({
  name: "",
  category: null as number | null,
  cpv_ids: [] as number[],
  expense_article: null as number | null,
  estimated_budget: null as number | null,
  branch: null as number | null,
  department: null as number | null,
  conduct_type: "rfx",
  publication_type: "open",
  currency: null as number | null,
  general_terms: "",
});
const selectedCategoryIds = computed(() =>
  form.category ? [form.category] : [],
);

const conductTypeOptions = [
  { value: "registration", label: "Реєстрація закупівлі" },
  { value: "rfx", label: "Збір пропозицій (RFx)" },
  { value: "online_auction", label: "Онлайн торги" },
];
const publicationTypeOptions = [
  { value: "open", label: "Відкрита процедура" },
  { value: "closed", label: "Закрита процедура" },
];

const categoryTree = ref<any[]>([]);
const expenseOptions = ref<{ value: number; label: string }[]>([]);
const branchOptions = ref<{ value: number; label: string }[]>([]);
const departmentOptions = ref<{ value: number; label: string }[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);
const positionsColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "unit_name", header: "Од. виміру" },
  { accessorKey: "quantity", header: "Кількість" },
  { accessorKey: "description", header: "Опис" },
  { accessorKey: "vat", header: "ПДВ" },
];

function getProposalPositionValue(proposal: any, positionId: number) {
  const list = proposal?.position_values || [];
  return list.find(
    (pv: any) =>
      (pv.tender_position_id ??
        pv.tender_position?.id ??
        pv.tender_position) === positionId,
  );
}

function getBestProposalIdForPosition(positionId: number, isPurchase: boolean) {
  const withPrice: { id: number; price: number }[] = [];
  for (const p of decisionProposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const num = Number(pv?.price);
    if (!Number.isNaN(num)) withPrice.push({ id: p.id, price: num });
  }
  if (withPrice.length === 0) return null;
  const best = isPurchase
    ? withPrice.reduce((a, b) => (a.price <= b.price ? a : b))
    : withPrice.reduce((a, b) => (a.price >= b.price ? a : b));
  return best.id;
}

function decisionWinnerOptionsForPosition(positionId: number) {
  return decisionProposals.value
    .filter((p) => {
      const pv = getProposalPositionValue(p, positionId);
      return pv != null && pv.price != null && !Number.isNaN(Number(pv.price));
    })
    .map((p) => ({
      value: p.id,
      label:
        p.supplier_name ?? p.supplier_company?.name ?? `Пропозиція #${p.id}`,
    }));
}

function setDecisionWinner(positionId: number, proposalId: number | null) {
  const next = { ...selectedWinnerByPosition.value };
  if (proposalId != null) next[positionId] = proposalId;
  else delete next[positionId];
  selectedWinnerByPosition.value = next;
}

const decisionTableColumns = [
  { accessorKey: "name", header: "Позиція" },
  { accessorKey: "quantity_unit", header: "Кількість" },
  { accessorKey: "market_value", header: "Орієнтовна ринкова" },
  { accessorKey: "best_counterparty", header: "Кращий контрагент" },
  { accessorKey: "best_price", header: "Краща ціна" },
  { accessorKey: "selected_counterparty", header: "Контрагент що обирається" },
  { accessorKey: "selected_price", header: "Ціна що обирається" },
  { accessorKey: "price_diff", header: "Розбіжність у ціні" },
  { accessorKey: "economy_market", header: "Економія по орієнтовній ринковій" },
];

const decisionTableRows = computed(() => {
  const proposals = decisionProposals.value;
  const selected = selectedWinnerByPosition.value;
  const isPurchase = true;
  return tenderPositions.value.map((pos) => {
    const pvList = proposals
      .map((p) => ({ proposal: p, pv: getProposalPositionValue(p, pos.id) }))
      .filter(
        (x) =>
          x.pv != null &&
          Number(x.pv.price) !== undefined &&
          !Number.isNaN(Number(x.pv.price)),
      );
    const prices = pvList.map((x) => Number(x.pv!.price));
    const avgPrice =
      prices.length > 0
        ? prices.reduce((a, b) => a + b, 0) / prices.length
        : null;
    const marketValue =
      estimatedMarketMethod.value === "arithmetic_mean" && avgPrice != null
        ? avgPrice.toFixed(2)
        : avgPrice != null
          ? avgPrice.toFixed(2)
          : "—";

    let bestProposal: any = null;
    let bestPrice: number | null = null;
    if (pvList.length > 0) {
      const byPrice = [...pvList].sort((a, b) =>
        isPurchase
          ? Number(a.pv!.price) - Number(b.pv!.price)
          : Number(b.pv!.price) - Number(a.pv!.price),
      );
      bestProposal = byPrice[0].proposal;
      bestPrice = Number(byPrice[0].pv!.price);
    }
    const bestCounterparty =
      bestProposal?.supplier_name ??
      bestProposal?.supplier_company?.name ??
      "—";
    const bestPriceStr = bestPrice != null ? bestPrice.toFixed(2) : "—";

    const selectedProposalId = selected[pos.id] ?? bestProposal?.id ?? null;
    const selectedProposal = selectedProposalId
      ? proposals.find((p) => p.id === selectedProposalId)
      : bestProposal;
    const selectedPv = selectedProposal
      ? getProposalPositionValue(selectedProposal, pos.id)
      : null;
    const selectedPrice =
      selectedPv != null && !Number.isNaN(Number(selectedPv.price))
        ? Number(selectedPv.price)
        : null;
    const selectedCounterparty =
      selectedProposal?.supplier_name ??
      selectedProposal?.supplier_company?.name ??
      "—";
    const selectedPriceStr =
      selectedPrice != null ? selectedPrice.toFixed(2) : "—";

    const priceDiff =
      bestPrice != null && selectedPrice != null
        ? selectedPrice - bestPrice
        : null;
    const priceDiffStr = priceDiff != null ? priceDiff.toFixed(2) : "—";

    const economyMarket =
      avgPrice != null && selectedPrice != null
        ? avgPrice - selectedPrice
        : null;
    const economyMarketStr =
      economyMarket != null ? economyMarket.toFixed(2) : "—";

    return {
      id: pos.id,
      name: pos.name,
      quantity_unit: pos.unit_name
        ? `${pos.quantity} ${pos.unit_name}`
        : String(pos.quantity),
      market_value: marketValue,
      best_counterparty: bestCounterparty,
      best_price: bestPriceStr,
      selected_counterparty: selectedCounterparty,
      selected_price: selectedPriceStr,
      price_diff: priceDiffStr,
      economy_market: economyMarketStr,
    };
  });
});

const selectedNomenclatureIds = computed(() =>
  tenderPositions.value.map((p) => p.nomenclature_id),
);
const nomenclatureSearchTree = computed(() =>
  availableNomenclatures.value.map((n: any) => ({
    id: n.id,
    name: `${n.name}${n.unit_name ? ` (${n.unit_name})` : ""}`,
    children: [],
  })),
);

const canEditStart = computed(() => {
  if (!tender.value?.start_at) return true;
  return new Date() < new Date(tender.value.start_at);
});

const canSubmitProposal = computed(() => {
  if (!tender.value || tender.value.conduct_type !== "registration")
    return false;
  const hasPositions = tenderPositions.value.length >= 1;
  const hasPriceParams =
    !!priceCriterionVat.value && !!priceCriterionDelivery.value;
  return hasPositions && hasPriceParams;
});

async function savePreparation() {
  if (!tender.value?.id) return false;
  const payload: Record<string, unknown> = {
    positions: tenderPositions.value.map((p) => ({
      nomenclature_id: p.nomenclature_id,
      quantity: p.quantity,
      description: p.description ?? "",
    })),
    criterion_ids: tenderCriteria.value.map((c) => c.id),
    price_criterion_vat: priceCriterionVat.value ?? "",
    price_criterion_delivery: priceCriterionDelivery.value ?? "",
  };
  return patchTender(payload);
}

async function openSubmitProposal() {
  saving.value = true;
  try {
    await savePreparation();
    if (!canSubmitProposal.value) {
      const msg =
        tenderPositions.value.length < 1
          ? "Додайте хоча б одну позицію номенклатури в тендер."
          : !priceCriterionVat.value || !priceCriterionDelivery.value
            ? "Налаштуйте параметри цінового критерія (ПДВ та Доставка)."
            : "";
      alert(msg || "Неможливо відкрити подачу пропозицій.");
      return;
    }
    await navigateTo(`/cabinet/tenders/proposals/${tenderId.value}`);
  } finally {
    saving.value = false;
  }
}

function goToProposalsPage() {
  navigateTo(`/cabinet/tenders/proposals/${tenderId.value}`);
}

// Дерево критеріїв для ContentSearch (плоский список з полем name)
const criteriaSearchTree = computed(() =>
  referenceCriteria.value.map((c: any) => ({
    id: c.id,
    name: `${c.name} (${criterionTypeLabel(c.type)})`,
    children: [],
  })),
);

const selectedCriteriaIds = computed(() =>
  tenderCriteria.value.map((c) => c.id),
);

function criterionTypeLabel(type: string) {
  const map: Record<string, string> = {
    numeric: "Числовий",
    text: "Текстовий",
    file: "Файловий",
    boolean: "Булевий",
  };
  return map[type] ?? type;
}

async function loadReferenceCriteria() {
  const { data } = await fetch("/tender-criteria/", {
    headers: getAuthHeaders(),
  });
  referenceCriteria.value = Array.isArray(data) ? data : [];
}

function toggleTenderCriterion(criterionId: number) {
  const existing = tenderCriteria.value.find((c) => c.id === criterionId);
  if (existing) {
    tenderCriteria.value = tenderCriteria.value.filter(
      (x) => x.id !== criterionId,
    );
    return;
  }
  const c = referenceCriteria.value.find((x) => x.id === criterionId);
  if (c) tenderCriteria.value = [...tenderCriteria.value, c];
}

function removeCriterionFromTender(c: any) {
  tenderCriteria.value = tenderCriteria.value.filter((x) => x.id !== c.id);
}

function flattenTree(
  items: any[],
  level = 0,
): { value: number; label: string }[] {
  const out: { value: number; label: string }[] = [];
  for (const item of items || []) {
    out.push({
      value: item.id,
      label: `${"  ".repeat(level)}${item.name || item.label}`,
    });
    if (item.children?.length)
      out.push(...flattenTree(item.children, level + 1));
  }
  return out;
}

function toggleCategory(id: number) {
  form.category = form.category === id ? null : id;
  if (form.category) {
    form.cpv_ids = [];
    tenderCpvLabels.value = [];
  }
}

function isoToInput(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function inputToIso(value: string) {
  return value ? new Date(value).toISOString() : null;
}

async function loadTender() {
  loading.value = true;
  try {
    const { data, error } = await fetch(
      `/procurement-tenders/${tenderId.value}/`,
      { headers: getAuthHeaders() },
    );
    if (error || !data) {
      tender.value = null;
      return;
    }
    tender.value = data;
    const stage = data.stage ?? "passport";
    displayStage.value =
      data.conduct_type === "registration" && stage === "acceptance"
        ? "decision"
        : stage;
    if (Array.isArray(data.positions)) {
      tenderPositions.value = data.positions.map((p: any) => ({
        id: p.id,
        nomenclature_id: p.nomenclature,
        name: p.name,
        unit_name: p.unit_name ?? "",
        quantity: p.quantity ?? 1,
        description: p.description ?? "",
      }));
    }
    priceCriterionVat.value = data.price_criterion_vat ?? undefined;
    priceCriterionDelivery.value = data.price_criterion_delivery ?? undefined;
    if (Array.isArray(data.criteria)) {
      tenderCriteria.value = data.criteria;
    }
    const cpvList = data.cpv_categories || [];
    form.cpv_ids = cpvList.length
      ? cpvList.map((c: any) => c.id)
      : data.cpv_category != null
        ? [data.cpv_category]
        : [];
    tenderCpvLabels.value = cpvList.length
      ? cpvList.map(
          (c: any) =>
            c.label || `${c.cpv_code || ""} - ${c.name_ua || ""}`.trim(),
        )
      : data.cpv_label
        ? [data.cpv_label]
        : [];
    Object.assign(form, {
      name: data.name ?? "",
      category: data.category ?? null,
      expense_article: data.expense_article ?? null,
      estimated_budget: data.estimated_budget ?? null,
      branch: data.branch ?? null,
      department: data.department ?? null,
      conduct_type: data.conduct_type ?? "rfx",
      publication_type: data.publication_type ?? "open",
      currency: data.currency ?? null,
      general_terms: data.general_terms ?? "",
    });
    timingForm.start_at = isoToInput(data.start_at);
    timingForm.end_at = isoToInput(data.end_at);
    await loadTours();
    await autoAdvanceAcceptance();
  } finally {
    loading.value = false;
  }
}

async function loadTours() {
  if (!tenderId.value) return;
  const { data } = await fetch(
    `/procurement-tenders/${tenderId.value}/tours/`,
    { headers: getAuthHeaders() },
  );
  const list = Array.isArray(data) ? data : [];
  tourOptions.value = list.map((t: { id: number; tour_number: number }) => ({
    value: t.id,
    label: `Тур ${t.tour_number}`,
  }));
}

function onTourSelect(value: number | null) {
  if (value != null && value !== tenderId.value) {
    navigateTo(`/cabinet/tenders/${value}`);
  }
}

async function loadOptions() {
  const headers = getAuthHeaders();
  const [cats, expenses, branches, currencies] = await Promise.all([
    fetch("/categories/", { headers }),
    fetch("/expenses/", { headers }),
    fetch("/branches/", { headers }),
    fetch("/currencies/", { headers }),
  ]);
  categoryTree.value = (cats.data as any[]) || [];
  expenseOptions.value = flattenTree((expenses.data as any[]) || []);
  branchOptions.value = flattenTree((branches.data as any[]) || []);
  currencyOptions.value = ((currencies.data as any[]) || []).map((c: any) => ({
    value: c.id,
    label: `${c.code} - ${c.name}`,
  }));
}

async function loadNomenclaturesForPreparation() {
  loadingNomenclatures.value = true;
  try {
    const headers = getAuthHeaders();
    let items: any[] = [];

    if ((form.cpv_ids?.length ?? 0) > 0) {
      const merged = new Map<number, any>();
      for (const cpvId of form.cpv_ids) {
        const { data: byCpv } = await fetch(`/nomenclatures/?cpv_id=${cpvId}`, {
          headers,
        });
        for (const n of (byCpv as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    } else if (form.category) {
      const { data: byCategory } = await fetch(
        `/nomenclatures/?category_id=${form.category}`,
        { headers },
      );
      const merged = new Map<number, any>();
      for (const n of (byCategory as any[]) || []) merged.set(n.id, n);

      const { data: categoryData } = await fetch(
        `/categories/${form.category}/`,
        {
          headers,
        },
      );
      const cpvIds: number[] = ((categoryData as any)?.cpvs || []).map(
        (c: any) => c.id,
      );
      for (const cpvId of cpvIds) {
        const { data: byCpv } = await fetch(`/nomenclatures/?cpv_id=${cpvId}`, {
          headers,
        });
        for (const n of (byCpv as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    }

    availableNomenclatures.value = items;

    const availableIds = new Set(items.map((n: any) => n.id));
    tenderPositions.value = tenderPositions.value.filter((p) =>
      availableIds.has(p.nomenclature_id),
    );
  } finally {
    loadingNomenclatures.value = false;
  }
}

function toggleTenderPosition(nomenclatureId: number) {
  const existingIndex = tenderPositions.value.findIndex(
    (p) => p.nomenclature_id === nomenclatureId,
  );

  if (existingIndex >= 0) {
    tenderPositions.value.splice(existingIndex, 1);
    return;
  }

  const n = availableNomenclatures.value.find(
    (x: any) => x.id === nomenclatureId,
  );
  if (!n) return;

  tenderPositions.value.push({
    nomenclature_id: n.id,
    name: n.name,
    unit_name: n.unit_name || "",
    quantity: 1,
    description: "",
    vat: "",
  });
}

async function loadDepartments() {
  if (!form.branch) {
    departmentOptions.value = [];
    return;
  }
  const { data } = await fetch(`/departments/?branch_id=${form.branch}`, {
    headers: getAuthHeaders(),
  });
  departmentOptions.value = flattenTree((data as any[]) || []);
}

function onBranchChange() {
  form.department = null;
  loadDepartments();
}

async function patchTender(payload: Record<string, unknown>) {
  if (!tender.value?.id) return false;
  const { data, error } = await fetch(
    `/procurement-tenders/${tender.value.id}/`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: payload,
    },
  );
  if (error || !data) return false;
  tender.value = { ...tender.value, ...data };
  if (data.stage != null) {
    const stage = data.stage;
    displayStage.value =
      tender.value?.conduct_type === "registration" && stage === "acceptance"
        ? "decision"
        : stage;
  }
  return true;
}

async function savePassport() {
  saving.value = true;
  try {
    await patchTender({
      name: form.name,
      category: form.category,
      cpv_ids: form.cpv_ids,
      expense_article: form.expense_article,
      estimated_budget: form.estimated_budget,
      branch: form.branch,
      department: form.department,
      conduct_type: form.conduct_type,
      publication_type: form.publication_type,
      currency: form.currency,
      general_terms: form.general_terms,
      stage: "preparation",
    });
  } finally {
    saving.value = false;
  }
}

function openPublishModal() {
  timingForm.start_at = isoToInput(tender.value?.start_at);
  timingForm.end_at = isoToInput(tender.value?.end_at);
  showPublishModal.value = true;
}

function openTimingModal() {
  timingForm.start_at = isoToInput(tender.value?.start_at);
  timingForm.end_at = isoToInput(tender.value?.end_at);
  showTimingModal.value = true;
}

async function publishTender() {
  if (!timingForm.start_at || !timingForm.end_at) return;
  const ok = await patchTender({
    start_at: inputToIso(timingForm.start_at),
    end_at: inputToIso(timingForm.end_at),
    stage: "acceptance",
  });
  if (ok) showPublishModal.value = false;
}

async function saveTiming() {
  const payload: Record<string, unknown> = {
    end_at: inputToIso(timingForm.end_at),
  };
  if (canEditStart.value) payload.start_at = inputToIso(timingForm.start_at);
  const ok = await patchTender(payload);
  if (ok) showTimingModal.value = false;
}

async function goToDecision() {
  await patchTender({ stage: "decision" });
}

async function autoAdvanceAcceptance() {
  if (tender.value?.stage !== "acceptance" || !tender.value?.end_at) return;
  if (new Date() > new Date(tender.value.end_at)) {
    await patchTender({ stage: "decision" });
  }
}

async function fixDecision(mode: "winner" | "cancel" | "next_round") {
  showDecisionModal.value = false;
  saving.value = true;
  try {
    const body: { mode: string; position_winners?: { position_id: number; proposal_id: number }[] } = { mode };
    if (mode === "winner") {
      body.position_winners = Object.entries(selectedWinnerByPosition.value).map(([position_id, proposal_id]) => ({
        position_id: Number(position_id),
        proposal_id,
      }));
    }
    const { data, error } = await fetch(
      `/procurement-tenders/${tenderId.value}/fix-decision/`,
      {
        method: "POST",
        headers: getAuthHeaders(),
        body,
      },
    );
    if (error || !data) return;
    if (data.id && data.stage === "preparation") {
      await navigateTo(`/cabinet/tenders/${data.id}`);
      return;
    }
    await loadTender();
  } finally {
    saving.value = false;
  }
}

async function approveTender() {
  await patchTender({ stage: "completed" });
}

async function loadDecisionProposals() {
  if (!tenderId.value) return;
  const { data } = await fetch(
    `/procurement-tenders/${tenderId.value}/proposals/`,
    { headers: getAuthHeaders() },
  );
  decisionProposals.value = Array.isArray(data) ? data : [];
  const next: Record<number, number> = {};
  for (const pos of tenderPositions.value) {
    const bestId = getBestProposalIdForPosition(pos.id, true);
    if (bestId != null) next[pos.id] = bestId;
  }
  selectedWinnerByPosition.value = next;
}

onMounted(async () => {
  await loadTender();
  await loadOptions();
  await loadNomenclaturesForPreparation();
  if (form.branch) await loadDepartments();
  if (displayStage.value === "decision") await loadDecisionProposals();
});

watch(tenderId, () => loadTender());
watch(displayStage, async (stage) => {
  if (stage === "decision") await loadDecisionProposals();
});
watch([isRegistration, () => displayStage.value], () => {
  if (isRegistration.value && displayStage.value === "acceptance") {
    displayStage.value = "decision";
  }
});
watch(
  () => [form.category, form.cpv_ids, tender.value?.stage],
  async () => {
    if (tender.value?.stage === "preparation") {
      await loadNomenclaturesForPreparation();
    }
  },
);
watch(prepTab, (tab) => {
  if (tab === "criteria") loadReferenceCriteria();
});
</script>

<style scoped>
/* Компактний степер */
.tender-stepper--compact :deep([data-slot="header"]) {
  gap: 0.25rem;
}
.tender-stepper--compact :deep([data-slot="indicator"]) {
  width: 1.75rem;
  height: 1.75rem;
  font-size: 0.75rem;
}
.tender-stepper--compact :deep([data-slot="title"]) {
  font-size: 0.8125rem;
}
.tender-stepper--compact :deep([data-slot="wrapper"]) {
  min-height: auto;
}
/* Прогрес: пройдені кроки та поточний етап тендера — акцентний колір */
.tender-stepper :deep(.tender-step-done [data-slot="trigger"]),
.tender-stepper :deep(.tender-step-progress-current [data-slot="trigger"]) {
  background-color: var(--color-primary-500);
  color: white;
}
.tender-stepper :deep(.tender-step-done [data-slot="separator"]) {
  background-color: var(--color-primary-500);
}
/* Крок, на якому зараз користувач (перегляд) — світліший */
.tender-stepper :deep(.tender-step-viewing [data-slot="trigger"]) {
  background-color: var(--color-primary-300);
  color: white;
}
</style>
