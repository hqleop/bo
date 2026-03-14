<template>
  <div>
    <div v-if="!loading && !tender" class="text-center py-12 text-gray-500">
      Тендер не знайдено.
    </div>
    <div v-else-if="tender" class="h-full flex flex-col">
      <div class="mb-4">
        <h1 class="text-xl font-semibold text-gray-900 truncate">
          № {{ tender.number }}
          <span class="font-normal text-gray-700">{{ tender.name }}</span>
        </h1>
      </div>
      <div
        v-if="!isParticipant"
        class="tender-stepper tender-stepper--compact mb-2"
      >
        <UStepper
          :model-value="currentStage"
          :items="stepperItems"
          value-key="value"
          size="sm"
          @update:model-value="onStageClick"
        />
      </div>

      <div class="flex flex-1 min-h-0 gap-6">
        <div class="flex-1 min-w-0 min-h-0 flex flex-col gap-4">
          <div class="flex items-center justify-between gap-4">
            <h2 class="text-base font-bold text-gray-800">
              Подача пропозицій (продаж)
            </h2>
            <UButton
              variant="ghost"
              size="sm"
              icon="i-heroicons-arrow-left"
              @click="
                isParticipant
                  ? navigateTo('/cabinet/participation?type=sales')
                  : goBack()
              "
            >
              {{
                isParticipant
                  ? "До списку тендерів"
                  : "Повернутись до підготовки"
              }}
            </UButton>
          </div>
          <p
            v-if="isViewingPreviousTour"
            class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
          >
            Перегляд попереднього туру. Зміни пропозицій заборонені.
          </p>
          <UFormField v-if="!isParticipant" label="Контрагент (покупець)">
            <div class="flex gap-2 items-center">
              <span
                v-if="selectedSupplier"
                class="flex-1 py-2 px-3 border border-gray-200 rounded bg-gray-50"
              >
                {{ selectedSupplier.label }}
                <span
                  v-if="selectedSupplier.edrpou"
                  class="text-gray-500 text-sm"
                  >({{ selectedSupplier.edrpou }})</span
                >
              </span>
              <span
                v-else
                class="flex-1 py-2 px-3 border border-gray-200 rounded bg-gray-50 text-gray-500"
                >Не обрано</span
              >
              <UButton
                variant="outline"
                :disabled="isViewingPreviousTour"
                @click="showSupplierModal = true"
              >
                Обрати контрагента
              </UButton>
            </div>
          </UFormField>

          <div
            v-if="tenderCriteriaGeneral.length > 0"
            class="rounded-lg border border-blue-200 bg-blue-50/50 p-3 space-y-3 mb-4"
          >
            <h4 class="text-sm font-semibold text-gray-800">
              Загальні критерії
            </h4>
            <p class="text-xs text-gray-600">
              Одне значення стосується всіх позицій.
            </p>
            <div class="flex flex-wrap gap-4">
              <UFormField
                v-for="c in tenderCriteriaGeneral"
                :key="c.id"
                :label="c.name"
                class="mb-0 min-w-[200px]"
              >
                <template
                  v-if="
                    currentProposal &&
                    !isViewingPreviousTour &&
                    (!isParticipant || participantCanEdit)
                  "
                >
                  <UInput
                    v-if="criterionInputKind(c) === 'text'"
                    v-model="generalCriterionValues[c.id]"
                    size="sm"
                    class="w-full"
                    @blur="savePositionValues"
                  />
                  <UInput
                    v-else-if="criterionInputKind(c) === 'number'"
                    v-model="generalCriterionValues[c.id]"
                    type="number"
                    step="0.0001"
                    size="sm"
                    class="w-full"
                    @blur="savePositionValues"
                  />
                  <DateValuePicker
                    v-else-if="criterionInputKind(c) === 'date'"
                    size="sm"
                    class="w-full"
                    :model-value="
                      String(generalCriterionValues[c.id] ?? '').trim()
                    "
                    @update:model-value="
                      (value) => {
                        generalCriterionValues[c.id] = value;
                        savePositionValues();
                      }
                    "
                  />
                  <USelectMenu
                    v-else-if="criterionInputKind(c) === 'boolean'"
                    v-model="generalCriterionValues[c.id]"
                    :items="booleanCriterionOptions"
                    value-key="value"
                    label-key="label"
                    placeholder="Оберіть"
                    class="w-full"
                    @update:model-value="savePositionValues"
                  />
                  <div v-else class="space-y-2">
                    <UFileUpload
                      :model-value="getGeneralCriterionFileModel(c.id)"
                      :multiple="false"
                      label="Оберіть файл"
                      @update:model-value="
                        onGeneralCriterionFileChange(c.id, $event)
                      "
                    />
                    <p class="text-xs text-gray-600">
                      {{
                        formatCriterionValue(c, generalCriterionValues[c.id]) ||
                        "Файл не обрано"
                      }}
                    </p>
                  </div>
                </template>
                <span v-else class="block py-1.5 text-sm text-gray-700">{{
                  formatCriterionValue(c, generalCriterionValues[c.id]) || "-"
                }}</span>
              </UFormField>
            </div>
          </div>

          <div class="flex-1 min-h-0 overflow-auto">
            <UCard>
              <template #header>
                <h3 class="text-lg font-semibold">
                  Позиції тендера (додані на етапі Підготовка)
                </h3>
              </template>
              <p v-if="!tenderPositions.length" class="text-gray-500 py-4">
                У тендері немає позицій. Додайте позиції на етапі «Підготовка
                процедури» та поверніться сюди.
              </p>
              <template v-else>
                <div class="overflow-x-auto">
                  <table class="w-full text-sm border-collapse">
                    <thead>
                      <tr class="border-b border-gray-200 bg-gray-50">
                        <th class="text-left p-2 font-medium">Позиція</th>
                        <th
                          v-if="isOnlineAuction"
                          class="text-left p-2 font-medium"
                        >
                          Од. виміру
                        </th>
                        <th class="text-left p-2 font-medium">Кількість</th>
                        <th
                          v-if="!isOnlineAuction"
                          class="text-left p-2 font-medium"
                        >
                          Опис
                        </th>
                        <th class="text-left p-2 font-medium whitespace-nowrap">
                          {{ priceColumnHeader }}
                        </th>
                        <th
                          v-if="isOnlineAuction"
                          class="text-left p-2 font-medium whitespace-nowrap"
                        >
                          Краща цінова пропозиція
                        </th>
                        <th
                          v-if="isOnlineAuction"
                          class="text-left p-2 font-medium"
                        >
                          Подати
                        </th>
                        <th
                          v-if="isOnlineAuction"
                          class="text-left p-2 font-medium whitespace-nowrap"
                        >
                          Нова цінова пропозиція
                        </th>
                        <th
                          v-if="isOnlineAuction"
                          class="text-left p-2 font-medium whitespace-nowrap"
                        >
                          Діапазон
                        </th>
                        <th
                          v-for="c in tenderCriteriaIndividual"
                          :key="c.id"
                          class="text-left p-2 font-medium"
                        >
                          {{ c.name
                          }}<span v-if="c.is_required" class="text-red-600">
                            *</span
                          >
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in positionRows"
                        :key="row.id"
                        class="border-b border-gray-200 hover:bg-gray-50/50"
                      >
                        <td class="p-2">{{ row.name }}</td>
                        <td v-if="isOnlineAuction" class="p-2">
                          {{ row.unit_name || "-" }}
                        </td>
                        <td class="p-2">
                          {{
                            isOnlineAuction
                              ? formatNumericDisplay(row.quantity)
                              : `${formatNumericDisplay(row.quantity)} ${row.unit_name}`
                          }}
                        </td>
                        <td v-if="!isOnlineAuction" class="p-2 max-w-[200px]">
                          {{ row.description || "—" }}
                        </td>
                        <td class="p-2">
                          <template v-if="isOnlineAuction">
                            <span class="text-gray-700">{{
                              row.price || "—"
                            }}</span>
                          </template>
                          <UInput
                            v-else-if="
                              currentProposal &&
                              !isViewingPreviousTour &&
                              (!isParticipant || participantCanEdit)
                            "
                            v-model="row.price"
                            type="number"
                            step="0.0001"
                            size="sm"
                            class="min-w-[100px]"
                            @blur="savePositionValues"
                          />
                          <span v-else class="text-gray-700">{{
                            row.price || "—"
                          }}</span>
                        </td>
                        <td v-if="isOnlineAuction" class="p-2">
                          {{ getCurrentBestPriceForPosition(row.id) ?? "—" }}
                        </td>
                        <td v-if="isOnlineAuction" class="p-2">
                          <UButton
                            size="xs"
                            :disabled="
                              !(
                                currentProposal &&
                                !isViewingPreviousTour &&
                                (!isParticipant || participantCanEdit) &&
                                submittingPositionId !== row.id
                              )
                            "
                            @click="submitPositionPrice(row.id)"
                          >
                            Подати
                          </UButton>
                        </td>
                        <td v-if="isOnlineAuction" class="p-2">
                          <UInput
                            v-if="
                              currentProposal &&
                              !isViewingPreviousTour &&
                              (!isParticipant || participantCanEdit)
                            "
                            v-model="row.next_price"
                            type="number"
                            step="0.0001"
                            size="sm"
                            class="min-w-[120px]"
                          />
                          <span v-else class="text-gray-700">—</span>
                        </td>
                        <td v-if="isOnlineAuction" class="p-2">
                          <template
                            v-if="
                              currentProposal &&
                              !isViewingPreviousTour &&
                              (!isParticipant || participantCanEdit) &&
                              getRangeValues(row.id)
                            "
                          >
                            <button
                              type="button"
                              class="text-green-700 hover:text-green-900 hover:underline"
                              @click="
                                applyRangeValue(
                                  row.id,
                                  getRangeValues(row.id)?.from ?? null,
                                )
                              "
                            >
                              {{
                                formatPriceValue(
                                  getRangeValues(row.id)?.from ?? 0,
                                )
                              }}
                            </button>
                            <span class="mx-1 text-gray-500">-</span>
                            <button
                              type="button"
                              class="text-green-700 hover:text-green-900 hover:underline"
                              @click="
                                applyRangeValue(
                                  row.id,
                                  getRangeValues(row.id)?.to ?? null,
                                )
                              "
                            >
                              {{
                                formatPriceValue(
                                  getRangeValues(row.id)?.to ?? 0,
                                )
                              }}
                            </button>
                          </template>
                          <span v-else>{{
                            getRangeDisplay(row.id) || "—"
                          }}</span>
                        </td>
                        <td
                          v-for="c in tenderCriteriaIndividual"
                          :key="c.id"
                          class="p-2"
                        >
                          <template
                            v-if="
                              currentProposal &&
                              !isViewingPreviousTour &&
                              (!isParticipant || participantCanEdit)
                            "
                          >
                            <UInput
                              v-if="criterionInputKind(c) === 'text'"
                              v-model="row.criterion_values[c.id]"
                              size="sm"
                              class="min-w-[80px]"
                              @blur="savePositionValues"
                            />
                            <UInput
                              v-else-if="criterionInputKind(c) === 'number'"
                              v-model="row.criterion_values[c.id]"
                              type="number"
                              step="0.0001"
                              size="sm"
                              class="min-w-[80px]"
                              @blur="savePositionValues"
                            />
                            <DateValuePicker
                              v-else-if="criterionInputKind(c) === 'date'"
                              size="sm"
                              class="min-w-[140px]"
                              :model-value="
                                String(row.criterion_values[c.id] ?? '').trim()
                              "
                              @update:model-value="
                                (value) => {
                                  row.criterion_values[c.id] = value;
                                  savePositionValues();
                                }
                              "
                            />
                            <USelectMenu
                              v-else-if="criterionInputKind(c) === 'boolean'"
                              v-model="row.criterion_values[c.id]"
                              :items="booleanCriterionOptions"
                              value-key="value"
                              label-key="label"
                              placeholder="Оберіть"
                              class="min-w-[120px]"
                              @update:model-value="savePositionValues"
                            />
                            <div v-else class="space-y-2 min-w-[170px]">
                              <UFileUpload
                                :model-value="
                                  getPositionCriterionFileModel(row.id, c.id)
                                "
                                :multiple="false"
                                label="Оберіть файл"
                                @update:model-value="
                                  onPositionCriterionFileChange(
                                    row.id,
                                    c.id,
                                    $event,
                                  )
                                "
                              />
                              <p class="text-xs text-gray-600">
                                {{
                                  formatCriterionValue(
                                    c,
                                    row.criterion_values[c.id],
                                  ) || "Файл не обрано"
                                }}
                              </p>
                            </div>
                          </template>
                          <span v-else class="text-gray-700">{{
                            formatCriterionValue(
                              c,
                              row.criterion_values[c.id],
                            ) || "-"
                          }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div
                  v-if="
                    currentProposal && !isViewingPreviousTour && !isParticipant
                  "
                  class="mt-3 pt-3 border-t border-gray-200"
                >
                  <UButton size="sm" @click="savePositionValues"
                    >Зберегти значення</UButton
                  >
                </div>
                <p
                  v-else-if="!isParticipant && !isViewingPreviousTour"
                  class="text-sm text-gray-500 mt-3"
                >
                  Оберіть контрагента (покупця) вище, щоб заповнити ціну та
                  критерії по позиціях.
                </p>
              </template>
            </UCard>
          </div>
        </div>

        <aside class="w-72 flex-shrink-0 flex flex-col gap-4">
          <div
            v-if="showAcceptanceTimingInfo"
            class="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-800"
          >
            <p class="font-semibold text-gray-900">Прийом пропозицій</p>
            <p class="mt-2 text-xs text-gray-600">
              Початок: {{ formatDateTime(tender?.start_at) }}
            </p>
            <p class="text-xs text-gray-600">
              Завершення: {{ formatDateTime(tender?.end_at) }}
            </p>
            <p class="mt-2 font-medium text-gray-900">
              Таймер: {{ timerText }}
            </p>
          </div>
          <template v-if="isParticipant">
            <div class="space-y-3">
              <UButton
                v-if="!isProposalSubmitted && !isOnlineAuction"
                class="w-full"
                :loading="submitWithdrawLoading"
                :disabled="!participantCanEdit"
                @click="onSubmitProposal"
              >
                Подати пропозицію
              </UButton>
              <UButton
                v-else-if="isProposalSubmitted"
                class="w-full"
                color="error"
                variant="solid"
                :loading="submitWithdrawLoading"
                :disabled="!participantCanWithdraw"
                @click="onWithdrawProposal"
              >
                Відкликати пропозицію
              </UButton>
              <UButton
                class="w-full"
                variant="outline"
                @click="showFilesModal = true"
              >
                Прикріплені файли
              </UButton>
              <div class="rounded-lg border border-gray-200 p-4 text-sm space-y-3">
                <div>
                  <p class="font-semibold text-gray-900">Організатор тендера</p>
                  <p class="mt-2 text-gray-800">
                    {{ tender?.organizer_contact?.full_name || "—" }}
                  </p>
                  <p class="text-gray-600">
                    {{ tender?.organizer_contact?.phone || "—" }}
                  </p>
                  <p class="text-gray-600 break-all">
                    {{ tender?.organizer_contact?.email || "—" }}
                  </p>
                </div>
                <UButton class="w-full" variant="outline" @click="openParticipantChatModal">
                  Чат із організатором
                </UButton>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="space-y-3">
              <UButton
                class="w-full"
                variant="outline"
                @click="showCheckModal = true"
              >
                Усі пропозиції
              </UButton>
              <UButton
                class="w-full"
                variant="outline"
                @click="showFilesModal = true"
              >
                Прикріплені файли
              </UButton>
            </div>
          </template>
        </aside>
      </div>

      <!-- Модальне вікно вибору контрагента (покупця) -->
      <UModal v-model:open="showSupplierModal">
        <template #content>
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">
                Обрати контрагента (покупця)
              </h3>
            </template>
            <UFormField label="Пошук за назвою або кодом ЄДРПОУ">
              <UInput
                v-model="supplierSearch"
                placeholder="Введіть назву або ЄДРПОУ"
                class="mb-3"
              />
            </UFormField>
            <div class="max-h-80 overflow-y-auto space-y-1">
              <button
                v-for="s in filteredSuppliers"
                :key="s.value"
                type="button"
                class="w-full text-left px-3 py-2 rounded hover:bg-gray-100 border border-transparent hover:border-gray-200"
                @click="selectSupplier(s)"
              >
                <span class="font-medium">{{ s.label }}</span>
                <span v-if="s.edrpou" class="text-gray-500 text-sm ml-2"
                  >({{ s.edrpou }})</span
                >
              </button>
              <p
                v-if="filteredSuppliers.length === 0"
                class="text-gray-500 py-4 text-center"
              >
                Нічого не знайдено. Змініть пошук або додайте контрагента в
                розділі «Контрагенти».
              </p>
            </div>
          </UCard>
        </template>
      </UModal>
      <UModal
        v-model:open="showParticipantChatModal"
        :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-2xl' }"
      >
        <template #content>
          <UCard class="min-w-0 max-h-[88vh] overflow-hidden">
            <template #header><h3>Чат із організатором</h3></template>
            <div class="flex max-h-[calc(88vh-5rem)] flex-col space-y-4">
              <div class="min-h-0 flex-1 overflow-auto rounded border border-gray-200 p-3">
                <div v-if="chatMessages.length" class="space-y-3">
                  <div
                    v-for="message in chatMessages"
                    :key="message.id"
                    class="rounded border border-gray-100 p-3"
                  >
                    <p class="font-medium text-gray-900">
                      {{ message.author_display || "—" }}
                    </p>
                    <p class="text-xs text-gray-500">
                      {{ formatDateTime(message.created_at) }}
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
                v-model="chatDraft"
                :rows="4"
                placeholder="Введіть текст повідомлення"
              />
              <div class="flex justify-end gap-2">
                <UButton variant="outline" @click="closeParticipantChatModal">
                  Скасувати
                </UButton>
                <UButton :loading="chatSending" @click="submitParticipantChatMessage">
                  Надіслати
                </UButton>
              </div>
            </div>
          </UCard>
        </template>
      </UModal>

      <UModal
        v-model:open="showCheckModal"
        :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
      >
        <template #content>
          <UCard class="flex flex-col max-h-[90vh] overflow-hidden">
            <template #header>
              <h3 class="text-lg font-semibold">Усі пропозиції</h3>
            </template>
            <div
              class="overflow-auto min-h-0 flex-1 resize-y min-h-[300px]"
              style="resize: vertical"
            >
              <table
                v-if="tenderPositions.length && proposals.length"
                class="w-full text-sm border-collapse"
              >
                <thead>
                  <tr class="border-b border-gray-200 bg-gray-100">
                    <th
                      class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                    >
                      Назва позиції
                    </th>
                    <th
                      class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                    >
                      Кількість
                    </th>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <th
                        :colspan="2 + tenderCriteria.length"
                        class="text-left p-2 font-medium bg-gray-200 border-l border-gray-300"
                      >
                        {{
                          proposal.supplier_company?.name ||
                          proposal.supplier_name ||
                          "—"
                        }}
                        <span
                          v-if="proposal.supplier_company?.edrpou"
                          class="text-gray-600 font-normal"
                        >
                          ({{ proposal.supplier_company.edrpou }})</span
                        >
                      </th>
                    </template>
                  </tr>
                  <tr class="border-b border-gray-200 bg-gray-50">
                    <th class="p-2 bg-gray-50"></th>
                    <th class="p-2 bg-gray-50"></th>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        {{ priceColumnHeader }}
                      </th>
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        Сума
                      </th>
                      <th
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="text-left p-2 font-medium border-l border-gray-200"
                      >
                        {{ c.name }}
                      </th>
                    </template>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="pos in tenderPositions"
                    :key="pos.id"
                    class="border-b border-gray-200 hover:bg-gray-50/50"
                  >
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ pos.name }}
                    </td>
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ formatNumericDisplay(pos.quantity) }}
                      {{ pos.unit_name || "" }}
                    </td>
                    <template v-for="proposal in proposals" :key="proposal.id">
                      <td
                        class="p-2 border-l border-gray-200"
                        :class="
                          (checkComparisonByPosition[pos.id]?.bestId ===
                            proposal.id &&
                            'bg-green-500/20') ||
                          (checkComparisonByPosition[pos.id]?.worstId ===
                            proposal.id &&
                            checkComparisonByPosition[pos.id]?.worstId !==
                              checkComparisonByPosition[pos.id]?.bestId &&
                            'bg-red-500/20')
                        "
                      >
                        {{
                          getProposalPositionValue(proposal, pos.id)?.price ??
                          "—"
                        }}
                      </td>
                      <td
                        class="p-2 border-l border-gray-200"
                        :class="
                          (checkComparisonByPosition[pos.id]?.bestId ===
                            proposal.id &&
                            'bg-green-500/20') ||
                          (checkComparisonByPosition[pos.id]?.worstId ===
                            proposal.id &&
                            checkComparisonByPosition[pos.id]?.worstId !==
                              checkComparisonByPosition[pos.id]?.bestId &&
                            'bg-red-500/20')
                        "
                      >
                        {{ getProposalPositionSum(proposal, pos) ?? "—" }}
                      </td>
                      <td
                        v-for="c in tenderCriteria"
                        :key="c.id"
                        class="p-2 border-l border-gray-200"
                      >
                        {{
                          getProposalCriterionValue(proposal, pos.id, c.id) ??
                          "—"
                        }}
                      </td>
                    </template>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-gray-500 py-8 text-center">
                Немає позицій або пропозицій для порівняння. Додайте позиції в
                тендер та заповніть пропозиції від контрагентів.
              </p>
            </div>
          </UCard>
        </template>
      </UModal>
      <UModal v-model:open="showFilesModal">
        <template #content>
          <UCard>
            <template #header><h3>Прикріплені файли</h3></template>
            <div v-if="tenderFilesLoading" class="text-gray-500">
              Завантаження...
            </div>
            <p v-else-if="tenderFilesError" class="text-sm text-red-600">
              {{ tenderFilesError }}
            </p>
            <div v-else-if="tenderFiles.length" class="space-y-2">
              <div
                v-for="f in tenderFiles"
                :key="f.id"
                class="flex items-center justify-between gap-3 rounded border border-gray-200 p-2"
              >
                <a
                  :href="f.file_url || '#'"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-primary-600 hover:underline truncate"
                >
                  {{ f.name || `Файл #${f.id}` }}
                </a>
                <span class="text-xs text-gray-500 shrink-0">
                  {{ formatFileDate(f.uploaded_at) }}
                </span>
              </div>
            </div>
            <p v-else class="text-gray-500">Немає прикріплених файлів.</p>
          </UCard>
        </template>
      </UModal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getApiErrorMessage } from "~/shared/api/error";
import {
  criterionInputKind,
  extractFilesArray,
  fileModelKey,
  formatDecimalValue,
  formatCriterionValue,
  formatPriceValue,
  normalizeCriterionValueForSave,
  normalizeCriterionValueForUi,
  toValidNumber,
  type CriterionValue,
} from "~/domains/tenders/tenderProposal.utils";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Пропозиції — продаж" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));

const tender = ref<any | null>(null);
const loading = ref(true);
const proposals = ref<any[]>([]);
const currentProposal = ref<any | null>(null);
const positionRows = ref<any[]>([]);
const showCheckModal = ref(false);
const showFilesModal = ref(false);
const showParticipantChatModal = ref(false);
const tenderFiles = ref<any[]>([]);
const tenderFilesLoading = ref(false);
const tenderFilesError = ref("");
const savingPositions = ref(false);
const submitWithdrawLoading = ref(false);
const submittingPositionId = ref<number | null>(null);
const chatMessages = ref<any[]>([]);
const chatDraft = ref("");
const chatSending = ref(false);
let chatPollInterval: ReturnType<typeof setInterval> | null = null;
const now = ref(new Date());
let nowInterval: ReturnType<typeof setInterval> | null = null;

const isSales = true;
const tendersUC = useTendersUseCases();
const { me } = useMe();
const myCompanyId = computed(
  () => (me.value as any)?.memberships?.[0]?.company?.id ?? null,
);
const isParticipant = computed(
  () =>
    tender.value &&
    myCompanyId.value != null &&
    Number(tender.value.company) !== myCompanyId.value,
);
const {
  selectedSupplierId,
  selectedSupplier,
  showSupplierModal,
  supplierSearch,
  filteredSuppliers,
  loadSuppliers,
  selectSupplier,
  initSelectedSupplierFromProposals,
} = useTenderProposalPage({
  onSupplierSelect,
});

const vatLabels: Record<string, string> = {
  with_vat: "з ПДВ",
  without_vat: "без ПДВ",
};
const deliveryLabels: Record<string, string> = {
  with_delivery: "із урахуванням доставки",
  without_delivery: "без урахування доставки",
};

function parseVatPercentValue(value: unknown): number | null {
  const raw = String(value ?? "")
    .trim()
    .replace(",", ".");
  if (!raw) return null;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return null;
  if (parsed <= 0 || parsed > 100) return null;
  return Math.round(parsed * 100) / 100;
}

const tenderCriteria = computed(() => tender.value?.criteria ?? []);
const tenderCriteriaIndividual = computed(() =>
  tenderCriteria.value.filter(
    (c: any) => (c.application || "individual") === "individual",
  ),
);
const tenderCriteriaGeneral = computed(() =>
  tenderCriteria.value.filter(
    (c: any) => (c.application || "individual") === "general",
  ),
);
const booleanCriterionOptions = [
  { value: true, label: "Так" },
  { value: false, label: "Ні" },
];
const fileCriterionModels = ref<Record<string, File[]>>({});
const generalCriterionValues = ref<Record<number, CriterionValue>>({});

const tenderPositions = computed(() => tender.value?.positions ?? []);
const isOnlineAuction = computed(
  () => tender.value?.conduct_type === "online_auction",
);
const MAX_INCREMENTAL_REALTIME_PROPOSAL_SYNC = 6;
const proposalsRealtime = useTenderProposalsRealtime({
  tenderId,
  isSales,
  tenderStage: computed(() => tender.value?.stage ?? null),
  isOnlineAuction,
  isParticipant,
  reload: reloadRealtimeProposals,
});

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

const visibleStageItems = computed(() => {
  const isRegistration = tender.value?.conduct_type === "registration";
  if (isRegistration) return stageItems.filter((s) => s.value !== "acceptance");
  return stageItems;
});

const currentStage = computed(() => tender.value?.stage ?? "passport");

const isViewingPreviousTour = computed(
  () => tender.value && tender.value.is_latest_tour === false,
);
const showAcceptanceTimingInfo = computed(() => currentStage.value === "acceptance");

const acceptanceStartAt = computed(() => {
  const t = tender.value?.start_at;
  if (!t) return null;
  const timestamp = new Date(t).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
});
const acceptanceEndAt = computed(() => {
  const t = tender.value?.end_at;
  if (!t) return null;
  const timestamp = new Date(t).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
});
function formatTimerDuration(ms: number) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${days} дн / ${pad(hours)} год / ${pad(minutes)} хв / ${pad(seconds)} с`;
}
const timerText = computed(() => {
  const n = now.value.getTime();
  const start = acceptanceStartAt.value;
  const end = acceptanceEndAt.value;
  if (start != null && n < start) {
    return `До початку: ${formatTimerDuration(start - n)}`;
  }
  if (end != null && n > end) return "Прийом пропозицій завершено";
  if (end != null && n <= end) {
    return `До завершення: ${formatTimerDuration(end - n)}`;
  }
  return "Час прийому не задано";
});
const participantCanManageProposal = computed(() => {
  if (!tender.value || tender.value.stage !== "acceptance") return false;
  const n = now.value.getTime();
  const start = acceptanceStartAt.value;
  const end = acceptanceEndAt.value;
  if (start != null && n < start) return false;
  if (end != null && n > end) return false;
  return true;
});
const myProposal = computed(() =>
  proposals.value.find(
    (p: any) =>
      p.supplier_company_id === myCompanyId.value ||
      p.supplier_company?.id === myCompanyId.value,
  ),
);
const isProposalSubmitted = computed(() => {
  const proposal = myProposal.value as Record<string, unknown> | undefined;
  if (!proposal) return false;
  const status = String(proposal.status ?? "").toLowerCase();
  if (proposal.withdrawn_at) return false;
  if (status === "withdrawn" || status === "retracted") return false;
  return !!proposal.submitted_at;
});
const participantCanWithdraw = computed(
  () => participantCanManageProposal.value && isProposalSubmitted.value,
);
const participantCanEdit = computed(
  () => participantCanManageProposal.value && !isProposalSubmitted.value,
);

const stepperItems = computed(() => {
  const stage = currentStage.value;
  const order = visibleStageItems.value.map((s) => s.value);
  const progressIndex = order.indexOf(stage);
  return visibleStageItems.value.map((s, index) => ({
    ...s,
    description: "",
    class: [
      index < progressIndex ? "tender-step-done" : "",
      index === progressIndex ? "tender-step-progress-current" : "",
    ]
      .filter(Boolean)
      .join(" "),
  }));
});

const priceColumnHeader = computed(() => {
  const v = tender.value?.price_criterion_vat;
  const d = tender.value?.price_criterion_delivery;
  const vPercent = parseVatPercentValue(tender.value?.price_criterion_vat_percent);
  const vLabel = v && vatLabels[v] ? vatLabels[v] : v || "";
  const vPercentLabel =
    v === "with_vat" && vPercent != null ? `${vPercent}%` : "";
  const dLabel = d && deliveryLabels[d] ? deliveryLabels[d] : d || "";
  const parts = ["Ціна", vLabel, dLabel].filter(Boolean);
  if (vPercentLabel) parts.splice(Math.max(parts.length - 1, 1), 0, vPercentLabel);
  return parts.join(" ");
});

function getGeneralCriterionFileModel(criterionId: number) {
  return fileCriterionModels.value[fileModelKey("g", criterionId)] || [];
}

function getPositionCriterionFileModel(
  positionId: number,
  criterionId: number,
) {
  return fileCriterionModels.value[fileModelKey(positionId, criterionId)] || [];
}


async function onGeneralCriterionFileChange(
  criterionId: number,
  value: unknown,
) {
  const files = extractFilesArray(value);
  fileCriterionModels.value[fileModelKey("g", criterionId)] = files;
  generalCriterionValues.value[criterionId] = files.map((f) => f.name);
  await savePositionValues();
}

async function onPositionCriterionFileChange(
  positionId: number,
  criterionId: number,
  value: unknown,
) {
  const files = extractFilesArray(value);
  fileCriterionModels.value[fileModelKey(positionId, criterionId)] = files;
  const row = positionRows.value.find((r: any) => r.id === positionId);
  if (row) row.criterion_values[criterionId] = files.map((f) => f.name);
  await savePositionValues();
}

function getProposalPositionValue(proposal: any, positionId: number) {
  const list = proposal?.position_values || [];
  return list.find(
    (pv: any) =>
      (pv.tender_position_id ??
        pv.tender_position?.id ??
        pv.tender_position) === positionId,
  );
}

function getProposalCriterionValue(
  proposal: any,
  positionId: number,
  criterionId: number,
) {
  const pv = getProposalPositionValue(proposal, positionId);
  const cv = pv?.criterion_values;
  if (!cv || typeof cv !== "object") return null;
  const v = cv[criterionId] ?? cv[String(criterionId)];
  return v != null && v !== "" ? v : null;
}

function getProposalPositionSum(
  proposal: any,
  pos: { id: number; quantity: number },
) {
  const pv = getProposalPositionValue(proposal, pos.id);
  const price = pv?.price;
  if (price == null || price === "") return null;
  const num = Number(price);
  if (Number.isNaN(num)) return null;
  const qty = Number(pos.quantity) || 0;
  return formatDecimalValue(qty * num, 4);
}

function formatNumericDisplay(value: unknown): string {
  const parsed = toValidNumber(value);
  if (parsed == null) return String(value ?? "");
  return formatDecimalValue(parsed, 4);
}

/** Продаж: краща = більша ціна, гірша = менша ціна */
function getBestWorstForPosition(positionId: number) {
  const withPrice: { id: number; price: number }[] = [];
  for (const p of proposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const num = Number(pv?.price);
    if (!Number.isNaN(num)) withPrice.push({ id: p.id, price: num });
  }
  if (withPrice.length === 0) return { bestId: null, worstId: null };
  const best = withPrice.reduce((a, b) => (a.price >= b.price ? a : b));
  const worst = withPrice.reduce((a, b) => (a.price <= b.price ? a : b));
  return { bestId: best.id, worstId: worst.id };
}


function getCurrentBestPriceForPosition(positionId: number): number | null {
  const prices: number[] = [];
  for (const p of proposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const price = toValidNumber(pv?.price);
    if (price != null) prices.push(price);
  }
  if (!prices.length) return null;
  return isSales ? Math.max(...prices) : Math.min(...prices);
}

function getRangeValues(
  positionId: number,
): { from: number; to: number } | null {
  if (!isOnlineAuction.value) return null;
  const pos = (tender.value?.positions || []).find(
    (p: any) => p.id === positionId,
  );
  if (!pos) return null;

  const startPrice = toValidNumber(pos.start_price);
  const minStep = toValidNumber(pos.min_bid_step);
  const maxStep = toValidNumber(pos.max_bid_step);
  if (startPrice == null || minStep == null || maxStep == null) return null;

  const best = getCurrentBestPriceForPosition(positionId);
  if (best == null) {
    const end = isSales ? startPrice + maxStep : startPrice - maxStep;
    return { from: startPrice, to: end };
  }

  const first = isSales ? best + minStep : best - minStep;
  const second = isSales ? first + maxStep : first - maxStep;
  return { from: first, to: second };
}

function getRangeDisplay(positionId: number): string | null {
  const range = getRangeValues(positionId);
  if (!range) return null;
  return `${formatPriceValue(range.from)} - ${formatPriceValue(range.to)}`;
}

function applyRangeValue(positionId: number, value: number | null) {
  if (value == null) return;
  const row = positionRows.value.find((r: any) => r.id === positionId);
  if (!row) return;
  row.next_price = String(value);
}

async function submitPositionPrice(positionId: number) {
  const proposalId = currentProposal.value?.id;
  const row = positionRows.value.find((r: any) => r.id === positionId);
  if (!proposalId || !row) return;

  const nextPrice = toValidNumber(row.next_price);
  if (nextPrice == null) {
    alert("Не вірне значення ціни.");
    return;
  }

  const range = getRangeValues(positionId);
  if (range) {
    const minValue = Math.min(range.from, range.to);
    const maxValue = Math.max(range.from, range.to);
    if (nextPrice < minValue || nextPrice > maxValue) {
      alert(`Значення поза діапазоном: ${getRangeDisplay(positionId)}.`);
      return;
    }
  }

  submittingPositionId.value = positionId;
  try {
    const cv = row.criterion_values || {};
    const criterion_values: Record<
      string,
      string | number | boolean | string[]
    > = {};
    for (const c of tenderCriteria.value) {
      const source =
        (c.application || "individual") === "general"
          ? generalCriterionValues.value[c.id]
          : cv[c.id];
      const normalized = normalizeCriterionValueForSave(c, source);
      if (normalized !== null) criterion_values[String(c.id)] = normalized;
    }

    const { data, error } = await tendersUC.patchProposalPositionValues(
      tenderId.value,
      proposalId,
      isSales,
      {
        position_values: [
          {
            tender_position_id: positionId,
            price: nextPrice,
            criterion_values,
          },
        ],
      },
      { skipLoader: true },
    );

    if (error) {
      alert(getApiErrorMessage(error));
      return;
    }
    if (data) {
      currentProposal.value = data;
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) {
        proposals.value = proposals.value.map((p: any, i: number) =>
          i === idx ? data : p,
        );
      }
      buildPositionRows(data);
      await loadProposals(true);
      row.next_price = "";
      await nextTick();
    }
  } finally {
    submittingPositionId.value = null;
  }
}

const checkComparisonByPosition = computed(() => {
  const out: Record<number, { bestId: number | null; worstId: number | null }> =
    {};
  for (const pos of tenderPositions.value) {
    out[pos.id] = getBestWorstForPosition(pos.id);
  }
  return out;
});

const canGoToDecision = computed(() => {
  return proposals.value.some(
    (p: any) =>
      p.position_values &&
      p.position_values.length > 0 &&
      p.position_values.some((pv: any) => pv.price != null),
  );
});

async function loadTender() {
  const { data } = await tendersUC.getTenderParticipantView(tenderId.value, isSales);
  if (data) {
    tender.value = data;
    buildPositionRowsFromTender();
  }
}

async function loadProposals(skipLoader = false) {
  const { data } = await tendersUC.getTenderProposals(tenderId.value, isSales, {
    skipLoader,
  });
  if (data) proposals.value = Array.isArray(data) ? data : [];
}

async function reloadRealtimeProposals(changedProposalIds: number[]) {
  const normalizedIds = Array.from(
    new Set(
      (changedProposalIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0),
    ),
  );

  if (
    !normalizedIds.length ||
    normalizedIds.length > MAX_INCREMENTAL_REALTIME_PROPOSAL_SYNC
  ) {
    await loadProposals(true);
    refreshCurrentProposalViewFromList();
    return;
  }

  const { data: changedProposals, error: changedProposalsError } =
    await tendersUC.getTenderProposals(tenderId.value, isSales, {
      skipLoader: true,
      proposalIds: normalizedIds,
    });
  if (changedProposalsError || !Array.isArray(changedProposals)) {
    await loadProposals(true);
    refreshCurrentProposalViewFromList();
    return;
  }

  const updatedById = new Map<number, any>();
  for (const proposal of changedProposals) {
    const proposalId = Number(proposal?.id);
    if (!Number.isInteger(proposalId) || proposalId <= 0) continue;
    updatedById.set(proposalId, proposal);
  }

  const hasMissingIds = normalizedIds.some((proposalId) => !updatedById.has(proposalId));
  if (!updatedById.size || hasMissingIds) {
    await loadProposals(true);
    refreshCurrentProposalViewFromList();
    return;
  }

  const existing = proposals.value;
  const existingIds = new Set(existing.map((proposal: any) => Number(proposal.id)));
  const next = existing.map(
    (proposal: any) => updatedById.get(Number(proposal.id)) || proposal,
  );
  for (const [proposalId, proposal] of updatedById.entries()) {
    if (!existingIds.has(proposalId)) next.push(proposal);
  }
  proposals.value = next;
  refreshCurrentProposalViewFromList();
}

function refreshCurrentProposalViewFromList() {
  const nextPriceDrafts = new Map<number, unknown>(
    positionRows.value.map((row: any) => [Number(row.id), row.next_price]),
  );

  const restoreNextPriceDrafts = () => {
    if (!nextPriceDrafts.size) return;
    for (const row of positionRows.value) {
      const draft = nextPriceDrafts.get(Number(row.id));
      if (draft !== undefined && draft !== null && String(draft) !== "") {
        row.next_price = draft;
      }
    }
  };

  if (isParticipant.value) {
    if (myProposal.value) {
      currentProposal.value = myProposal.value;
      buildPositionRows(myProposal.value);
      restoreNextPriceDrafts();
    }
    return;
  }

  const supplierId = selectedSupplierId.value;
  if (!supplierId) return;
  const proposal = proposals.value.find(
    (p: any) =>
      p.supplier_company_id === supplierId ||
      p.supplier_company?.id === supplierId,
  );
  if (!proposal) return;
  currentProposal.value = proposal;
  buildPositionRows(proposal);
  restoreNextPriceDrafts();
}

function stopProposalsRefresh() {
  proposalsRealtime.stop();
}

function startProposalsRefresh() {
  proposalsRealtime.start();
}

async function loadTenderFiles() {
  tenderFilesLoading.value = true;
  tenderFilesError.value = "";
  try {
    const { data, error } = await tendersUC.getTenderFiles(
      tenderId.value,
      isSales,
    );
    if (error) {
      tenderFilesError.value = error;
      tenderFiles.value = [];
      return;
    }
    tenderFiles.value = Array.isArray(data) ? data : [];
  } finally {
    tenderFilesLoading.value = false;
  }
}

function formatFileDate(value?: string) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString("uk-UA");
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString("uk-UA");
}

function stopChatPolling() {
  if (chatPollInterval) {
    clearInterval(chatPollInterval);
    chatPollInterval = null;
  }
}

function startChatPolling() {
  stopChatPolling();
  if (!showParticipantChatModal.value) return;
  chatPollInterval = setInterval(() => {
    void loadChatMessages(false);
  }, 15000);
}

async function loadChatMessages(clearDraft = false) {
  const { data } = await tendersUC.getTenderChatMessages(
    tenderId.value,
    isSales,
    myCompanyId.value ?? undefined,
  );
  chatMessages.value = Array.isArray(data) ? data : [];
  if (clearDraft) chatDraft.value = "";
}

async function openParticipantChatModal() {
  showParticipantChatModal.value = true;
  await loadChatMessages(true);
  startChatPolling();
}

function closeParticipantChatModal() {
  showParticipantChatModal.value = false;
  chatDraft.value = "";
  stopChatPolling();
}

async function submitParticipantChatMessage() {
  const body = chatDraft.value.trim();
  if (!body) return;
  chatSending.value = true;
  try {
    const { error } = await tendersUC.sendTenderChatMessage(tenderId.value, isSales, {
      body,
      supplier_company_id: myCompanyId.value ?? undefined,
    });
    if (error) {
      alert(getApiErrorMessage(error));
      return;
    }
    await loadChatMessages(true);
  } finally {
    chatSending.value = false;
  }
}

async function onSupplierSelect(id: number | null) {
  if (!id) {
    currentProposal.value = null;
    buildPositionRowsFromTender();
    return;
  }
  const proposal = proposals.value.find(
    (p: any) => p.supplier_company_id === id || p.supplier_company?.id === id,
  );
  if (!proposal) {
    await addProposal(id);
    return;
  }
  currentProposal.value = proposal;
  buildPositionRows(proposal);
}

async function addProposal(supplierCompanyId: number) {
  const { data } = await tendersUC.addProposal(tenderId.value, isSales, {
    supplier_company_id: supplierCompanyId,
  });
  if (data) {
    proposals.value = [...proposals.value, data];
    currentProposal.value = data;
    buildPositionRows(data);
  }
}

function buildPositionRowsFromTender() {
  const positions = tender.value?.positions || [];
  const criteria = tender.value?.criteria || [];
  const generalIds = (tender.value?.criteria || [])
    .filter((c: any) => (c.application || "individual") === "general")
    .map((c: any) => c.id);
  fileCriterionModels.value = {};
  generalCriterionValues.value = generalIds.reduce(
    (acc: Record<number, CriterionValue>, id: number) => {
      acc[id] = "";
      return acc;
    },
    {},
  );
  positionRows.value = positions.map((pos: any) => {
    const criterion_values: Record<number, CriterionValue | ""> = {};
    for (const c of criteria) {
      criterion_values[c.id] = normalizeCriterionValueForUi(c, "");
    }
    return {
      id: pos.id,
      name: pos.name,
      quantity: pos.quantity,
      unit_name: pos.unit_name ?? "",
      description: pos.description ?? "",
      price: "",
      next_price: "",
      criterion_values,
    };
  });
}

function buildPositionRows(proposal: any) {
  const positions = tender.value?.positions || [];
  const valuesByPos = (proposal.position_values || []).reduce(
    (acc: any, pv: any) => {
      const posId =
        pv.tender_position_id ?? pv.tender_position?.id ?? pv.tender_position;
      acc[posId] = pv;
      return acc;
    },
    {},
  );
  const criteria = tender.value?.criteria || [];
  const generalCriteria = criteria.filter(
    (c: any) => (c.application || "individual") === "general",
  );
  fileCriterionModels.value = {};
  const newRows = positions.map((pos: any) => {
    const pv = valuesByPos[pos.id];
    const criterion_values: Record<number, CriterionValue | ""> = {};
    if (pv?.criterion_values && typeof pv.criterion_values === "object") {
      for (const [k, v] of Object.entries(pv.criterion_values)) {
        const criterionMeta = criteria.find((c: any) => c.id === Number(k));
        criterion_values[Number(k)] = normalizeCriterionValueForUi(
          criterionMeta,
          v,
        );
      }
    }
    for (const c of criteria) {
      if (criterion_values[c.id] === undefined)
        criterion_values[c.id] = normalizeCriterionValueForUi(c, "");
    }
    return {
      id: pos.id,
      name: pos.name,
      quantity: pos.quantity,
      unit_name: pos.unit_name ?? "",
      description: pos.description ?? "",
      price: pv?.price != null ? String(pv.price) : "",
      next_price: "",
      criterion_values,
    };
  });
  positionRows.value = [...newRows];
  for (const c of generalCriteria) {
    const firstVal = newRows[0]?.criterion_values?.[c.id];
    if (firstVal !== undefined)
      generalCriterionValues.value[c.id] = normalizeCriterionValueForUi(
        c,
        firstVal,
      );
  }
}

async function savePositionValues() {
  if (!currentProposal.value?.id || !positionRows.value.length) return;
  savingPositions.value = true;
  const generalVals = generalCriterionValues.value;
  try {
    const position_values = positionRows.value.map((row) => {
      const cv = row.criterion_values || {};
      const criterion_values: Record<
        string,
        string | number | boolean | string[]
      > = {};
      for (const c of tenderCriteria.value) {
        const val =
          (c.application || "individual") === "general"
            ? generalVals[c.id]
            : cv[c.id];
        const normalized = normalizeCriterionValueForSave(c, val);
        if (normalized !== null) criterion_values[String(c.id)] = normalized;
      }
      return {
        tender_position_id: row.id,
        price: row.price !== "" ? parseFloat(String(row.price)) : null,
        criterion_values,
      };
    });
    const { data } = await tendersUC.patchProposalPositionValues(
      tenderId.value,
      currentProposal.value.id,
      isSales,
      { position_values },
    );
    if (data) {
      currentProposal.value = data;
      buildPositionRows(data);
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) {
        proposals.value = proposals.value.map((p: any, i: number) =>
          i === idx ? data : p,
        );
      }
      await nextTick();
    }
  } finally {
    savingPositions.value = false;
  }
}

async function onSubmitProposal() {
  submitWithdrawLoading.value = true;
  try {
    const { data } = await tendersUC.submitProposal(tenderId.value, isSales);
    if (data) {
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) proposals.value[idx] = data;
      if (currentProposal.value?.id === data.id) {
        currentProposal.value = data;
      }
    }
  } finally {
    submitWithdrawLoading.value = false;
  }
}

async function onWithdrawProposal() {
  submitWithdrawLoading.value = true;
  try {
    const { data } = await tendersUC.withdrawProposal(tenderId.value, isSales);
    if (data) {
      const idx = proposals.value.findIndex((p: any) => p.id === data.id);
      if (idx !== -1) proposals.value[idx] = data;
      if (currentProposal.value?.id === data.id) {
        currentProposal.value = data;
      }
    }
  } finally {
    submitWithdrawLoading.value = false;
  }
}

function goBack() {
  navigateTo(
    isParticipant.value
      ? "/cabinet/participation?type=sales"
      : `/cabinet/tenders/sales/${tenderId.value}`,
  );
}

function onStageClick(_stageValue: string) {
  navigateTo(
    isParticipant.value
      ? "/cabinet/participation?type=sales"
      : `/cabinet/tenders/sales/${tenderId.value}`,
  );
}

onMounted(async () => {
  loading.value = true;
  try {
    await loadTender();
    await loadProposals(true);
    const part =
      tender.value &&
      myCompanyId.value != null &&
      Number(tender.value.company) !== myCompanyId.value;
    if (!part) await loadSuppliers();
    if (part && myProposal.value) {
      currentProposal.value = myProposal.value;
      buildPositionRows(myProposal.value);
    } else if (proposals.value.length > 0 && !selectedSupplierId.value) {
      await initSelectedSupplierFromProposals(proposals.value);
    }
    nowInterval = setInterval(() => {
      now.value = new Date();
    }, 1000);
    startProposalsRefresh();
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  if (nowInterval) clearInterval(nowInterval);
  stopChatPolling();
  stopProposalsRefresh();
});

watch(
  () => tender.value?.stage,
  () => {
    startProposalsRefresh();
  },
);

watch(showFilesModal, async (open) => {
  if (!open) return;
  await loadTenderFiles();
});

watch(showParticipantChatModal, (open) => {
  if (open) {
    startChatPolling();
    return;
  }
  stopChatPolling();
});
</script>

