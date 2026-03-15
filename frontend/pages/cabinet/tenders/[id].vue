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
  <div v-else class="h-full min-h-0 flex flex-col border-0 ring-0 outline-none">
    <div class="mb-4 flex items-center justify-between gap-4">
      <h1
        v-if="tender.number"
        class="text-xl font-semibold text-gray-900 truncate min-w-0"
      >
        № {{ tender.number }}
        <span class="font-normal text-gray-700">{{ tender.name }}</span>
      </h1>
      <div class="flex items-center gap-2 shrink-0">
        <UButton
          variant="outline"
          icon="i-heroicons-document-text"
          @click="openProtocolModal"
        >
          Протокол
        </UButton>
        <div v-if="tourOptions.length" class="flex items-center gap-2 shrink-0">
          <span class="text-sm text-gray-600">Тур:</span>
          <USelect
            :model-value="tenderId"
            :items="tourOptions"
            value-key="value"
            class="min-w-[120px]"
            @update:model-value="onTourSelect"
          />
        </div>
      </div>
    </div>
    <div
      v-if="!isParticipant"
      class="tender-stepper tender-stepper--compact mb-1"
    >
      <UStepper
        v-model="currentStepValue"
        :items="stepperItems"
        value-key="value"
        :linear="false"
        size="sm"
      />
    </div>

    <UAlert
      v-if="isViewingPreviousTourOnly"
      color="neutral"
      variant="subtle"
      icon="i-heroicons-eye"
      title="Перегляд попереднього туру"
      description="Ви переглядаєте збережені дані попереднього туру. Редагування та зміна етапів недоступні — кожен тур зберігається окремо."
      class="mb-4"
    />

    <div class="flex flex-1 min-h-0 gap-6 border-0 ring-0">
      <div
        class="flex-1 min-w-0 min-h-0 border-0 ring-0 flex flex-col overflow-y-auto"
      >
        <template v-if="displayStage === 'passport'">
          <UCard class="flex-1 min-h-full">
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">
                Паспорт тендера
              </h3>
            </template>
            <UForm :state="form" class="space-y-6">
              <div
                class="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6 lg:gap-8"
              >
                <div class="space-y-6">
                  <UFormField
                    label="Назва тендера"
                    required
                    class="mb-0 w-full"
                  >
                    <UInput
                      v-model="form.name"
                      placeholder="Введіть назву тендера"
                      size="md"
                      class="w-full"
                      :disabled="isViewingPreviousTour"
                    />
                  </UFormField>

                  <div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <ContentSearch
                        label="Категорія"
                        placeholder="Оберіть категорію"
                        search-placeholder="Пошук категорії"
                        :disabled="isViewingPreviousTour"
                        :tree="categoryTree"
                        :selected-ids="selectedCategoryIds"
                        :search-term="categorySearch"
                        :disabled-ids="categoryDisabledIds"
                        @toggle="toggleCategory"
                        @update:search-term="categorySearch = $event"
                      />
                      <CpvTenderModalSelect
                        label="Категорія CPV"
                        placeholder="Оберіть CPV"
                        required
                        :disabled="isViewingPreviousTour"
                        :selected-ids="form.cpv_ids"
                        :selected-labels="tenderCpvLabels"
                        @update:selected-ids="form.cpv_ids = $event"
                        @update:selected-labels="tenderCpvLabels = $event"
                      />
                    </div>
                  </div>

                  <div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <ContentSearch
                        label="Стаття бюджету"
                        placeholder="Оберіть статтю"
                        search-placeholder="Пошук статті бюджету"
                        :disabled="isViewingPreviousTour"
                        :tree="expenseTree"
                        :selected-ids="selectedExpenseIds"
                        :search-term="expenseSearch"
                        :disabled-ids="expenseDisabledIds"
                        @toggle="toggleExpense"
                        @update:search-term="expenseSearch = $event"
                      />
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <UFormField label="Орієнтовний бюджет">
                          <UInput
                            v-model.number="form.estimated_budget"
                            type="number"
                            step="0.0001"
                            placeholder="0"
                            size="sm"
                            class="w-full"
                            :disabled="isViewingPreviousTour"
                          />
                        </UFormField>
                        <UFormField label="Валюта" required>
                          <USelectMenu
                            v-model="form.currency"
                            :items="currencyOptions"
                            value-key="value"
                            placeholder="Валюту"
                            size="sm"
                            class="w-full"
                            :disabled="isViewingPreviousTour"
                          />
                        </UFormField>
                      </div>
                    </div>
                  </div>

                  <div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <ContentSearch
                        label="Філіал"
                        placeholder="Оберіть філіал"
                        search-placeholder="Пошук філіалу"
                        :disabled="isViewingPreviousTour"
                        :tree="branchTree"
                        :selected-ids="selectedBranchIds"
                        :search-term="branchSearch"
                        :disabled-ids="branchDisabledIds"
                        @toggle="toggleBranch"
                        @update:search-term="branchSearch = $event"
                      />
                      <ContentSearch
                        label="Підрозділ"
                        placeholder="Оберіть підрозділ"
                        search-placeholder="Пошук підрозділу"
                        :disabled="isViewingPreviousTour"
                        :tree="departmentTree"
                        :selected-ids="selectedDepartmentIds"
                        :search-term="departmentSearch"
                        :disabled-ids="departmentDisabledIds"
                        @toggle="toggleDepartment"
                        @update:search-term="departmentSearch = $event"
                      />
                    </div>
                  </div>

                  <div>
                    <div class="grid grid-cols-2 md:grid-cols-2 gap-4">
                      <UFormField label="Тип проведення" required>
                        <USelectMenu
                          v-model="form.conduct_type"
                          :items="conductTypeOptions"
                          value-key="value"
                          placeholder="Оберіть тип"
                          size="sm"
                          class="w-full"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                      <UFormField label="Тип публікації" required>
                        <USelectMenu
                          v-model="form.publication_type"
                          :items="publicationTypeOptions"
                          value-key="value"
                          placeholder="Оберіть тип"
                          size="sm"
                          class="w-full"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                      <div class="grid grid-cols-1 md:grid-cols-1 gap-4">
                        <UFormField
                          label="Модель погодження"
                          :required="isApprovalModelRequired"
                        >
                          <USelectMenu
                            v-model="form.approval_model_id"
                            :items="approvalModelOptions"
                            value-key="value"
                            placeholder="Оберіть модель"
                            size="sm"
                            class="w-full"
                            :disabled="
                              isViewingPreviousTour ||
                              !isApprovalModelLookupReady
                            "
                          />
                        </UFormField>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  class="border-t border-gray-200 pt-5 lg:border-t-0 lg:border-l lg:border-gray-200 lg:pt-0 lg:pl-6 flex flex-col min-h-[320px]"
                >
                  <div class="mb-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <UFormField label="Орієнтовна дата прийому пропозицій">
                        <div class="grid grid-cols-[1fr_auto] gap-2">
                          <DateValuePicker
                            :model-value="plannedStartDate"
                            :disabled="isViewingPreviousTour"
                            @update:model-value="
                              plannedStartDate = $event || ''
                            "
                          />
                          <UInput
                            v-model="plannedStartTime"
                            placeholder="ГГ:ХХ"
                            inputmode="numeric"
                            maxlength="5"
                            class="w-24"
                            :disabled="isViewingPreviousTour"
                            @update:model-value="
                              plannedStartTime = formatTimeInput($event)
                            "
                          />
                        </div>
                      </UFormField>
                      <UFormField label="Орієнтовна дата та час завершення">
                        <div class="grid grid-cols-[1fr_auto] gap-2">
                          <DateValuePicker
                            :model-value="plannedEndDate"
                            :disabled="isViewingPreviousTour"
                            @update:model-value="plannedEndDate = $event || ''"
                          />
                          <UInput
                            v-model="plannedEndTime"
                            placeholder="ГГ:ХХ"
                            inputmode="numeric"
                            maxlength="5"
                            class="w-24"
                            :disabled="isViewingPreviousTour"
                            @update:model-value="
                              plannedEndTime = formatTimeInput($event)
                            "
                          />
                        </div>
                      </UFormField>
                    </div>
                  </div>
                  <UFormField
                    label="Опис умов та вимог"
                    class="mb-0 flex-1 flex flex-col min-h-0"
                  >
                    <div class="mb-2">
                      <UButton
                        size="sm"
                        variant="outline"
                        icon="i-heroicons-document-text"
                        :disabled="isViewingPreviousTour"
                        @click="openConditionTemplateModal"
                      >
                        Обрати шаблон
                      </UButton>
                    </div>
                    <div
                      class="general-terms-editor-wrapper flex flex-col min-h-[320px] rounded-md border border-gray-200 bg-white overflow-hidden"
                    >
                      <UEditor
                        v-slot="{ editor }"
                        v-model="form.general_terms"
                        content-type="html"
                        :extensions="[
                          TextAlign.configure({
                            types: ['heading', 'paragraph'],
                          }),
                        ]"
                        placeholder="Опишіть загальні умови, вимоги до учасників, порядок оцінки пропозицій тощо. Цей текст буде доступний учасникам."
                        :editable="!isViewingPreviousTour"
                        :ui="{
                          root: 'flex flex-col min-h-[300px]',
                          content: 'flex-1 min-h-[260px] flex flex-col',
                          base: 'min-h-[260px] outline-none py-2 px-3 cursor-text',
                        }"
                        class="w-full"
                      >
                        <UEditorToolbar
                          :editor="editor"
                          :items="generalTermsEditorToolbarItems"
                          class="border-b border-gray-200 px-2 py-1 flex-shrink-0"
                        />
                      </UEditor>
                    </div>
                  </UFormField>
                </div>
              </div>
            </UForm>
          </UCard>
        </template>

        <template v-else-if="displayStage === 'preparation'">
          <!-- Панель запрошення учасників: 2/3 ліворуч, 1/3 праворуч -->
          <div
            v-if="showInvitationPanel"
            class="h-full min-h-0 flex flex-col rounded-lg p-4 bg-white"
          >
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">Запрошення учасників</h3>
              <UButton
                variant="ghost"
                size="sm"
                icon="i-heroicons-arrow-left"
                @click="showInvitationPanel = false"
              >
                До підготовки
              </UButton>
            </div>
            <!-- Пропорції: 2/5 контрагенти, 2/5 CPV, 1/5 email -->
            <div class="flex flex-1 min-h-0 gap-4">
              <!-- Область 1 (2/5): Обрання контрагента — верх: два пошуки + список постачальників з пагінацією та Запросити, низ: запрошені -->
              <div
                class="flex-[2] min-w-0 flex flex-col border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden"
              >
                <h4
                  class="p-3 border-b border-gray-200 text-sm font-semibold text-gray-700"
                >
                  Обрання контрагента зі списку контрагентів компанії
                </h4>
                <div
                  class="flex-1 min-h-0 flex flex-col min-w-0 divide-y divide-gray-200"
                >
                  <!-- Верхня половина: пошуки + список постачальників -->
                  <div
                    class="flex-1 min-h-0 flex flex-col p-3 overflow-hidden min-h-[200px]"
                  >
                    <UFormField label="Пошук контрагента за назвою або кодом">
                      <UInput
                        v-model="invitationContractorSearch"
                        placeholder="Назва або ЄДРПОУ"
                        size="sm"
                        class="w-full"
                      />
                    </UFormField>
                    <UFormField
                      label="Фільтр постачальників по категорії CPV"
                      class="mt-2"
                    >
                      <USelectMenu
                        v-model="invitationSupplierCpvFilterIds"
                        :items="invitationCpvOptions"
                        value-key="id"
                        label-key="label"
                        placeholder="Усі категорії"
                        multiple
                        class="w-full"
                      />
                    </UFormField>
                    <div
                      class="flex-1 min-h-0 overflow-auto mt-3 border border-gray-200 rounded-lg bg-white"
                    >
                      <ul
                        v-if="invitationSupplierPageList.length"
                        class="divide-y divide-gray-100"
                      >
                        <li
                          v-for="rel in invitationSupplierPageList"
                          :key="rel.id"
                          class="flex items-center justify-between gap-2 px-3 py-2 hover:bg-gray-50"
                        >
                          <UCheckbox
                            :model-value="
                              selectedContractorCompanyIds.includes(
                                rel.supplier_company?.id ?? 0,
                              )
                            "
                            class="shrink-0"
                            @update:model-value="
                              toggleContractorSelection(
                                rel.supplier_company?.id,
                              )
                            "
                          />
                          <span class="flex-1 text-sm truncate">{{
                            rel.supplier_company?.name ||
                            rel.supplier_company?.edrpou ||
                            "—"
                          }}</span>
                          <span
                            v-if="rel.supplier_company?.edrpou"
                            class="text-xs text-gray-500 shrink-0"
                            >{{ rel.supplier_company.edrpou }}</span
                          >
                          <UButton
                            size="xs"
                            variant="outline"
                            @click="inviteOneContractor(rel)"
                          >
                            Запросити
                          </UButton>
                        </li>
                      </ul>
                      <p v-else class="text-sm text-gray-500 p-3">
                        Немає постачальників за критеріями пошуку.
                      </p>
                    </div>
                    <div
                      class="flex items-center justify-between gap-2 mt-2 flex-shrink-0"
                    >
                      <div class="flex items-center gap-2">
                        <UButton
                          size="xs"
                          variant="outline"
                          :disabled="invitationSupplierPage <= 1"
                          @click="
                            invitationSupplierPage = invitationSupplierPage - 1
                          "
                        >
                          Назад
                        </UButton>
                        <span class="text-sm text-gray-600">
                          {{ invitationSupplierPage }} /
                          {{ invitationSupplierTotalPages || 1 }}
                        </span>
                        <UButton
                          size="xs"
                          variant="outline"
                          :disabled="
                            invitationSupplierPage >=
                            invitationSupplierTotalPages
                          "
                          @click="
                            invitationSupplierPage = invitationSupplierPage + 1
                          "
                        >
                          Далі
                        </UButton>
                      </div>
                      <UButton
                        size="sm"
                        :disabled="selectedContractorCompanyIds.length === 0"
                        @click="inviteSelectedContractors"
                      >
                        Запросити
                      </UButton>
                    </div>
                  </div>
                  <!-- Нижня половина: запрошені компанії -->
                  <div
                    v-if="false"
                    class="flex-1 min-h-0 flex flex-col p-3 min-h-[120px]"
                  >
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">
                      Запрошені компанії
                    </h4>
                    <ul
                      v-if="invitedCompanies.length"
                      class="space-y-1.5 overflow-auto min-h-0 flex-1"
                    >
                      <li
                        v-for="(company, idx) in invitedCompanies"
                        :key="company.id"
                        class="flex items-center justify-between gap-2 py-1.5 px-2 rounded bg-white border border-gray-200 text-sm"
                      >
                        <span class="truncate flex-1 min-w-0">{{
                          company.name || company.edrpou || "—"
                        }}</span>
                        <UButton
                          icon="i-heroicons-trash"
                          size="xs"
                          variant="ghost"
                          color="error"
                          aria-label="Видалити"
                          @click="removeInvitedCompany(idx)"
                        />
                      </li>
                    </ul>
                    <p v-else class="text-sm text-gray-500 py-1">Порожньо.</p>
                  </div>
                </div>
              </div>

              <!-- Центральна область: запрошені компанії -->
              <div
                class="flex-1 min-w-0 flex flex-col border border-gray-200 rounded-lg bg-white p-4 overflow-hidden"
              >
                <h4 class="text-sm font-semibold text-gray-700 mb-2">
                  Запрошені компанії
                </h4>
                <ul
                  v-if="invitedCompanies.length"
                  class="space-y-1.5 overflow-auto min-h-0 flex-1"
                >
                  <li
                    v-for="(company, idx) in invitedCompanies"
                    :key="company.id"
                    class="flex items-center justify-between gap-2 py-1.5 px-2 rounded bg-gray-50 border border-gray-200 text-sm"
                  >
                    <span class="truncate flex-1 min-w-0">{{
                      company.name || company.edrpou || "—"
                    }}</span>
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="error"
                      aria-label="Видалити"
                      @click="removeInvitedCompany(idx)"
                    />
                  </li>
                </ul>
                <p v-else class="text-sm text-gray-500 py-1">Порожньо.</p>
              </div>

              <!-- Область 2 (2/5): зверху пошук + список CPV (системні) з пагінацією та Запросити, знизу — категорії по яким запрошуються -->
              <div
                v-if="false"
                class="flex-[2] min-w-0 flex flex-col border border-gray-200 rounded-lg bg-white overflow-hidden divide-y divide-gray-200"
              >
                <h4
                  class="p-3 border-b border-gray-200 text-sm font-semibold text-gray-700"
                >
                  Пошук контрагентів по CPV
                </h4>
                <div class="flex-1 min-h-0 flex flex-col min-w-0">
                  <div
                    class="flex-1 min-h-0 flex flex-col p-3 overflow-hidden min-h-[200px]"
                  >
                    <UFormField label="Пошук категорії CPV">
                      <UInput
                        v-model="invitationCpvSearchTerm"
                        placeholder="Код або назва CPV"
                        size="sm"
                        class="w-full"
                      />
                    </UFormField>
                    <div
                      class="flex-1 min-h-0 overflow-auto mt-3 border border-gray-200 rounded-lg bg-gray-50"
                    >
                      <ul
                        v-if="cpvWithCompaniesPageList.length"
                        class="divide-y divide-gray-100"
                      >
                        <li
                          v-for="item in cpvWithCompaniesPageList"
                          :key="item.id"
                          class="flex items-center gap-2 px-3 py-2 hover:bg-white"
                        >
                          <UCheckbox
                            :model-value="
                              selectedCpvIdsForInvite.includes(item.id)
                            "
                            class="shrink-0"
                            @update:model-value="toggleCpvForInvite(item.id)"
                          />
                          <span class="flex-1 text-sm truncate">{{
                            item.label
                          }}</span>
                          <UButton
                            size="xs"
                            variant="outline"
                            @click="inviteOneCpv(item.id)"
                          >
                            Запросити
                          </UButton>
                        </li>
                      </ul>
                      <p
                        v-else-if="cpvWithCompaniesLoading"
                        class="text-sm text-gray-500 p-3"
                      >
                        Завантаження...
                      </p>
                      <p v-else class="text-sm text-gray-500 p-3">
                        Немає категорій за критеріями пошуку.
                      </p>
                    </div>
                    <div
                      class="flex items-center justify-between gap-2 mt-2 flex-shrink-0"
                    >
                      <div class="flex items-center gap-2">
                        <UButton
                          size="xs"
                          variant="outline"
                          :disabled="cpvWithCompaniesPage <= 1"
                          @click="
                            cpvWithCompaniesPage = cpvWithCompaniesPage - 1
                          "
                        >
                          Назад
                        </UButton>
                        <span class="text-sm text-gray-600">
                          {{ cpvWithCompaniesPage }} /
                          {{ cpvWithCompaniesTotalPages || 1 }}
                        </span>
                        <UButton
                          size="xs"
                          variant="outline"
                          :disabled="
                            cpvWithCompaniesPage >= cpvWithCompaniesTotalPages
                          "
                          @click="
                            cpvWithCompaniesPage = cpvWithCompaniesPage + 1
                          "
                        >
                          Далі
                        </UButton>
                      </div>
                      <UButton
                        size="sm"
                        :disabled="selectedCpvIdsForInvite.length === 0"
                        @click="inviteSelectedCpv"
                      >
                        Запросити
                      </UButton>
                    </div>
                  </div>
                  <div class="flex-1 min-h-0 flex flex-col p-3 min-h-[120px]">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">
                      Категорії CPV, за якими запрошуються учасники
                    </h4>
                    <ul
                      v-if="invitationCpvFilterIds.length"
                      class="space-y-1.5 overflow-auto min-h-0 flex-1"
                    >
                      <li
                        v-for="id in invitationCpvFilterIds"
                        :key="id"
                        class="flex items-center justify-between py-1.5 px-2 rounded bg-white border border-gray-200 text-sm"
                      >
                        <span class="truncate flex-1 min-w-0">{{
                          invitationCpvLabelById(id)
                        }}</span>
                        <UButton
                          icon="i-heroicons-trash"
                          size="xs"
                          variant="ghost"
                          color="error"
                          aria-label="Видалити"
                          @click="removeInvitedCpv(id)"
                        />
                      </li>
                    </ul>
                    <p v-else class="text-sm text-gray-500 py-1">
                      Оберіть категорії вище та натисніть Запросити.
                    </p>
                  </div>
                </div>
              </div>

              <!-- Область 3 (1/5): Запрошення по email -->
              <div
                class="flex-1 min-w-0 flex flex-col border border-gray-200 rounded-lg bg-white p-4 overflow-hidden"
              >
                <CpvTenderModalSelect
                  label=""
                  placeholder="Запросити по CPV"
                  :selected-ids="invitationCpvFilterIds"
                  :selected-labels="invitationCpvSelectedLabels"
                  @update:selected-ids="onInvitationCpvIdsUpdate"
                  @update:selected-labels="onInvitationCpvLabelsUpdate"
                />
                <UButton
                  class="w-full shrink-0 mt-2"
                  icon="i-heroicons-envelope"
                  @click="showInviteByEmailModal = true"
                >
                  Запрошення по email
                </UButton>
                <div class="mt-4 flex-1 min-h-0 overflow-auto">
                  <h4 class="text-sm font-semibold text-gray-700 mb-2">
                    Запрошені за email
                  </h4>
                  <ul v-if="invitedEmails.length" class="space-y-1.5">
                    <li
                      v-for="(email, idx) in invitedEmails"
                      :key="idx"
                      class="flex items-center justify-between py-2 px-3 rounded-md bg-gray-50 border border-gray-200 text-sm"
                    >
                      <span class="truncate">{{ email }}</span>
                      <UButton
                        icon="i-heroicons-trash"
                        size="xs"
                        variant="ghost"
                        color="error"
                        aria-label="Видалити"
                        @click="removeInvitedEmail(idx)"
                      />
                    </li>
                  </ul>
                  <p v-else class="text-sm text-gray-500 py-2">Порожньо.</p>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="h-full min-h-0 flex flex-col rounded-lg p-4 bg-white"
          >
            <h3 class="text-lg font-semibold mb-3">Підготовка процедури</h3>
            <UTabs
              v-model="prepTab"
              :items="prepTabs"
              value-key="value"
              class="mb-4 prep-tabs"
              content
            >
              <template #content="{ item }">
                <div
                  v-if="item.value === 'positions'"
                  class="h-full min-h-0 flex flex-col gap-4"
                >
                  <div class="rounded-lg p-4 bg-gray-50/50">
                    <div
                      :class="[
                        'grid grid-cols-1 gap-6',
                        isOnlineAuctionConductType
                          ? 'xl:grid-cols-2'
                          : 'xl:grid-cols-1',
                      ]"
                    >
                      <div>
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
                              :disabled="isViewingPreviousTour || isParticipant"
                              @update:model-value="onPriceCriterionVatChange"
                            />
                          </UFormField>
                          <UFormField
                            label="% ПДВ"
                            class="min-w-[180px]"
                            :required="isVatPercentRequired"
                          >
                            <UInput
                              v-model="priceCriterionVatPercent"
                              type="number"
                              min="0"
                              max="100"
                              step="0.0001"
                              placeholder="Напр. 20"
                              :disabled="
                                isViewingPreviousTour ||
                                isParticipant ||
                                !isVatPercentRequired
                              "
                              @blur="onPriceCriterionVatPercentBlur"
                            />
                          </UFormField>
                          <UFormField label="Доставка" class="min-w-[260px]">
                            <USelectMenu
                              v-model="priceCriterionDelivery"
                              :items="deliveryOptions"
                              value-key="value"
                              placeholder="Оберіть варіант"
                              :disabled="isViewingPreviousTour || isParticipant"
                              @update:model-value="
                                onPriceCriterionDeliveryChange
                              "
                            />
                          </UFormField>
                        </div>
                      </div>
                      <div v-if="isOnlineAuctionConductType">
                        <h4 class="text-sm font-semibold text-gray-700 mb-3">
                          Параметри онлайн торгів
                        </h4>
                        <UFormField
                          label="Модель проведення"
                          class="max-w-xs"
                          :required="isOnlineAuctionConductType"
                        >
                          <USelectMenu
                            v-model="form.auction_model"
                            :items="auctionModelOptions"
                            value-key="value"
                            placeholder="Оберіть модель"
                            :disabled="
                              isViewingPreviousTour ||
                              isParticipant ||
                              !isOnlineAuctionConductType
                            "
                          />
                        </UFormField>
                      </div>
                    </div>
                  </div>
                  <div
                    v-if="!isParticipant"
                    class="flex items-center justify-start gap-2 shrink-0"
                  >
                    <UButton
                      variant="outline"
                      size="sm"
                      icon="i-heroicons-plus"
                      :disabled="isViewingPreviousTour"
                      @click="showNomenclaturePickerModal = true"
                    >
                      Додати номенклатуру
                    </UButton>
                  </div>
                  <div class="flex-1 min-h-0 flex gap-4">
                    <!-- Ліва колонка: пошук + дерево категорії → номенклатури (тільки для власника) -->
                    <aside
                      v-if="false && !isParticipant"
                      class="w-72 flex-shrink-0 flex flex-col min-h-0 border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden"
                    >
                      <div class="p-2 border-b border-gray-200">
                        <UInput
                          v-model="nomenclatureSearch"
                          placeholder="Пошук номенклатури"
                          size="sm"
                          class="w-full"
                        />
                      </div>
                      <div class="flex-1 min-h-0 overflow-auto p-2">
                        <div
                          v-if="loadingNomenclatures"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Завантаження номенклатур...
                        </div>
                        <div
                          v-else-if="!nomenclatureTreeItems.length"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Оберіть категорію або CPV у паспорті тендера.
                        </div>
                        <UTree
                          v-else
                          :items="nomenclatureTreeItems"
                          size="sm"
                          :get-key="getNomenclatureTreeKey"
                          class="border-0"
                          @select="onNomenclatureTreeSelect"
                        />
                      </div>
                    </aside>

                    <!-- Таблиця позицій -->
                    <div class="flex-1 min-h-0 flex flex-col min-w-0">
                      <div
                        class="flex-1 min-h-0 overflow-auto positions-table-wrapper"
                      >
                        <UTable
                          :data="
                            isParticipant
                              ? displayTenderPositions
                              : tenderPositions
                          "
                          :columns="positionsTableColumns"
                          class="w-full positions-table"
                        >
                          <template #attributes_add-header>
                            <div class="flex justify-center">
                              <UButton
                                v-if="!isParticipant"
                                size="xs"
                                variant="soft"
                                color="primary"
                                class="rounded-full h-8 w-8 p-0 flex items-center justify-center"
                                icon="i-heroicons-plus"
                                title="Додати атрибут"
                                :disabled="isViewingPreviousTour"
                                @click="openAttributePickerModal"
                              >
                              </UButton>
                            </div>
                          </template>
                          <template #warehouse_add-header>
                            <div class="flex justify-center">
                              <UButton
                                v-if="!isParticipant && !usesPositionWarehouses"
                                size="xs"
                                variant="soft"
                                class="rounded-full h-8 w-8 p-0 flex items-center justify-center"
                                icon="i-heroicons-building-storefront"
                                title="Додати склади по позиціях"
                                :disabled="isViewingPreviousTour"
                                @click="enablePositionWarehouses()"
                              />
                            </div>
                          </template>
                          <template #warehouse-header>
                            <div class="flex items-center gap-1">
                              <span class="truncate">Місце постачання</span>
                              <UButton
                                v-if="!isParticipant"
                                size="xs"
                                color="error"
                                variant="ghost"
                                icon="i-heroicons-x-mark"
                                :disabled="isViewingPreviousTour"
                                @click.stop="disablePositionWarehouses()"
                              />
                            </div>
                          </template>
                          <template
                            v-for="attribute in tenderAttributes"
                            :key="`attr-header-${attribute.id}`"
                            #[`${attributeAccessorKey(attribute.id)}-header`]
                          >
                            <div class="flex items-center gap-1">
                              <span class="truncate">{{
                                attribute.name || "Атрибут"
                              }}</span>
                              <UButton
                                v-if="!isParticipant"
                                size="xs"
                                color="error"
                                variant="ghost"
                                icon="i-heroicons-x-mark"
                                :disabled="isViewingPreviousTour"
                                @click.stop="
                                  removeAttributeFromTender(attribute.id)
                                "
                              />
                            </div>
                          </template>
                          <template #seq-cell="{ row }">
                            <span class="text-sm text-gray-500">{{
                              row.index + 1
                            }}</span>
                          </template>
                          <template #quantity-cell="{ row }">
                            <UInput
                              type="number"
                              min="0"
                              step="0.0001"
                              v-model.number="row.original.quantity"
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                            />
                          </template>
                          <template #warehouse-cell="{ row }">
                            <UButton
                              variant="outline"
                              class="w-full justify-start text-left"
                              :disabled="isViewingPreviousTour || isParticipant"
                              @click="openWarehousePickerModal(row.original)"
                            >
                              {{
                                getPositionWarehouseLabel(row.original) ||
                                "Оберіть місце постачання"
                              }}
                            </UButton>
                          </template>
                          <template #start_price-cell="{ row }">
                            <UInput
                              type="number"
                              min="0"
                              step="0.0001"
                              v-model.number="row.original.start_price"
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                            />
                          </template>
                          <template #min_bid_step-cell="{ row }">
                            <UInput
                              type="number"
                              min="0"
                              step="0.0001"
                              v-model.number="row.original.min_bid_step"
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                            />
                          </template>
                          <template #max_bid_step-cell="{ row }">
                            <UInput
                              type="number"
                              min="0"
                              step="0.0001"
                              v-model.number="row.original.max_bid_step"
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                            />
                          </template>
                          <template #description-cell="{ row }">
                            <UInput
                              v-model="row.original.description"
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                            />
                          </template>
                          <template
                            v-for="attribute in tenderAttributes"
                            :key="`attr-cell-${attribute.id}`"
                            #[`${attributeAccessorKey(attribute.id)}-cell`]="{
                              row,
                            }"
                          >
                            <UInput
                              v-if="attribute.type === 'numeric'"
                              type="number"
                              min="0"
                              step="0.0001"
                              size="sm"
                              :model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] ?? null
                              "
                              :disabled="isViewingPreviousTour || isParticipant"
                              @update:model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] = $event
                              "
                            />
                            <DateValuePicker
                              v-else-if="attribute.type === 'date'"
                              :model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] ?? ''
                              "
                              size="sm"
                              :disabled="isViewingPreviousTour || isParticipant"
                              @update:model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] = $event || ''
                              "
                            />
                            <UInput
                              v-else
                              size="sm"
                              :model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] ?? ''
                              "
                              :disabled="isViewingPreviousTour || isParticipant"
                              @update:model-value="
                                ensurePositionAttributeValues(row.original)[
                                  String(attribute.id)
                                ] = $event || ''
                              "
                            />
                          </template>
                          <template #warehouse_add-cell />
                          <template #attributes_add-cell />
                          <template #actions-cell="{ row }">
                            <UButton
                              v-if="!isParticipant"
                              color="error"
                              variant="ghost"
                              size="xs"
                              icon="i-heroicons-trash"
                              :aria-label="'Видалити позицію'"
                              :disabled="isViewingPreviousTour"
                              @click="removeTenderPositionByRow(row)"
                            />
                          </template>
                        </UTable>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else-if="item.value === 'criteria'" class="space-y-6">
                  <!-- Параметри цінового критерія -->
                  <div v-if="false" class="rounded-lg p-4 bg-gray-50/50">
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
                          :disabled="isViewingPreviousTour || isParticipant"
                          @update:model-value="onPriceCriterionVatChange"
                        />
                      </UFormField>
                      <UFormField label="Доставка" class="min-w-[260px]">
                        <USelectMenu
                          v-model="priceCriterionDelivery"
                          :items="deliveryOptions"
                          value-key="value"
                          placeholder="Оберіть варіант"
                          :disabled="isViewingPreviousTour || isParticipant"
                          @update:model-value="onPriceCriterionDeliveryChange"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <!-- Інші критерії тендера: ліва панель (пошук + дерево) + список обраних -->
                  <div class="flex gap-4 min-h-0 flex-1">
                    <aside
                      class="w-72 flex-shrink-0 flex flex-col min-h-0 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
                    >
                      <div class="p-2 border-b border-gray-200">
                        <UInput
                          v-model="criteriaSearch"
                          placeholder="Пошук критеріїв"
                          size="sm"
                          class="w-full"
                        />
                      </div>
                      <div class="flex-1 min-h-0 overflow-auto p-2">
                        <div
                          v-if="loadingReferenceCriteria"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Завантаження критеріїв...
                        </div>
                        <div
                          v-else-if="!criteriaTreeItems.length"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Немає критеріїв у довіднику.
                        </div>
                        <UTree
                          v-else
                          :items="criteriaTreeItems"
                          size="sm"
                          :get-key="getCriteriaTreeKey"
                          class="border-0"
                          @select="onCriteriaTreeSelect"
                        />
                      </div>
                    </aside>
                    <div
                      class="flex-1 min-w-0 flex flex-col rounded-lg p-4 bg-white"
                    >
                      <div class="flex items-center justify-between gap-2 mb-3">
                        <h4 class="text-sm font-semibold text-gray-700">
                          Додані критерії
                        </h4>
                        <UButton
                          size="sm"
                          variant="outline"
                          icon="i-heroicons-plus"
                          :disabled="isViewingPreviousTour"
                          @click="openCreateCriterionModal"
                        >
                          Створити критерій
                        </UButton>
                      </div>
                      <p class="text-sm text-gray-600 mb-3">
                        Подвійний клік по критерію в списку зліва додає його
                        сюди. Загальні критерії заповнюються один раз на тендер,
                        індивідуальні — по кожній позиції.
                      </p>
                      <div v-if="tenderCriteriaGeneral.length > 0" class="mb-4">
                        <h5
                          class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2"
                        >
                          Загальні критерії
                        </h5>
                        <ul class="space-y-2 text-sm">
                          <li
                            v-for="c in tenderCriteriaGeneral"
                            :key="c.id"
                            class="flex items-center justify-between gap-2 py-2 px-3 rounded-md bg-blue-50/50 border border-blue-100"
                          >
                            <span class="font-medium">{{ c.name }}</span>
                            <span class="text-gray-500 text-xs">{{
                              `Тип: ${criterionTypeLabel(c.type)} | Застосування: ${criterionApplicationLabel(c.application, c.application_label)} | Обов'язковий: ${c.is_required ? "Так" : "Ні"}`
                            }}</span>
                            <UButton
                              icon="i-heroicons-trash"
                              size="xs"
                              variant="ghost"
                              color="error"
                              aria-label="Видалити з тендера"
                              :disabled="isViewingPreviousTour"
                              @click="removeCriterionFromTender(c)"
                            />
                          </li>
                        </ul>
                      </div>
                      <div v-if="tenderCriteriaIndividual.length > 0">
                        <h5
                          class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2"
                        >
                          Індивідуальні критерії (по позиції)
                        </h5>
                        <ul
                          class="space-y-2 text-sm flex-1 min-h-0 overflow-auto"
                        >
                          <li
                            v-for="c in tenderCriteriaIndividual"
                            :key="c.id"
                            class="flex items-center justify-between gap-2 py-2 px-3 rounded-md bg-gray-50 border border-gray-200"
                          >
                            <span class="font-medium">{{ c.name }}</span>
                            <span class="text-gray-500 text-xs">{{
                              `Тип: ${criterionTypeLabel(c.type)} | Застосування: ${criterionApplicationLabel(c.application, c.application_label)} | Обов'язковий: ${c.is_required ? "Так" : "Ні"}`
                            }}</span>
                            <UButton
                              icon="i-heroicons-trash"
                              size="xs"
                              variant="ghost"
                              color="error"
                              aria-label="Видалити з тендера"
                              :disabled="isViewingPreviousTour"
                              @click="removeCriterionFromTender(c)"
                            />
                          </li>
                        </ul>
                      </div>
                      <p
                        v-if="tenderCriteria.length === 0"
                        class="text-sm text-gray-500 py-2"
                      >
                        Критерії не додано.
                      </p>
                    </div>
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
              <div class="mt-3">
                <UTabs v-model="acceptanceTab" :items="acceptanceTabItems" />
              </div>
            </template>
            <div
              v-if="acceptanceTab === 'suppliers'"
              class="border border-gray-200 rounded-lg overflow-hidden"
            >
              <table class="w-full text-sm border-collapse">
                <thead>
                  <tr class="border-b border-gray-200 bg-gray-50">
                    <th class="text-left p-2 font-medium">Контрагент</th>
                    <th class="text-left p-2 font-medium">
                      Час підтвердження участі
                    </th>
                    <th class="text-left p-2 font-medium">
                      Час подачі пропозиції
                    </th>
                    <th class="text-left p-2 font-medium w-40">Дія</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="proposal in decisionProposals"
                    :key="proposal.id"
                    class="border-b border-gray-200 hover:bg-gray-50/50"
                  >
                    <td class="p-2">
                      {{
                        proposal.supplier_company?.name ||
                        proposal.supplier_name ||
                        "—"
                      }}
                    </td>
                    <td class="p-2">
                      {{ formatDateTime(proposal.created_at) }}
                    </td>
                    <td class="p-2">
                      {{ formatDateTime(proposal.submitted_at) }}
                    </td>
                    <td class="p-2">
                      <UButton
                        size="xs"
                        variant="outline"
                        @click="openParticipantProposalModal(proposal)"
                      >
                        Пропозиція
                      </UButton>
                    </td>
                  </tr>
                  <tr v-if="!decisionProposals.length">
                    <td colspan="4" class="p-4 text-center text-gray-500">
                      Немає контрагентів, що підтвердили участь.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-if="acceptanceTab === 'positions'"
              class="mt-4 border border-gray-200 rounded-lg overflow-hidden overflow-auto"
            >
              <table
                v-if="
                  proposalComparisonPositions.length &&
                  submittedDecisionProposals.length
                "
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
                    <template
                      v-for="proposal in submittedDecisionProposals"
                      :key="proposal.id"
                    >
                      <th
                        :colspan="3 + (tender.value?.criteria?.length ?? 0)"
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
                          >({{ proposal.supplier_company.edrpou }})</span
                        >
                      </th>
                    </template>
                  </tr>
                  <tr class="border-b border-gray-200 bg-gray-50">
                    <th class="p-2 bg-gray-50"></th>
                    <th class="p-2 bg-gray-50"></th>
                    <template
                      v-for="proposal in submittedDecisionProposals"
                      :key="proposal.id"
                    >
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        {{ proposalComparisonPriceHeader }}
                      </th>
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        Ціна без ПДВ
                      </th>
                      <th
                        class="text-left p-2 font-medium border-l border-gray-200 whitespace-nowrap"
                      >
                        Сума
                      </th>
                      <th
                        v-for="c in tender.value?.criteria ?? []"
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
                    v-for="pos in proposalComparisonPositions"
                    :key="pos.id"
                    class="border-b border-gray-200 hover:bg-gray-50/50"
                  >
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ pos.name }}
                    </td>
                    <td class="p-2 bg-white whitespace-nowrap">
                      {{ formatDecimalDisplay(pos.quantity) }}
                      {{ pos.unit_name || "" }}
                    </td>
                    <template
                      v-for="proposal in submittedDecisionProposals"
                      :key="proposal.id"
                    >
                      <td class="p-2 border-l border-gray-200">
                        {{
                          formatNumericOrDash(
                            getProposalPositionValue(proposal, pos.id)?.price,
                          )
                        }}
                      </td>
                      <td class="p-2 border-l border-gray-200">
                        {{
                          formatNumericOrDash(
                            getProposalPositionValue(proposal, pos.id)
                              ?.price_without_vat,
                          )
                        }}
                      </td>
                      <td class="p-2 border-l border-gray-200">
                        {{ getProposalPositionSum(proposal, pos) ?? "—" }}
                      </td>
                      <td
                        v-for="c in tender.value?.criteria ?? []"
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
                Немає позицій або пропозицій для відображення.
              </p>
            </div>
            <div
              v-if="acceptanceTab === 'history' && isOnlineAuctionTender"
              class="mt-4 space-y-4"
            >
              <div class="max-w-sm">
                <UFormField label="Позиція">
                  <USelectMenu
                    v-model="acceptanceBidHistoryPositionId"
                    :items="acceptanceBidHistoryPositionOptions"
                    value-key="value"
                    label-key="label"
                    placeholder="Оберіть позицію"
                  />
                </UFormField>
              </div>
              <div class="border border-gray-200 rounded-lg overflow-hidden">
                <table
                  v-if="acceptanceBidHistory.length"
                  class="w-full text-sm border-collapse"
                >
                  <thead>
                    <tr class="border-b border-gray-200 bg-gray-50">
                      <th class="text-left p-2 font-medium">Контрагент</th>
                      <th class="text-left p-2 font-medium">Ставка</th>
                      <th class="text-left p-2 font-medium">Користувач</th>
                      <th class="text-left p-2 font-medium">Дата та час</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="item in acceptanceBidHistory"
                      :key="item.id"
                      class="border-b border-gray-200 hover:bg-gray-50/50"
                    >
                      <td class="p-2">
                        {{ item.supplier_company_name || "—" }}
                      </td>
                      <td class="p-2">{{ formatNumericOrDash(item.price) }}</td>
                      <td class="p-2">{{ item.created_by_display || "—" }}</td>
                      <td class="p-2">{{ formatDateTime(item.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="text-gray-500 py-8 text-center">
                  {{
                    acceptanceBidHistoryLoading
                      ? "Завантаження історії ставок..."
                      : "Немає історії ставок для вибраної позиції."
                  }}
                </p>
              </div>
            </div>
          </UCard>
        </template>
        <template v-else-if="displayStage === 'decision'">
          <div class="space-y-6">
            <!-- Верхня область: орієнтовна ринкова та рішення -->
            <div class="rounded-lg p-4 bg-gray-50/50">
              <div class="flex flex-wrap items-end gap-6">
                <UFormField label="Орієнтовна ринкова" class="min-w-[220px]">
                  <USelectMenu
                    v-model="estimatedMarketMethod"
                    :items="estimatedMarketOptions"
                    value-key="value"
                    placeholder="Оберіть"
                  />
                </UFormField>
                <UFormField label="Економія по ринковій" class="min-w-[260px]">
                  <USelectMenu
                    v-model="decisionMarketMode"
                    :items="decisionMarketModeOptions"
                    value-key="value"
                    placeholder="Оберіть"
                  />
                </UFormField>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
                <div class="rounded border border-gray-200 bg-white p-3">
                  <div class="text-xs text-gray-500">
                    Вартість по кращій ціні
                  </div>
                  <div class="text-base font-semibold text-gray-900">
                    {{ formatDecisionSummaryAmount(decisionSummary.bestTotal) }}
                  </div>
                </div>
                <div class="rounded border border-gray-200 bg-white p-3">
                  <div class="text-xs text-gray-500">
                    Вартість за ціною що обирається
                  </div>
                  <div class="text-base font-semibold text-gray-900">
                    {{
                      formatDecisionSummaryAmount(decisionSummary.selectedTotal)
                    }}
                  </div>
                </div>
                <div class="rounded border border-gray-200 bg-white p-3">
                  <div class="text-xs text-gray-500">Економія в сумі</div>
                  <div class="text-base font-semibold text-gray-900">
                    {{
                      formatDecisionSummaryAmount(
                        decisionSummary.aggregateTotal,
                      )
                    }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Таблиця позицій (стиль як на підготовці) -->
            <div class="rounded-lg p-4 bg-white">
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
                  <template #economy_market-cell="{ row }">
                    <span
                      :class="[
                        'inline-block w-full py-1 -my-1 px-2 -mx-2 rounded',
                        Number(row.original.economy_market_num) < 0
                          ? 'bg-red-100 text-red-700'
                          : 'text-gray-700',
                      ]"
                      >{{ row.original.economy_market }}</span
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
                Перегляньте переможців по позиціях та підтвердьте рішення для
                завершення тендера.
              </p>
              <div class="border border-gray-200 rounded-lg overflow-hidden">
                <table class="w-full text-sm border-collapse">
                  <thead>
                    <tr class="border-b border-gray-200 bg-gray-50">
                      <th class="text-left p-2 font-medium">Позиція</th>
                      <th class="text-left p-2 font-medium">Кількість</th>
                      <th class="text-left p-2 font-medium">Переможець</th>
                      <th class="text-left p-2 font-medium">Ціна</th>
                      <th class="text-left p-2 font-medium">Вартість</th>
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
                      v-for="pos in displayTenderPositions"
                      :key="pos.id"
                      class="border-b border-gray-200 hover:bg-gray-50/50"
                    >
                      <td class="p-2">{{ pos.name }}</td>
                      <td class="p-2">
                        {{ formatDecimalDisplay(pos.quantity) }}
                        {{ pos.unit_name ?? "" }}
                      </td>
                      <td class="p-2">
                        {{ pos.winner_supplier_name ?? "—" }}
                      </td>
                      <td class="p-2">
                        {{ formatNumericOrDash(pos.winner_price) }}
                      </td>
                      <td class="p-2">
                        {{
                          getApprovalPositionTotal(
                            pos.quantity,
                            pos.winner_price,
                          )
                        }}
                      </td>
                      <td v-for="c in tenderCriteria" :key="c.id" class="p-2">
                        {{
                          (pos.winner_criterion_values &&
                            (pos.winner_criterion_values[c.id] ??
                              pos.winner_criterion_values[String(c.id)])) ??
                          "—"
                        }}
                      </td>
                    </tr>
                    <tr v-if="!displayTenderPositions.length">
                      <td colspan="100" class="p-4 text-center text-gray-500">
                        Немає позицій.
                      </td>
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

      <aside
        class="w-56 flex-shrink-0 flex min-h-0 flex-col gap-3 rounded-xl border border-gray-200 bg-white shadow-sm p-3"
      >
        <template v-if="displayStage === 'passport'">
          <UButton
            class="w-full"
            :loading="saving"
            :disabled="isViewingPreviousTour"
            @click="savePassport"
          >
            Зберегти
          </UButton>
        </template>

        <template v-else-if="displayStage === 'preparation'">
          <template v-if="canShowApproverActionButtons">
            <UButton
              class="w-full"
              :loading="approvalActionSaving"
              :disabled="isViewingPreviousTourOnly"
              @click="openApprovalActionModal('approved')"
            >
              Погодити
            </UButton>
            <UButton
              class="w-full"
              color="error"
              variant="outline"
              :disabled="isViewingPreviousTourOnly"
              @click="openApprovalActionModal('rejected')"
            >
              Відхилити
            </UButton>
          </template>
          <UButton
            v-if="canShowPreparationSubmitButton"
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="openApprovalSubmitModal"
          >
            Зберегти
          </UButton>
          <UButton
            v-if="canShowPreparationGoDecisionButton"
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="goToDecision"
          >
            Перейти на вибір рішення
          </UButton>
          <UButton
            v-if="canShowPreparationPublishButtons"
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="openPublishModal"
          >
            Затвердити
          </UButton>
          <template v-if="isTenderAuthor">
            <UButton
              v-if="!showInvitationPanel"
              class="w-full"
              variant="outline"
              :disabled="isViewingPreviousTour"
              @click="showInvitationPanel = true"
            >
              Запросити учасників
            </UButton>
          </template>
          <UButton
            class="w-full"
            variant="outline"
            @click="openAttachedFilesModal"
          >
            Прикріплені файли
          </UButton>
        </template>

        <template v-else-if="displayStage === 'acceptance'">
          <div
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
              Таймер: {{ acceptanceTimerText }}
            </p>
          </div>
          <UButton
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="openTimingModal"
          >
            Змінити час проведення
          </UButton>
          <UButton
            v-if="canShowAcceptanceInvitationsButton"
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="showAcceptanceInvitationsModal = true"
          >
            Запрошення
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            @click="openAttachedFilesModal"
          >
            Прикріплені файли
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalsModal"
          >
            Усі пропозиції
          </UButton>
          <UButton
            v-if="!isParticipant"
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openOrganizerChatModal"
          >
            Чат із контрагентами
          </UButton>
          <div
            v-if="isParticipant"
            class="rounded-lg border border-gray-200 p-4 text-sm space-y-3"
          >
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
            <UButton
              class="w-full"
              variant="outline"
              @click="openParticipantChatModal"
            >
              Чат із організатором
            </UButton>
          </div>
        </template>
        <template v-else-if="displayStage === 'decision'">
          <template
            v-if="
              displayStage === 'decision' &&
              tender?.conduct_type === 'registration'
            "
          >
            <UButton
              class="w-full"
              variant="outline"
              :disabled="isViewingPreviousTour"
              @click="goBackToPreparation"
            >
              Повернутись на підготовку
            </UButton>
          </template>
          <template
            v-else-if="
              displayStage === 'decision' &&
              (tender?.conduct_type === 'rfx' ||
                tender?.conduct_type === 'online_auction')
            "
          >
            <UButton
              class="w-full"
              variant="outline"
              :disabled="isViewingPreviousTour"
              @click="openResumeAcceptanceModal"
            >
              Відновити прийом пропозицій
            </UButton>
          </template>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="showWinnerModal = true"
          >
            Ручний вибір переможця
          </UButton>
          <UButton
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="openDecisionModal"
          >
            Зафіксувати рішення
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalsModal"
          >
            Усі пропозиції
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalEditor"
          >
            Редагувати КП
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalChangeReportModal"
          >
            Звіт по змінам в КП
          </UButton>
          <UButton
            class="w-full"
            color="warning"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openDisqualificationModal"
          >
            Дискваліфікація
          </UButton>
        </template>

        <template v-else-if="displayStage === 'approval'">
          <template v-if="canShowApproverActionButtons">
            <UButton
              class="w-full"
              :loading="approvalActionSaving"
              :disabled="isViewingPreviousTourOnly"
              @click="openApprovalActionModal('approved')"
            >
              Погодити
            </UButton>
            <UButton
              class="w-full"
              color="error"
              variant="outline"
              :disabled="isViewingPreviousTourOnly"
              @click="openApprovalActionModal('rejected')"
            >
              Відхилити
            </UButton>
          </template>
          <template v-else-if="canShowAuthorApprovalButtons">
            <UButton
              class="w-full"
              :disabled="isViewingPreviousTour"
              @click="openApprovalActionModal('approved')"
            >
              Затвердити
            </UButton>
            <UButton
              class="w-full"
              color="error"
              variant="outline"
              :disabled="isViewingPreviousTour"
              @click="openApprovalActionModal('rejected')"
            >
              Скасувати
            </UButton>
          </template>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalsModal"
          >
            Усі пропозиції
          </UButton>
        </template>
        <UButton
          v-if="displayStage !== 'passport'"
          class="w-full"
          variant="outline"
          @click="openApprovalJournalModal"
        >
          Журнал погодження
        </UButton>
        <UCard
          v-if="showApprovalRouteCard"
          class="mt-auto min-h-[264px] basis-2/5 flex flex-col"
        >
          <template #header
            ><h4 class="text-sm font-semibold">Маршрут погодження</h4></template
          >
          <div
            class="mt-2 flex-1 min-h-0 overflow-auto text-xs approval-route-scroll"
          >
            <div class="space-y-2 pr-1 min-w-max pb-2">
              <div
                v-for="(node, index) in approvalRouteNodes"
                :key="`${node.kind}-${node.order || index}-${index}`"
                class="rounded p-2 max-w-[320px]"
              >
                <div class="flex items-center gap-2 font-medium">
                  <UIcon
                    :name="
                      node.kind === 'role'
                        ? 'i-lucide-users-round'
                        : 'i-lucide-user-round'
                    "
                    class="size-4 text-gray-600"
                  />
                  <span class="break-words">{{
                    node.label ||
                    (node.kind === "role" ? "Роль" : "Автор тендера")
                  }}</span>
                </div>
                <div class="mt-2 space-y-1.5">
                  <div
                    v-for="userNode in node.users || []"
                    :key="`${node.order || index}-${userNode.id || userNode.short_name}`"
                    class="ml-4 flex items-center gap-2"
                  >
                    <span
                      class="inline-flex h-6 w-6 items-center justify-center rounded-full"
                      :class="approvalUserStatusClass(userNode.status)"
                    >
                      <UIcon
                        :name="approvalUserStatusIcon(userNode.status)"
                        class="size-4"
                      />
                    </span>
                    <span class="break-words">{{
                      userNode.short_name || userNode.full_name || "—"
                    }}</span>
                  </div>
                </div>
              </div>
              <p v-if="!approvalRouteNodes.length" class="text-gray-500">
                Маршрут погодження ще не сформовано.
              </p>
            </div>
          </div>
        </UCard>
        <UCard
          v-if="displayStage === 'passport' && form.approval_model_id"
          class="mt-auto"
        >
          <template #header
            ><h4 class="text-sm font-semibold">Погоджувачі</h4></template
          >
          <ul class="space-y-2 text-xs">
            <li
              v-for="step in selectedApprovalModelSteps"
              :key="step.id || step.order"
              class="border-l-2 border-gray-300 pl-2"
            >
              <div class="font-medium">{{ step.role_name || "Роль" }}</div>
              <div class="text-gray-500">
                Підготовка: {{ ruleLabel(step.preparation_rule) }}
              </div>
              <div class="text-gray-500">
                Затвердження: {{ ruleLabel(step.approval_rule) }}
              </div>
            </li>
          </ul>
        </UCard>
      </aside>
    </div>

    <UModal v-model:open="showApprovalJournalModal">
      <template #content>
        <UCard>
          <template #header><h3>Журнал погодження</h3></template>
          <UTable
            :data="approvalJournalRows"
            :columns="approvalJournalColumns"
            class="w-full"
          />
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showApprovalActionModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{
                pendingApprovalAction === "approved"
                  ? "Погодити тендер"
                  : "Скасувати тендер"
              }}
            </h3>
          </template>
          <div class="space-y-4">
            <UFormField
              :label="
                pendingApprovalAction === 'approved'
                  ? 'Коментар (необовʼязково)'
                  : 'Коментар (обовʼязково)'
              "
            >
              <UTextarea v-model="approvalActionComment" :rows="4" />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton
                variant="outline"
                @click="showApprovalActionModal = false"
                >Скасувати</UButton
              >
              <UButton
                :loading="approvalActionSaving"
                @click="submitApprovalAction"
              >
                Підтвердити
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showApprovalSubmitModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>Зберегти та передати на погодження</h3>
          </template>
          <div class="space-y-4">
            <UFormField label="Коментар (необовʼязково)">
              <UTextarea v-model="approvalSubmitComment" :rows="4" />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton
                variant="outline"
                @click="showApprovalSubmitModal = false"
              >
                Скасувати
              </UButton>
              <UButton
                :loading="approvalSubmitSaving"
                @click="submitApprovalSubmit"
              >
                Зберегти
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showConditionTemplateModal">
      <template #content>
        <UCard>
          <template #header><h3>Шаблони умов</h3></template>
          <div class="space-y-3">
            <div
              v-if="conditionTemplatesLoading"
              class="py-8 text-center text-sm text-gray-500"
            >
              Завантаження шаблонів...
            </div>
            <div
              v-else-if="!conditionTemplates.length"
              class="py-8 text-center text-sm text-gray-500"
            >
              Немає доступних шаблонів умов.
            </div>
            <div v-else class="max-h-[60vh] overflow-auto space-y-2">
              <UButton
                v-for="templateItem in conditionTemplates"
                :key="templateItem.id"
                class="w-full justify-start"
                variant="outline"
                color="neutral"
                @click="applyConditionTemplate(templateItem)"
              >
                {{ templateItem.name }}
              </UButton>
            </div>
            <div class="flex justify-end">
              <UButton
                variant="outline"
                @click="showConditionTemplateModal = false"
              >
                Закрити
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showAcceptanceInvitationsModal">
      <template #content>
        <UCard>
          <template #header><h3>Запрошення</h3></template>
          <div class="space-y-3">
            <UButton class="w-full" @click="repeatAcceptanceInvitationNotice">
              Повторити сповіщення
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="
                showAcceptanceInvitationsModal = false;
                showInviteByEmailModal = true;
              "
            >
              Запросити по email
            </UButton>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showPublishModal">
      <template #content>
        <UCard>
          <template #header><h3>Період проведення</h3></template>
          <div class="space-y-4">
            <p class="text-sm text-gray-600">
              Вкажіть дати та час початку/завершення прийому пропозицій.
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField label="Дата початку" required>
                <DateValuePicker
                  :model-value="publishStartDate"
                  class="w-full"
                  @update:model-value="publishStartDate = $event || ''"
                />
              </UFormField>
              <UFormField label="Дата завершення" required>
                <DateValuePicker
                  :model-value="publishEndDate"
                  class="w-full"
                  @update:model-value="publishEndDate = $event || ''"
                />
              </UFormField>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField label="Час початку" required>
                <UInput
                  v-model="publishStartTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="
                    publishStartTime = formatTimeInput($event)
                  "
                />
              </UFormField>
              <UFormField label="Час завершення" required>
                <UInput
                  v-model="publishEndTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="publishEndTime = formatTimeInput($event)"
                />
              </UFormField>
            </div>
            <p class="text-xs text-gray-500">
              Введіть час вручну у форматі ГГ:ХХ (наприклад 9:30 або 09:30).
            </p>
            <UFormField label="Коментар" required>
              <UTextarea
                v-model="timingComment"
                :rows="3"
                class="w-full"
                placeholder="Вкажіть причину зміни часу проведення"
              />
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

    <UModal v-model:open="showInviteByEmailModal">
      <template #content>
        <UCard>
          <template #header><h3>Запрошення по email</h3></template>
          <div class="space-y-4">
            <UFormField
              label="Введіть email (кожен з нового рядка) або завантажте список"
            >
              <UTextarea
                v-model="inviteByEmailText"
                placeholder="email1@example.com&#10;email2@example.com"
                :rows="6"
                class="w-full"
              />
            </UFormField>
            <div class="flex items-center gap-2">
              <input
                ref="inviteByEmailFileInput"
                type="file"
                accept=".txt,.csv,text/plain"
                class="hidden"
                @change="onInviteByEmailFileChange"
              />
              <UButton
                variant="outline"
                size="sm"
                icon="i-heroicons-arrow-up-tray"
                @click="inviteByEmailFileInput?.click()"
              >
                Завантажити список
              </UButton>
              <span class="text-xs text-gray-500"
                >Файл: один email на рядок</span
              >
            </div>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="submitInviteByEmail">
                Запросити
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showInviteByEmailModal = false"
              >
                Скасувати
              </UButton>
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
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField
                label="Дата початку"
                required
                :help="
                  canEditStart
                    ? ''
                    : 'Після старту час початку змінювати не можна'
                "
              >
                <DateValuePicker
                  :model-value="timingStartDate"
                  class="w-full"
                  :disabled="!canEditStart"
                  @update:model-value="timingStartDate = $event || ''"
                />
              </UFormField>
              <UFormField label="Дата завершення" required>
                <DateValuePicker
                  :model-value="timingEndDate"
                  class="w-full"
                  @update:model-value="timingEndDate = $event || ''"
                />
              </UFormField>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField label="Час початку" required>
                <UInput
                  v-model="timingStartTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="
                    timingStartTime = formatTimeInput($event)
                  "
                  :disabled="!canEditStart"
                />
              </UFormField>
              <UFormField label="Час завершення" required>
                <UInput
                  v-model="timingEndTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="timingEndTime = formatTimeInput($event)"
                />
              </UFormField>
            </div>
            <p class="text-xs text-gray-500">
              Введіть час вручну у форматі ГГ:ХХ (наприклад 9:30 або 09:30).
            </p>
            <div class="flex gap-2">
              <UButton
                class="flex-1"
                :disabled="isViewingPreviousTour"
                @click="saveTiming"
              >
                Зберегти
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showTimingModal = false"
              >
                Скасувати
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showResumeAcceptanceModal">
      <template #content>
        <UCard>
          <template #header><h3>Відновити прийом пропозицій</h3></template>
          <p class="text-sm text-gray-600 mb-4">
            Вкажіть час початку (не раніше поточного) та час завершення прийому
            пропозицій.
          </p>
          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField label="Дата початку" required>
                <DateValuePicker
                  :model-value="resumeAcceptanceStartDate"
                  class="w-full"
                  @update:model-value="resumeAcceptanceStartDate = $event || ''"
                />
              </UFormField>
              <UFormField label="Дата завершення" required>
                <DateValuePicker
                  :model-value="resumeAcceptanceEndDate"
                  class="w-full"
                  @update:model-value="resumeAcceptanceEndDate = $event || ''"
                />
              </UFormField>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <UFormField label="Час початку" required>
                <UInput
                  v-model="resumeAcceptanceStartTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="
                    resumeAcceptanceStartTime = formatTimeInput($event)
                  "
                />
              </UFormField>
              <UFormField label="Час завершення" required>
                <UInput
                  v-model="resumeAcceptanceEndTime"
                  type="text"
                  inputmode="numeric"
                  placeholder="ГГ:ХХ"
                  maxlength="5"
                  class="w-full"
                  @update:model-value="
                    resumeAcceptanceEndTime = formatTimeInput($event)
                  "
                />
              </UFormField>
            </div>
            <p class="text-xs text-gray-500">
              Введіть час вручну у форматі ГГ:ХХ (наприклад 9:30 або 09:30).
            </p>
            <div class="flex gap-2">
              <UButton
                class="flex-1"
                :disabled="resumeAcceptanceSaving"
                @click="submitResumeAcceptance"
              >
                Відновити
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                :disabled="resumeAcceptanceSaving"
                @click="showResumeAcceptanceModal = false"
              >
                Скасувати
              </UButton>
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
              v-for="pos in displayTenderPositions"
              :key="pos.id"
              class="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-3"
            >
              <span class="text-sm font-medium min-w-[140px]">{{
                pos.name
              }}</span>
              <USelectMenu
                :model-value="selectedWinnerByPosition[pos.id] ?? null"
                :items="decisionWinnerOptionsWithEmpty(pos.id)"
                value-key="value"
                placeholder="Оберіть контрагента"
                class="flex-1 min-w-[200px]"
                @update:model-value="(v) => setDecisionWinner(pos.id, v)"
              />
              <UButton
                type="button"
                size="xs"
                variant="outline"
                color="error"
                :disabled="selectedWinnerByPosition[pos.id] == null"
                @click="setDecisionWinner(pos.id, null)"
              >
                Видалити
              </UButton>
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
          <div class="space-y-4">
            <UFormField label="Варіант рішення" required>
              <USelectMenu
                v-model="selectedDecisionMode"
                :items="decisionModeSelectableOptions"
                value-key="value"
                placeholder="Оберіть рішення"
                class="w-full"
              />
            </UFormField>
            <UFormField
              v-if="showDecisionJustificationField"
              label="Обґрунтування (необов'язково)"
            >
              <UTextarea
                v-model="decisionJustification"
                :rows="3"
                placeholder="За потреби вкажіть обґрунтування"
              />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="closeDecisionModal">
                Закрити
              </UButton>
              <UButton
                :loading="saving"
                :disabled="!selectedDecisionMode"
                @click="confirmDecision"
              >
                Передати на затвердження
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <TenderDeferredModals
      v-if="showDeferredTenderModals"
      :show-protocol-modal="showProtocolModal"
      :show-proposals-modal="showProposalsModal"
      :show-participant-proposal-modal="showParticipantProposalModal"
      :show-participant-chat-modal="showParticipantChatModal"
      :show-organizer-chat-modal="showOrganizerChatModal"
      :show-proposal-change-report-modal="showProposalChangeReportModal"
      :show-disqualification-modal="showDisqualificationModal"
      :show-attached-files-modal="showAttachedFilesModal"
      :protocol-preview="protocolPreview"
      :protocol-preview-loading="protocolPreviewLoading"
      :protocol-preview-error="protocolPreviewError"
      :download-protocol-pdf="downloadProtocolPdf"
      :proposal-comparison-positions="proposalComparisonPositions"
      :submitted-decision-proposals="submittedDecisionProposals"
      :tender="tender"
      :proposal-comparison-price-header="proposalComparisonPriceHeader"
      :proposal-comparison-by-position="proposalComparisonByPosition"
      :format-numeric-or-dash="formatNumericOrDash"
      :get-proposal-position-value="getProposalPositionValue"
      :get-proposal-position-sum="getProposalPositionSum"
      :get-proposal-criterion-value="getProposalCriterionValue"
      :format-decimal-display="formatDecimalDisplay"
      :selected-participant-proposal="selectedParticipantProposal"
      :display-tender-positions="displayTenderPositions"
      :chat-messages="chatMessages"
      :chat-draft="chatDraft"
      :chat-sending="chatSending"
      :close-chat-modals="closeChatModals"
      :submit-participant-chat-message="submitParticipantChatMessage"
      :chat-threads="chatThreads"
      :selected-chat-supplier-id="selectedChatSupplierId"
      :select-organizer-chat-thread="selectOrganizerChatThread"
      :submit-organizer-chat-message="submitOrganizerChatMessage"
      :format-date-time="formatDateTime"
      :proposal-change-report="proposalChangeReport"
      :proposal-change-report-loading="proposalChangeReportLoading"
      :format-criterion-summary="formatCriterionSummary"
      :disqualification-rows="disqualificationRows"
      :disqualification-saving="disqualificationSaving"
      :submit-disqualifications="submitDisqualifications"
      :is-read-only-approver="isReadOnlyApprover"
      :attached-files-uploading="attachedFilesUploading"
      :attached-files-loading="attachedFilesLoading"
      :attached-files-list="attachedFilesList"
      :on-attached-files-input-change="onAttachedFilesInputChange"
      :toggle-file-visibility="toggleFileVisibility"
      :format-file-date="formatFileDate"
      :delete-attached-file="deleteAttachedFile"
      @update:show-protocol-modal="showProtocolModal = $event"
      @update:show-proposals-modal="showProposalsModal = $event"
      @update:show-participant-proposal-modal="showParticipantProposalModal = $event"
      @update:show-participant-chat-modal="showParticipantChatModal = $event"
      @update:show-organizer-chat-modal="showOrganizerChatModal = $event"
      @update:show-proposal-change-report-modal="showProposalChangeReportModal = $event"
      @update:show-disqualification-modal="showDisqualificationModal = $event"
      @update:show-attached-files-modal="showAttachedFilesModal = $event"
      @update:chat-draft="chatDraft = $event"
    />

    <UModal v-model:open="showCreateCriterionModal">
      <template #content>
        <UCard>
          <template #header><h3>Створити критерій</h3></template>
          <div class="space-y-4">
            <UFormField label="Назва критерія" required>
              <UInput
                v-model="createCriterionForm.name"
                placeholder="Наприклад: Ціна за одиницю"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <UFormField label="Тип критерія" required>
              <USelectMenu
                v-model="createCriterionForm.type"
                :items="criterionTypeOptions"
                value-key="value"
                placeholder="Оберіть тип"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <UFormField label="Застосування" required>
              <USelectMenu
                v-model="createCriterionForm.application"
                :items="criterionApplicationOptions"
                value-key="value"
                placeholder="Оберіть застосування"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <UFormField>
              <UCheckbox
                v-model="createCriterionForm.is_required"
                label="Обов'язковий критерій"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <div class="flex gap-2 justify-end pt-2">
              <UButton
                variant="outline"
                :disabled="createCriterionSaving"
                @click="showCreateCriterionModal = false"
              >
                Скасувати
              </UButton>
              <UButton
                :loading="createCriterionSaving"
                @click="saveCreateCriterion"
              >
                Створити та додати
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showNomenclaturePickerModal">
      <template #content>
        <UCard>
          <template #header><h3>Додати номенклатуру</h3></template>
          <div class="space-y-4">
            <UInput
              v-model="nomenclatureSearch"
              placeholder="Пошук номенклатури"
              size="sm"
              class="w-full"
            />
            <div
              class="h-[360px] overflow-auto border border-gray-200 rounded-lg p-2"
            >
              <div
                v-if="loadingNomenclatures"
                class="text-sm text-gray-500 py-4 text-center"
              >
                Завантаження номенклатур...
              </div>
              <div
                v-else-if="!nomenclatureTreeItems.length"
                class="text-sm text-gray-500 py-4 text-center"
              >
                Оберіть категорію або CPV у паспорті тендера.
              </div>
              <UTree
                v-else
                :items="nomenclatureTreeItems"
                size="sm"
                :get-key="getNomenclatureTreeKey"
                class="border-0"
                @select="onNomenclatureTreeSelect"
              />
            </div>
            <div class="flex items-center justify-start gap-2">
              <UButton
                size="sm"
                icon="i-heroicons-plus"
                :disabled="
                  selectedNomenclatureId == null || isViewingPreviousTour
                "
                @click="addSelectedNomenclatureFromPicker"
              >
                Додати номенклатуру
              </UButton>
              <UButton
                size="sm"
                variant="outline"
                icon="i-heroicons-plus"
                :disabled="
                  isViewingPreviousTour || !(form.cpv_ids?.length ?? 0)
                "
                @click="
                  showNomenclaturePickerModal = false;
                  showCreateNomenclatureModal = true;
                "
              >
                Створити номенклатуру
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <WarehousePickerModal
      :open="showWarehousePickerModal"
      :items="availableWarehouses"
      :loading="loadingWarehouses"
      :selected-warehouse-id="selectedWarehouseIdForActivePosition"
      title="Обрати місце постачання"
      @update:open="showWarehousePickerModal = $event"
      @select="onWarehouseSelected"
    />

    <UModal v-model:open="showAttributePickerModal">
      <template #content>
        <UCard>
          <template #header><h3>Додати атрибут</h3></template>
          <div class="space-y-4">
            <UInput
              v-model="attributeSearch"
              placeholder="Пошук атрибутів"
              size="sm"
              class="w-full"
            />
            <div
              class="h-[360px] overflow-auto border border-gray-200 rounded-lg p-2"
            >
              <div
                v-if="loadingReferenceAttributes"
                class="text-sm text-gray-500 py-4 text-center"
              >
                Завантаження атрибутів...
              </div>
              <div
                v-else-if="!attributesTreeItems.length"
                class="text-sm text-gray-500 py-4 text-center"
              >
                Немає атрибутів у довіднику.
              </div>
              <UTree
                v-else
                :items="attributesTreeItems"
                size="sm"
                :get-key="getAttributesTreeKey"
                class="border-0"
                @select="onAttributesTreeSelect"
              />
            </div>
            <div class="flex items-center justify-start gap-2">
              <UButton
                size="sm"
                icon="i-heroicons-plus"
                :disabled="selectedAttributeId == null || isViewingPreviousTour"
                @click="addSelectedAttributeFromPicker"
              >
                Додати атрибут
              </UButton>
              <UButton
                size="sm"
                variant="outline"
                icon="i-heroicons-plus"
                :disabled="isViewingPreviousTour"
                @click="
                  showAttributePickerModal = false;
                  openCreateAttributeModal();
                "
              >
                Створити атрибут
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showCreateAttributeModal">
      <template #content>
        <UCard>
          <template #header><h3>Створити атрибут</h3></template>
          <div class="space-y-4">
            <UFormField label="Назва атрибута" required>
              <UInput
                v-model="createAttributeForm.name"
                placeholder="Введіть назву"
                :disabled="createAttributeSaving"
              />
            </UFormField>
            <UFormField label="Тип атрибута" required>
              <USelectMenu
                v-model="createAttributeForm.type"
                :items="attributeTypeOptions"
                value-key="value"
                :disabled="createAttributeSaving"
              />
            </UFormField>
            <UFormField label="Категорія">
              <USelectMenu
                v-model="createAttributeForm.category"
                :items="attributeCategoryOptions"
                value-key="value"
                placeholder="Оберіть категорію"
                :disabled="createAttributeSaving"
              />
            </UFormField>
            <UCheckbox
              v-model="createAttributeForm.is_required"
              label="Обовʼязковий для заповнення"
              :disabled="createAttributeSaving"
            />
            <template v-if="createAttributeForm.type === 'numeric'">
              <UFormField label="Варіанти числових значень">
                <div class="space-y-2">
                  <div
                    v-for="(_val, idx) in createAttributeForm.options
                      .numeric_choices"
                    :key="idx"
                    class="flex gap-2 items-center"
                  >
                    <UInput
                      v-model.number="
                        createAttributeForm.options.numeric_choices[idx]
                      "
                      type="number"
                      class="flex-1"
                      :disabled="createAttributeSaving"
                    />
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="red"
                      aria-label="Видалити"
                      :disabled="createAttributeSaving"
                      @click="
                        createAttributeForm.options.numeric_choices.splice(
                          idx,
                          1,
                        )
                      "
                    />
                  </div>
                  <UButton
                    size="sm"
                    variant="outline"
                    icon="i-heroicons-plus"
                    :disabled="createAttributeSaving"
                    @click="
                      createAttributeForm.options.numeric_choices.push(null)
                    "
                  >
                    Додати значення
                  </UButton>
                </div>
              </UFormField>
            </template>
            <template v-else-if="createAttributeForm.type === 'text'">
              <UFormField label="Варіанти текстових значень">
                <div class="space-y-2">
                  <div
                    v-for="(_val, idx) in createAttributeForm.options
                      .text_choices"
                    :key="idx"
                    class="flex gap-2 items-center"
                  >
                    <UInput
                      v-model="createAttributeForm.options.text_choices[idx]"
                      class="flex-1"
                      placeholder="Текст варіанту"
                      :disabled="createAttributeSaving"
                    />
                    <UButton
                      icon="i-heroicons-trash"
                      size="xs"
                      variant="ghost"
                      color="red"
                      aria-label="Видалити"
                      :disabled="createAttributeSaving"
                      @click="
                        createAttributeForm.options.text_choices.splice(idx, 1)
                      "
                    />
                  </div>
                  <UButton
                    size="sm"
                    variant="outline"
                    icon="i-heroicons-plus"
                    :disabled="createAttributeSaving"
                    @click="createAttributeForm.options.text_choices.push('')"
                  >
                    Додати варіант
                  </UButton>
                </div>
              </UFormField>
            </template>
            <div class="flex gap-2 justify-end">
              <UButton
                variant="outline"
                :disabled="createAttributeSaving"
                @click="showCreateAttributeModal = false"
              >
                Скасувати
              </UButton>
              <UButton
                :loading="createAttributeSaving"
                @click="submitCreateAttribute"
              >
                Створити та додати
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showCreateNomenclatureModal">
      <template #content>
        <UCard>
          <template #header><h3>Створити номенклатуру</h3></template>
          <div class="space-y-4">
            <p class="text-sm text-gray-600">
              Номенклатура буде створена в довіднику, привʼязана до категорій
              CPV з паспорта тендера та додана до позицій тендера.
            </p>
            <UFormField label="Назва номенклатури" required>
              <UInput
                v-model="createNomenclatureForm.name"
                placeholder="Введіть назву"
                :disabled="createNomenclatureSaving"
              />
            </UFormField>
            <UFormField label="Одиниця виміру" required>
              <USelectMenu
                v-model="createNomenclatureForm.unit"
                :items="createNomenclatureUnitOptions"
                value-key="value"
                placeholder="Оберіть одиницю виміру"
                :disabled="createNomenclatureSaving"
              />
            </UFormField>
            <div class="flex gap-2 justify-end">
              <UButton
                variant="outline"
                :disabled="createNomenclatureSaving"
                @click="showCreateNomenclatureModal = false"
              >
                Скасувати
              </UButton>
              <UButton
                :loading="createNomenclatureSaving"
                @click="submitCreateNomenclature"
              >
                Створити та додати
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import { TextAlign } from "@tiptap/extension-text-align";
import WarehousePickerModal from "~/components/tenders/WarehousePickerModal.vue";
import { TENDER_STAGE_ITEMS } from "~/domains/tenders/tenders.constants";
import type {
  TenderConditionTemplate,
  TenderProtocolPreviewPayload,
} from "~/domains/tenders/tenders.types";

const TenderDeferredModals = defineAsyncComponent(
  () => import("~/components/tenders/TenderDeferredModals.vue"),
);

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Тендер на закупівлю" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));
const isSales = false;
const protocolPdfDownloadUrl = computed(
  () => `/api/procurement-tenders/${tenderId.value}/protocol-pdf/?download=1`,
);
const tendersUC = useTendersUseCases();
const { fetch } = useApi();
const { me } = useMe();
const myCompanyId = computed(
  () =>
    (me.value as { memberships?: Array<{ company?: { id?: number } }> })
      ?.memberships?.[0]?.company?.id ?? null,
);
const isParticipant = computed(
  () =>
    tender.value &&
    myCompanyId.value != null &&
    Number(tender.value.company) !== myCompanyId.value,
);

const tender = ref<any | null>(null);
const loading = ref(true);
const saving = ref(false);
const acceptanceTimerNowMs = ref(Date.now());
let acceptanceTimerInterval: ReturnType<typeof setInterval> | null = null;
const tourOptions = ref<{ value: number; label: string }[]>([]);
const prepTab = ref<"positions" | "criteria">("positions");
const prepTabs = [
  { label: "Позиції", value: "positions" },
  { label: "Критерії", value: "criteria" },
];

const generalTermsEditorToolbarItems = [
  [
    { kind: "mark", mark: "bold", icon: "i-lucide-bold" },
    { kind: "mark", mark: "italic", icon: "i-lucide-italic" },
    { kind: "mark", mark: "underline", icon: "i-lucide-underline" },
  ],
  [
    {
      icon: "i-lucide-list",
      tooltip: { text: "Lists" },
      content: { align: "start" },
      items: [
        { kind: "bulletList", icon: "i-lucide-list", label: "Bullet List" },
        {
          kind: "orderedList",
          icon: "i-lucide-list-ordered",
          label: "Ordered List",
        },
      ],
    },
  ],
  [
    {
      icon: "i-lucide-align-justify",
      tooltip: { text: "Text Align" },
      content: { align: "end" },
      items: [
        {
          kind: "textAlign",
          align: "left",
          icon: "i-lucide-align-left",
          label: "Align Left",
        },
        {
          kind: "textAlign",
          align: "center",
          icon: "i-lucide-align-center",
          label: "Align Center",
        },
        {
          kind: "textAlign",
          align: "right",
          icon: "i-lucide-align-right",
          label: "Align Right",
        },
        {
          kind: "textAlign",
          align: "justify",
          icon: "i-lucide-align-justify",
          label: "Align Justify",
        },
      ],
    },
  ],
];

// Параметри цінового критерія (значення value з опцій)
const priceCriterionVat = ref<string | undefined>(undefined);
const priceCriterionVatPercent = ref("");
const priceCriterionDelivery = ref<string | undefined>(undefined);
const vatOptions = [
  { value: "with_vat", label: "з ПДВ" },
  { value: "without_vat", label: "без ПДВ" },
];
const deliveryOptions = [
  {
    value: "with_delivery",
    label: "із урахуванням доставки",
  },
  {
    value: "without_delivery",
    label: "без урахування доставки",
  },
];

// Критерії з довідника та додані до тендера
const referenceCriteria = ref<any[]>([]);
const tenderCriteria = ref<any[]>([]);
const referenceAttributes = ref<any[]>([]);
const tenderAttributes = ref<any[]>([]);
const criteriaSearch = ref("");
const attributeSearch = ref("");
const categorySearch = ref("");
const expenseSearch = ref("");
const branchSearch = ref("");
const departmentSearch = ref("");
const nomenclatureSearch = ref("");
const selectedNomenclatureId = ref<number | null>(null);
const selectedAttributeId = ref<number | null>(null);
const activeWarehousePositionId = ref<number | null>(null);
const loadingNomenclatures = ref(false);
const loadingReferenceAttributes = ref(false);
const loadingWarehouses = ref(false);
const tenderPositions = ref<any[]>([]);
const availableWarehouses = ref<any[]>([]);
const usesPositionWarehouses = ref(false);
const showWarehousePickerModal = ref(false);
let tenderPositionLocalKeyCounter = 0;

function nextTenderPositionLocalKey() {
  tenderPositionLocalKeyCounter += 1;
  return `new-${tenderPositionLocalKeyCounter}`;
}

const warehouseTypeForPositions = computed(() =>
  isSales ? "shipment" : "delivery",
);
const isOnlineAuctionConductType = computed(
  () => (form.conduct_type ?? tender.value?.conduct_type) === "online_auction",
);
const isClassicAuctionMode = computed(
  () =>
    isOnlineAuctionConductType.value &&
    String(form.auction_model ?? tender.value?.auction_model) ===
      "classic_auction",
);
/** Позиції для відображення: з API (tender.positions) або локальний ref (для власника після loadTender). */
const displayTenderPositions = computed(() => {
  const raw = tender.value?.positions;
  if (Array.isArray(raw) && raw.length > 0) {
    return raw.map((p: any) => ({
      id: p.id,
      nomenclature_id: p.nomenclature_id ?? p.nomenclature,
      name: p.name,
      unit_name: p.unit_name ?? "",
      position_local_key: p.position_local_key ?? p.id ?? null,
      quantity: p.quantity ?? 1,
      description: p.description ?? "",
      warehouse_id: p.warehouse_id ?? p.warehouse ?? null,
      warehouse_name: p.warehouse_name ?? "",
      warehouse_full_address: p.warehouse_full_address ?? "",
      warehouse_region: p.warehouse_region ?? "",
      warehouse_type: p.warehouse_type ?? "",
      warehouse_type_label: p.warehouse_type_label ?? "",
      start_price: p.start_price ?? null,
      min_bid_step: p.min_bid_step ?? null,
      max_bid_step: p.max_bid_step ?? null,
      attribute_values:
        p.attribute_values && typeof p.attribute_values === "object"
          ? { ...p.attribute_values }
          : {},
      winner_proposal_id: p.winner_proposal_id ?? null,
      winner_supplier_name: p.winner_supplier_name ?? null,
      winner_price: p.winner_price ?? null,
      winner_criterion_values:
        p.winner_criterion_values &&
        typeof p.winner_criterion_values === "object"
          ? { ...p.winner_criterion_values }
          : {},
    }));
  }
  return tenderPositions.value;
});
const availableNomenclatures = ref<any[]>([]);

const showPublishModal = ref(false);
const publishStartDate = ref("");
const publishEndDate = ref("");
const publishStartTime = ref("");
const publishEndTime = ref("");
const plannedStartDate = ref("");
const plannedEndDate = ref("");
const plannedStartTime = ref("");
const plannedEndTime = ref("");
const timingStartDate = ref("");
const timingEndDate = ref("");
const timingStartTime = ref("");
const timingEndTime = ref("");
const timingComment = ref("");
const showProtocolModal = ref(false);
const protocolPreview = ref<TenderProtocolPreviewPayload | null>(null);
const protocolPreviewLoading = ref(false);
const protocolPreviewError = ref("");
const showApprovalJournalModal = ref(false);
const showApprovalActionModal = ref(false);
const approvalActionSaving = ref(false);
const pendingApprovalAction = ref<"approved" | "rejected">("approved");
const approvalActionComment = ref("");
const approvalJournalRows = ref<any[]>([]);
const approvalRoutePayload = ref<any | null>(null);
const isReadOnlyApprover = ref(false);
const showApprovalSubmitModal = ref(false);
const approvalSubmitComment = ref("");
const approvalSubmitSaving = ref(false);
const showTimingModal = ref(false);
type DecisionMode = "winner" | "cancel" | "next_round";
const decisionModeOptions: { value: DecisionMode; label: string }[] = [
  { value: "winner", label: "Закрити із переможцями" },
  { value: "next_round", label: "Перенести на наступний тур" },
  { value: "cancel", label: "Скасувати" },
];
const showDecisionModal = ref(false);
const selectedDecisionMode = ref<DecisionMode | null>(null);
const decisionJustification = ref("");
const showDecisionJustificationField = computed(
  () =>
    selectedDecisionMode.value === "winner" ||
    selectedDecisionMode.value === "cancel",
);
const decisionModeSelectableOptions = computed(() =>
  submittedDecisionProposals.value.length > 0
    ? decisionModeOptions
    : decisionModeOptions.filter((item) => item.value !== "winner"),
);
const showResumeAcceptanceModal = ref(false);
const resumeAcceptanceForm = reactive({ start_at: "", end_at: "" });
const resumeAcceptanceStartDate = ref("");
const resumeAcceptanceEndDate = ref("");
const resumeAcceptanceStartTime = ref("");
const resumeAcceptanceEndTime = ref("");
const resumeAcceptanceSaving = ref(false);
const showWinnerModal = ref(false);
const showInvitationPanel = ref(false);
const showInviteByEmailModal = ref(false);
const showAcceptanceInvitationsModal = ref(false);
const showConditionTemplateModal = ref(false);
const conditionTemplates = ref<TenderConditionTemplate[]>([]);
const conditionTemplatesLoading = ref(false);
const showAttachedFilesModal = ref(false);
const showProposalsModal = ref(false);
const showParticipantProposalModal = ref(false);
const selectedParticipantProposal = ref<any | null>(null);
const attachedFilesList = ref<
  {
    id: number;
    name?: string;
    file_url?: string;
    uploaded_at?: string;
    uploaded_by_display?: string;
    visible_to_participants?: boolean;
  }[]
>([]);
const attachedFilesLoading = ref(false);
const attachedFilesUploading = ref(false);
const attachedFilesVisibleToParticipants = ref(true);
const showNomenclaturePickerModal = ref(false);
const showAttributePickerModal = ref(false);
const showCreateAttributeModal = ref(false);
const showCreateNomenclatureModal = ref(false);
const createNomenclatureForm = reactive({
  name: "",
  unit: null as number | null,
});
const createNomenclatureSaving = ref(false);
const createAttributeSaving = ref(false);
const createNomenclatureUnits = ref<
  { id: number; name_ua?: string; short_name_ua?: string; name_en?: string }[]
>([]);
const createAttributeForm = reactive({
  name: "",
  type: "text" as "text" | "numeric" | "date",
  category: null as number | null,
  is_required: false,
  options: {
    numeric_choices: [] as (number | null)[],
    text_choices: [] as string[],
  },
});
const timingForm = reactive({ start_at: "", end_at: "" });

// Запрошення учасників: контрагенти та email
const suppliersUC = useSuppliersUseCases();
const invitationContractors = ref<
  Array<{
    id: number;
    supplier_company?: {
      id: number;
      name?: string;
      edrpou?: string;
      cpv_categories?: Array<{ id: number; label?: string }>;
    };
  }>
>([]);
const invitationCpvFilterIds = ref<number[]>([]);
const invitationCpvLabelsById = ref<Record<number, string>>({});
const invitationCpvSearchTerm = ref("");
const cpvWithCompaniesList = ref<
  Array<{ id: number; cpv_code: string; name_ua: string; label: string }>
>([]);
const cpvWithCompaniesLoading = ref(false);
const selectedCpvIdsForInvite = ref<number[]>([]);
const cpvWithCompaniesPage = ref(1);
const cpvWithCompaniesPageSize = 10;
const invitationContractorSearch = ref("");
const invitationSupplierCpvFilterIds = ref<number[]>([]);
const invitationSupplierPage = ref(1);
const invitationSupplierPageSize = 10;
const selectedContractorCompanyIds = ref<number[]>([]);
const invitedCompanies = ref<
  Array<{ id: number; name?: string; edrpou?: string }>
>([]);
const invitedEmails = ref<string[]>([]);
const inviteByEmailText = ref("");
const inviteByEmailFileInput = ref<HTMLInputElement | null>(null);

// Тільки ті коди CPV, за якими зареєстровані контрагенти
const createNomenclatureUnitOptions = computed(() =>
  createNomenclatureUnits.value.map((u) => ({
    value: u.id,
    label: u.short_name_ua || u.name_ua || u.name_en || String(u.id),
  })),
);
const attributeTypeOptions = [
  { value: "text", label: "Текстовий" },
  { value: "numeric", label: "Числовий" },
  { value: "date", label: "Дата" },
];
const attributeCategoryOptions = computed(() => [
  { value: null, label: "Без категорії" },
  ...flattenTree(categoryTree.value),
]);
function createAttributeOptionsForType(type: "text" | "numeric" | "date") {
  if (type === "numeric") {
    return {
      numeric_choices: [] as (number | null)[],
      text_choices: [] as string[],
    };
  }
  if (type === "text") {
    return {
      numeric_choices: [] as (number | null)[],
      text_choices: [] as string[],
    };
  }
  return {
    numeric_choices: [] as (number | null)[],
    text_choices: [] as string[],
  };
}
watch(
  () => createAttributeForm.type,
  (type) => {
    createAttributeForm.options = createAttributeOptionsForType(type);
  },
);

const invitationCpvOptions = computed(() => {
  const set = new Map<number, string>();
  for (const rel of invitationContractors.value) {
    const cats = rel.supplier_company?.cpv_categories ?? [];
    for (const c of cats) {
      if (c.id != null && !set.has(c.id))
        set.set(c.id, c.label ?? `CPV ${c.id}`);
    }
  }
  return Array.from(set.entries()).map(([id, label]) => ({ id, label }));
});

// CPV з зареєстрованими компаніями (системні) — фільтр по пошуку та пагінація
const cpvWithCompaniesFiltered = computed(() => {
  const list = cpvWithCompaniesList.value;
  const q = (invitationCpvSearchTerm.value || "").trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    (item) =>
      (item.label || "").toLowerCase().includes(q) ||
      (item.cpv_code || "").toLowerCase().includes(q) ||
      (item.name_ua || "").toLowerCase().includes(q),
  );
});

const cpvWithCompaniesTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil(cpvWithCompaniesFiltered.value.length / cpvWithCompaniesPageSize),
  ),
);

const cpvWithCompaniesPageList = computed(() => {
  const list = cpvWithCompaniesFiltered.value;
  const start = (cpvWithCompaniesPage.value - 1) * cpvWithCompaniesPageSize;
  return list.slice(start, start + cpvWithCompaniesPageSize);
});

function toggleCpvForInvite(id: number) {
  const arr = selectedCpvIdsForInvite.value;
  const i = arr.indexOf(id);
  if (i >= 0) {
    selectedCpvIdsForInvite.value = arr.filter((_, j) => j !== i);
  } else {
    selectedCpvIdsForInvite.value = [...arr, id];
  }
}

function inviteOneCpv(id: number) {
  if (invitationCpvFilterIds.value.includes(id)) return;
  invitationCpvFilterIds.value = [...invitationCpvFilterIds.value, id];
}

function inviteSelectedCpv() {
  const ids = selectedCpvIdsForInvite.value;
  const existing = new Set(invitationCpvFilterIds.value);
  for (const id of ids) {
    if (!existing.has(id)) {
      existing.add(id);
      invitationCpvFilterIds.value = [...invitationCpvFilterIds.value, id];
    }
  }
  selectedCpvIdsForInvite.value = [];
}

function removeInvitedCpv(id: number) {
  invitationCpvFilterIds.value = invitationCpvFilterIds.value.filter(
    (x) => x !== id,
  );
}

function onInvitationCpvIdsUpdate(ids: Array<number | string>) {
  invitationCpvFilterIds.value = (ids || [])
    .map((id) => Number(id))
    .filter((id) => Number.isInteger(id) && id > 0);
}

function onInvitationCpvLabelsUpdate(labels: string[]) {
  const next = { ...invitationCpvLabelsById.value };
  for (let i = 0; i < invitationCpvFilterIds.value.length; i++) {
    const id = invitationCpvFilterIds.value[i];
    const label = (labels?.[i] || "").trim();
    if (label && !/^#\d+$/.test(label)) next[id] = label;
  }
  invitationCpvLabelsById.value = next;
}

// Фільтр постачальників у області 1: по назві/коду та по CPV
const invitationSupplierListFiltered = computed(() => {
  let list = invitationContractors.value;
  const q = (invitationContractorSearch.value || "").trim().toLowerCase();
  if (q) {
    list = list.filter((rel) => {
      const name = (rel.supplier_company?.name ?? "").toLowerCase();
      const edrpou = (rel.supplier_company?.edrpou ?? "").toLowerCase();
      return name.includes(q) || edrpou.includes(q);
    });
  }
  const cpvIds = invitationSupplierCpvFilterIds.value;
  if (cpvIds.length) {
    const set = new Set(cpvIds);
    list = list.filter((rel) => {
      const cats = rel.supplier_company?.cpv_categories ?? [];
      return cats.some((c) => set.has(c.id));
    });
  }
  return list;
});

const invitationSupplierTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil(
      invitationSupplierListFiltered.value.length / invitationSupplierPageSize,
    ),
  ),
);

const invitationSupplierPageList = computed(() => {
  const list = invitationSupplierListFiltered.value;
  const start = (invitationSupplierPage.value - 1) * invitationSupplierPageSize;
  return list.slice(start, start + invitationSupplierPageSize);
});

function toggleContractorSelection(companyId: number | undefined) {
  if (companyId == null) return;
  const arr = selectedContractorCompanyIds.value;
  const i = arr.indexOf(companyId);
  if (i >= 0) {
    selectedContractorCompanyIds.value = arr.filter((_, j) => j !== i);
  } else {
    selectedContractorCompanyIds.value = [...arr, companyId];
  }
}

function invitationCpvLabelById(id: number): string {
  if (invitationCpvLabelsById.value[id])
    return invitationCpvLabelsById.value[id];
  const tenderCpv = Array.isArray((tender.value as any)?.cpv_categories)
    ? (tender.value as any).cpv_categories.find(
        (c: any) => Number(c?.id) === Number(id),
      )
    : null;
  const tenderLabel = tenderCpv
    ? tenderCpv.label ||
      `${tenderCpv.cpv_code || ""} - ${tenderCpv.name_ua || ""}`.trim()
    : undefined;
  return (
    invitationCpvOptions.value.find((o) => o.id === id)?.label ??
    cpvWithCompaniesList.value.find((c) => c.id === id)?.label ??
    tenderLabel ??
    `#${id}`
  );
}

const invitationCpvSelectedLabels = computed(() =>
  invitationCpvFilterIds.value.map((id) => invitationCpvLabelById(id)),
);

function inviteOneContractor(
  rel: (typeof invitationContractors.value)[number],
) {
  const cid = rel.supplier_company?.id;
  if (cid == null) return;
  if (invitedCompanies.value.some((c) => c.id === cid)) return;
  invitedCompanies.value.push({
    id: cid,
    name: rel.supplier_company?.name,
    edrpou: rel.supplier_company?.edrpou,
  });
}

function inviteSelectedContractors() {
  const ids = selectedContractorCompanyIds.value;
  const existingIds = new Set(invitedCompanies.value.map((c) => c.id));
  for (const rel of invitationContractors.value) {
    const cid = rel.supplier_company?.id;
    if (cid != null && ids.includes(cid) && !existingIds.has(cid)) {
      invitedCompanies.value.push({
        id: cid,
        name: rel.supplier_company?.name,
        edrpou: rel.supplier_company?.edrpou,
      });
      existingIds.add(cid);
    }
  }
  selectedContractorCompanyIds.value = [];
}

function removeInvitedCompany(index: number) {
  invitedCompanies.value = invitedCompanies.value.filter((_, i) => i !== index);
}

function removeInvitedEmail(index: number) {
  invitedEmails.value = invitedEmails.value.filter((_, i) => i !== index);
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
function parseEmailsFromText(text: string): string[] {
  const lines = (text || "")
    .split(/[\r\n]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const line of lines) {
    if (EMAIL_REGEX.test(line) && !seen.has(line)) {
      seen.add(line);
      out.push(line);
    }
  }
  return out;
}

async function loadInvitationContractors() {
  const { data } = await suppliersUC.getSupplierRelations();
  invitationContractors.value = (data ?? []).map((r: any) => ({
    id: r.id,
    supplier_company: r.supplier_company
      ? {
          id: r.supplier_company.id,
          name: r.supplier_company.name,
          edrpou: r.supplier_company.edrpou,
          cpv_categories: r.supplier_company.cpv_categories ?? [],
        }
      : undefined,
  }));
}

function submitInviteByEmail() {
  const parsed = parseEmailsFromText(inviteByEmailText.value);
  for (const email of parsed) {
    if (!invitedEmails.value.includes(email)) invitedEmails.value.push(email);
  }
  inviteByEmailText.value = "";
  showInviteByEmailModal.value = false;
}

function onInviteByEmailFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input?.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result ?? "");
    const parsed = parseEmailsFromText(text);
    for (const email of parsed) {
      if (!invitedEmails.value.includes(email)) invitedEmails.value.push(email);
    }
    input.value = "";
  };
  reader.readAsText(file, "UTF-8");
}

watch(showInvitationPanel, async (open) => {
  if (open && !isParticipant.value) {
    if (invitationContractors.value.length === 0)
      await loadInvitationContractors();
    if (cpvWithCompaniesList.value.length === 0) {
      cpvWithCompaniesLoading.value = true;
      const { data } = await tendersUC.getCpvWithCompanies();
      cpvWithCompaniesList.value = Array.isArray(data) ? data : [];
      cpvWithCompaniesLoading.value = false;
    }
    const cpvIds = form.cpv_ids ?? [];
    const allowedCpvIds = new Set(invitationCpvOptions.value.map((o) => o.id));
    if (cpvIds.length && allowedCpvIds.size) {
      invitationCpvFilterIds.value = cpvIds.filter((id) =>
        allowedCpvIds.has(id),
      );
    }
  }
});

watch(
  () => invitationSupplierListFiltered.value.length,
  () => {
    const maxPage = invitationSupplierTotalPages.value;
    if (invitationSupplierPage.value > maxPage) {
      invitationSupplierPage.value = maxPage;
    }
  },
);

watch(
  () => cpvWithCompaniesFiltered.value.length,
  () => {
    const maxPage = cpvWithCompaniesTotalPages.value;
    if (cpvWithCompaniesPage.value > maxPage) {
      cpvWithCompaniesPage.value = maxPage;
    }
  },
);

const decisionProposals = ref<any[]>([]);
const decisionProposalsFullLoaded = ref(false);
const decisionProposalsDeltaCursor = ref<string | null>(null);
const decisionProposalsIdleStreak = ref(0);
const submittedDecisionProposalsAll = computed(() =>
  decisionProposals.value.filter((proposal) => Boolean(proposal?.submitted_at)),
);
const submittedDecisionProposals = computed(() =>
  submittedDecisionProposalsAll.value.filter(
    (proposal) => !proposal?.disqualified_at,
  ),
);
const acceptanceTab = ref<"suppliers" | "positions" | "history">("suppliers");
const acceptanceBidHistoryPositionId = ref<number | null>(null);
const acceptanceBidHistory = ref<any[]>([]);
const acceptanceBidHistoryLoading = ref(false);
const showParticipantChatModal = ref(false);
const showOrganizerChatModal = ref(false);
const chatThreads = ref<any[]>([]);
const chatMessages = ref<any[]>([]);
const chatDraft = ref("");
const chatSending = ref(false);
const selectedChatSupplierId = ref<number | null>(null);
const showProposalChangeReportModal = ref(false);
const proposalChangeReport = ref<any[]>([]);
const proposalChangeReportLoading = ref(false);
const showDisqualificationModal = ref(false);
const disqualificationRows = ref<any[]>([]);
const disqualificationSaving = ref(false);
const showDeferredTenderModals = computed(
  () =>
    showProtocolModal.value ||
    showProposalsModal.value ||
    showParticipantProposalModal.value ||
    showParticipantChatModal.value ||
    showOrganizerChatModal.value ||
    showProposalChangeReportModal.value ||
    showDisqualificationModal.value ||
    showAttachedFilesModal.value,
);
let chatPollInterval: ReturnType<typeof setInterval> | null = null;
const isOnlineAuctionTender = computed(
  () => tender.value?.conduct_type === "online_auction",
);
const acceptanceTabItems = computed(() => {
  const items = [
    { value: "suppliers", label: "Пропозиції контрагентів" },
    { value: "positions", label: "Пропозиції попозиційно" },
  ];
  if (isOnlineAuctionTender.value) {
    items.push({ value: "history", label: "Історія ставок" });
  }
  return items;
});
const acceptanceBidHistoryPositionOptions = computed(() =>
  displayTenderPositions.value.map((pos: any) => ({
    value: Number(pos.id),
    label: pos.name || `Позиція ${pos.id}`,
  })),
);
const decisionMarketModeOptions = [
  { value: "first_tour", label: "Першого туру" },
  { value: "current_tour", label: "Поточного туру" },
];
const decisionMarketMode = ref<"first_tour" | "current_tour">("first_tour");
const firstTourMarketByPositionId = ref<Record<number, number | null>>({});
const realtimeTuning = useTenderRealtimeTuning({
  proposalCount: computed(() => decisionProposals.value.length),
  idleStreak: decisionProposalsIdleStreak,
});
const REALTIME_INCREMENTAL_SYNC_CHUNK_SIZE = realtimeTuning.chunkSize;
const REALTIME_MAX_INCREMENTAL_SYNC_IDS = realtimeTuning.maxIncrementalIds;
const REALTIME_DELTA_SYNC_IDS_THRESHOLD = realtimeTuning.deltaSyncIdsThreshold;
const organizerRealtimeSyncMs = realtimeTuning.organizerSyncMs;
const organizerBurstRealtimeSyncMs = realtimeTuning.organizerBurstSyncMs;
const organizerBurstPendingProposalIdsThreshold =
  realtimeTuning.organizerBurstPendingThreshold;
const hiddenRealtimeSyncMs = realtimeTuning.hiddenSyncMs;
const estimatedMarketMethod = ref("arithmetic_mean");
const estimatedMarketOptions = [
  { value: "arithmetic_mean", label: "Середня арифметична" },
];
const selectedWinnerByPosition = ref<Record<number, number | null>>({});

const stageItems = TENDER_STAGE_ITEMS;

const isRegistration = computed(
  () => (tender.value?.conduct_type ?? form.conduct_type) === "registration",
);
function normalizeStageForUi(
  stage: string | undefined | null,
  conductType: string | undefined | null,
) {
  const normalizedStage = stage ?? "passport";
  return conductType === "registration" && normalizedStage === "acceptance"
    ? "decision"
    : normalizedStage;
}
const isViewingPreviousTourOnly = computed(
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
function applyRealtimeSubmittedAtUpdate(message: {
  event?: string;
  payload?: Record<string, unknown>;
}) {
  const proposalId = Number(message?.payload?.proposal_id);
  if (!Number.isInteger(proposalId) || proposalId <= 0) return false;
  if (!decisionProposals.value.length) return false;
  const currentIndex = decisionProposals.value.findIndex(
    (proposal: any) => Number(proposal?.id) === proposalId,
  );
  if (currentIndex === -1) return false;

  const submittedAtRaw = message?.payload?.submitted_at;
  const submittedAt =
    typeof submittedAtRaw === "string" && submittedAtRaw.length > 0
      ? submittedAtRaw
      : null;
  const currentProposal = decisionProposals.value[currentIndex];
  if ((currentProposal?.submitted_at ?? null) === submittedAt) return true;

  const next = [...decisionProposals.value];
  next[currentIndex] = {
    ...currentProposal,
    submitted_at: submittedAt,
  };
  decisionProposals.value = next;
  return true;
}
const acceptanceRealtime = useTenderProposalsRealtime({
  tenderId,
  isSales,
  tenderStage: computed(() => displayStage.value),
  isOnlineAuction: computed(() => true),
  isParticipant,
  eventNames: ["proposal.submitted_at.updated"],
  onEvent: (message) => applyRealtimeSubmittedAtUpdate(message),
  reload: async (changedProposalIds) => {
    await loadDecisionProposals(true, changedProposalIds);
  },
  organizerMinSyncMs: organizerRealtimeSyncMs,
  organizerBurstMinSyncMs: organizerBurstRealtimeSyncMs,
  burstPendingProposalIdsThreshold: organizerBurstPendingProposalIdsThreshold,
  hiddenTabMinSyncMs: hiddenRealtimeSyncMs,
  maxProposalIdsPerSync: REALTIME_MAX_INCREMENTAL_SYNC_IDS,
  fallbackWhenWsOfflineMs: realtimeTuning.fallbackWhenWsOfflineMs,
  pauseSyncWhenHidden: realtimeTuning.pauseSyncWhenHidden,
  syncJitterRatio: realtimeTuning.syncJitterRatio,
});
const currentProcessStage = computed(() =>
  normalizeStageForUi(
    tender.value?.stage,
    tender.value?.conduct_type ?? form.conduct_type,
  ),
);
const currentProcessIndex = computed(() =>
  STAGE_ORDER.value.indexOf(currentProcessStage.value),
);
const displayStageIndex = computed(() =>
  STAGE_ORDER.value.indexOf(displayStage.value),
);
const shouldLockPastStages = computed(() =>
  ["acceptance", "decision", "approval", "completed"].includes(
    currentProcessStage.value,
  ),
);
const isPastStageView = computed(
  () =>
    shouldLockPastStages.value &&
    displayStageIndex.value !== -1 &&
    currentProcessIndex.value !== -1 &&
    displayStageIndex.value < currentProcessIndex.value,
);
const isEditLocked = computed(
  () =>
    !!isViewingPreviousTourOnly.value ||
    isPastStageView.value ||
    isReadOnlyApprover.value ||
    currentProcessStage.value === "completed",
);
const authorHasActivePreparationTask = computed(() => {
  if (
    isParticipant.value ||
    displayStage.value !== "preparation" ||
    !isTenderAuthor.value
  ) {
    return false;
  }
  const route = approvalRoutePayload.value;
  if (!route) return false;
  if (!route.has_approvers) return true;
  return !!route.can_author_submit || !!route.can_author_publish;
});
const isViewingPreviousTour = computed(() => {
  const authorLockedByRoute =
    !isParticipant.value &&
    displayStage.value === "preparation" &&
    isTenderAuthor.value &&
    !authorHasActivePreparationTask.value;
  return isEditLocked.value || authorLockedByRoute;
});
const currentUserId = computed(
  () =>
    Number((me.value as any)?.user?.id || (me.value as any)?.id || 0) || null,
);
const isTenderAuthor = computed(
  () =>
    !!tender.value &&
    currentUserId.value != null &&
    Number(tender.value.created_by || 0) === Number(currentUserId.value),
);
const approvalRouteNodes = computed(() =>
  Array.isArray(approvalRoutePayload.value?.nodes)
    ? approvalRoutePayload.value.nodes
    : [],
);
const approvalRouteHasApprovers = computed(
  () => !!approvalRoutePayload.value?.has_approvers,
);
const approvalRouteCanAuthorSubmit = computed(
  () => !!approvalRoutePayload.value?.can_author_submit,
);
const approvalRouteStatus = computed(() =>
  String(approvalRoutePayload.value?.status || ""),
);
const approvalRouteCanAuthorPublish = computed(
  () => !!approvalRoutePayload.value?.can_author_publish,
);
const approvalRouteCanApproverAction = computed(
  () => !!approvalRoutePayload.value?.can_approver_action,
);
const approvalRouteIsCurrentUserAuthor = computed(() => {
  const userId = currentUserId.value;
  if (userId == null) return false;
  return approvalRouteNodes.value.some((node: any) => {
    if (node?.kind !== "author" || !Array.isArray(node?.users)) return false;
    return node.users.some(
      (userNode: any) => Number(userNode?.id || 0) === Number(userId),
    );
  });
});
const showApprovalRouteCard = computed(
  () =>
    !isParticipant.value &&
    (displayStage.value === "preparation" || displayStage.value === "approval"),
);
const canShowPreparationSubmitButton = computed(
  () =>
    displayStage.value === "preparation" &&
    !isParticipant.value &&
    approvalRouteHasApprovers.value &&
    (approvalRouteCanAuthorSubmit.value ||
      (approvalRouteIsCurrentUserAuthor.value &&
        ["waiting_author", "rejected"].includes(approvalRouteStatus.value))) &&
    !approvalRouteCanAuthorPublish.value &&
    !isViewingPreviousTour.value,
);
const canShowPreparationPublishButtons = computed(
  () =>
    displayStage.value === "preparation" &&
    !isParticipant.value &&
    !isRegistration.value &&
    !isViewingPreviousTour.value &&
    (!approvalRouteHasApprovers.value || approvalRouteCanAuthorPublish.value),
);
const canShowPreparationGoDecisionButton = computed(
  () =>
    displayStage.value === "preparation" &&
    !isParticipant.value &&
    isRegistration.value &&
    !isViewingPreviousTour.value &&
    (!approvalRouteHasApprovers.value || approvalRouteCanAuthorPublish.value),
);
const canShowApproverActionButtons = computed(
  () =>
    !isParticipant.value &&
    (displayStage.value === "preparation" ||
      displayStage.value === "approval") &&
    !isViewingPreviousTourOnly.value &&
    approvalRouteCanApproverAction.value,
);
const canShowAuthorApprovalButtons = computed(
  () =>
    displayStage.value === "approval" &&
    !isParticipant.value &&
    !isViewingPreviousTour.value &&
    isTenderAuthor.value &&
    !approvalRouteHasApprovers.value,
);
const canShowAcceptanceInvitationsButton = computed(() => {
  const conductType = String(tender.value?.conduct_type ?? form.conduct_type);
  return (
    displayStage.value === "acceptance" &&
    !isParticipant.value &&
    !isViewingPreviousTour.value &&
    (conductType === "rfx" || conductType === "online_auction")
  );
});

const stepperItems = computed(() => {
  const progressIndex = currentProcessIndex.value;
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
    const currentIndex = currentProcessIndex.value;
    const targetIndex = STAGE_ORDER.value.indexOf(value);
    if (
      isReadOnlyApprover.value &&
      !isParticipant.value &&
      targetIndex !== -1
    ) {
      displayStage.value = value;
      return;
    }
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
  auction_model: "classic_auction",
  publication_type: "open",
  currency: null as number | null,
  general_terms: "",
  approval_model_id: null as number | null,
});
const selectedCategoryIds = computed(() =>
  form.category ? [form.category] : [],
);
const selectedExpenseIds = computed(() =>
  form.expense_article ? [form.expense_article] : [],
);
const selectedBranchIds = computed(() => (form.branch ? [form.branch] : []));
const selectedDepartmentIds = computed(() =>
  form.department ? [form.department] : [],
);

const conductTypeOptions = computed(() => {
  // Для тендерів з типом "Реєстрація" завжди показуємо лише цей варіант
  if (isRegistration.value) {
    return [
      {
        value: "registration",
        label: "Реєстрація закупівлі",
      },
    ];
  }
  const tour = tender.value?.tour_number ?? 1;
  if (tour <= 1) {
    // Перший тур: тільки Збір пропозицій та Онлайн торги
    return [
      { value: "rfx", label: "Збір пропозицій (RFx)" },
      { value: "online_auction", label: "Онлайн торги" },
    ];
  }
  // 2-й та подальші тури: усі три варіанти
  return [
    { value: "registration", label: "Реєстрація закупівлі" },
    { value: "rfx", label: "Збір пропозицій (RFx)" },
    { value: "online_auction", label: "Онлайн торги" },
  ];
});
const publicationTypeOptions = [
  { value: "open", label: "Відкрита процедура" },
  { value: "closed", label: "Закрита процедура" },
];
const auctionModelOptions = [
  { value: "classic_auction", label: "Класичний аукціон" },
];

const categoryTree = ref<any[]>([]);
const expenseTree = ref<any[]>([]);
const branchTree = ref<any[]>([]);
const departmentTree = ref<any[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);
const categoryDisabledIds = computed(() =>
  collectDisabledTreeIds(categoryTree.value),
);
const expenseDisabledIds = computed(() =>
  collectDisabledTreeIds(expenseTree.value),
);
const branchDisabledIds = computed(() =>
  collectDisabledTreeIds(branchTree.value),
);
const departmentDisabledIds = computed(() =>
  collectDisabledTreeIds(departmentTree.value),
);
const isExpenseArticleRequired = computed(
  () => countSelectableTreeNodes(expenseTree.value) > 0,
);
const isBranchRequired = computed(
  () => countSelectableTreeNodes(branchTree.value) > 0,
);
const isDepartmentRequired = computed(
  () => countSelectableTreeNodes(departmentTree.value) > 0,
);
const availableApprovalModels = ref<any[]>([]);
let approvalModelsDebounceTimer: ReturnType<typeof setTimeout> | null = null;
const approvalModelOptions = computed(() =>
  availableApprovalModels.value.map((m: any) => ({
    value: Number(m.id),
    label: m.name || `#${m.id}`,
  })),
);
const isApprovalModelLookupReady = computed(() => {
  const categoryId = Number(form.category || 0);
  const hasCategory = Number.isInteger(categoryId) && categoryId > 0;
  const budgetRaw = form.estimated_budget;
  const hasBudget = budgetRaw != null && Number.isFinite(Number(budgetRaw));
  return hasCategory && hasBudget;
});
const isApprovalModelRequired = computed(
  () =>
    isApprovalModelLookupReady.value && approvalModelOptions.value.length > 0,
);
const selectedApprovalModelSteps = computed(() => {
  const selected = availableApprovalModels.value.find(
    (m: any) => Number(m.id) === Number(form.approval_model_id),
  );
  return Array.isArray(selected?.steps) ? selected.steps : [];
});
const approvalJournalColumns = [
  { accessorKey: "created_at", header: "Дата" },
  { accessorKey: "user_display", header: "Користувач" },
  { accessorKey: "action_label", header: "Дія" },
  { accessorKey: "comment", header: "Коментар" },
];
const positionsColumns = computed(() => {
  const base = [
    { accessorKey: "seq", header: "№", cellClass: "w-12" },
    { accessorKey: "name", header: "Назва" },
    { accessorKey: "unit_name", header: "Од. виміру" },
    { accessorKey: "quantity", header: "Кількість" },
  ];
  if (isClassicAuctionMode.value) {
    base.push(
      { accessorKey: "start_price", header: "Стартова ціна" },
      { accessorKey: "min_bid_step", header: "Мін. крок ставки" },
      { accessorKey: "max_bid_step", header: "Макс. крок ставки" },
    );
  }
  base.push({ accessorKey: "description", header: "Опис" });
  for (const attribute of tenderAttributes.value || []) {
    base.push({
      accessorKey: attributeAccessorKey(attribute.id),
      header: attribute.name || "Атрибут",
    });
  }
  base.push({ accessorKey: "attributes_add", header: "", cellClass: "w-12" });
  base.push({ accessorKey: "actions", header: "", cellClass: "w-12" });
  return base;
});

const positionsTableColumns = computed(() => {
  const base = [...positionsColumns.value];
  const quantityIndex = base.findIndex(
    (column: any) => column?.accessorKey === "quantity",
  );
  const descriptionIndex = base.findIndex(
    (column: any) => column?.accessorKey === "description",
  );

  const warehouseAddColumn = {
    accessorKey: "warehouse_add",
    header: "",
    cellClass: "w-12",
  };
  const warehouseColumn = {
    accessorKey: "warehouse",
    header: "Місце постачання",
    cellClass: "min-w-[240px]",
  };

  if (
    !usesPositionWarehouses.value &&
    !isParticipant.value &&
    !base.some((column: any) => column?.accessorKey === "warehouse_add")
  ) {
    base.splice(quantityIndex >= 0 ? quantityIndex + 1 : 0, 0, warehouseAddColumn);
  }

  const currentWarehouseAddIndex = base.findIndex(
    (column: any) => column?.accessorKey === "warehouse_add",
  );
  if (usesPositionWarehouses.value && currentWarehouseAddIndex >= 0) {
    base.splice(currentWarehouseAddIndex, 1);
  }

  const currentWarehouseIndex = base.findIndex(
    (column: any) => column?.accessorKey === "warehouse",
  );
  if (usesPositionWarehouses.value) {
    if (currentWarehouseIndex === -1) {
      const insertIndex =
        descriptionIndex >= 0
          ? base.findIndex((column: any) => column?.accessorKey === "description")
          : quantityIndex + 2;
      base.splice(insertIndex >= 0 ? insertIndex : base.length, 0, warehouseColumn);
    }
  } else if (currentWarehouseIndex >= 0) {
    base.splice(currentWarehouseIndex, 1);
  }

  return base;
});

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
  for (const p of submittedDecisionProposals.value) {
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

function hasDecisionPriceForProposal(positionId: number, proposalId: unknown) {
  const normalizedId = Number(proposalId);
  if (!Number.isInteger(normalizedId) || normalizedId <= 0) return false;
  const proposal = submittedDecisionProposals.value.find(
    (p) => Number(p?.id) === normalizedId,
  );
  if (!proposal) return false;
  const pv = getProposalPositionValue(proposal, positionId);
  const price = Number(pv?.price);
  return pv != null && !Number.isNaN(price);
}

function resolveWinnerSelectionForPosition(
  positionId: number,
  isPurchase: boolean,
  persistedProposalId?: unknown,
  hasAnyPersistedWinners = false,
) {
  const hasCurrentSelection = Object.prototype.hasOwnProperty.call(
    selectedWinnerByPosition.value,
    positionId,
  );
  const currentSelection = selectedWinnerByPosition.value[positionId];
  if (hasCurrentSelection && currentSelection == null) {
    return null;
  }
  if (hasDecisionPriceForProposal(positionId, currentSelection)) {
    return Number(currentSelection);
  }
  if (persistedProposalId == null) {
    return hasAnyPersistedWinners
      ? null
      : getBestProposalIdForPosition(positionId, isPurchase);
  }
  if (hasDecisionPriceForProposal(positionId, persistedProposalId)) {
    return Number(persistedProposalId);
  }
  return getBestProposalIdForPosition(positionId, isPurchase);
}

function decisionWinnerOptionsForPosition(positionId: number) {
  return submittedDecisionProposals.value
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

function decisionWinnerOptionsWithEmpty(positionId: number) {
  return [
    { value: null, label: "Без переможця" },
    ...decisionWinnerOptionsForPosition(positionId),
  ];
}

function setDecisionWinner(positionId: number, proposalId: number | null) {
  const next = { ...selectedWinnerByPosition.value };
  next[positionId] = proposalId != null ? Number(proposalId) : null;
  selectedWinnerByPosition.value = next;
}

const decisionMarketMetricHeader = computed(() =>
  decisionMarketMode.value === "current_tour"
    ? "Економія по орієнтовній ринковій поточного туру"
    : "Економія по орієнтовній ринковій першого туру",
);

const decisionTableColumns = computed(() => [
  { accessorKey: "name", header: "Позиція" },
  { accessorKey: "quantity_unit", header: "Кількість" },
  {
    accessorKey: "market_value",
    header: "Орієнтовна ринкова",
  },
  {
    accessorKey: "best_counterparty",
    header: "Кращий контрагент",
  },
  { accessorKey: "best_price", header: "Краща ціна" },
  {
    accessorKey: "selected_counterparty",
    header: "Контрагент що обирається",
  },
  {
    accessorKey: "selected_price",
    header: "Ціна що обирається",
  },
  { accessorKey: "price_diff", header: "Розбіжність у ціні" },
  {
    accessorKey: "economy_market",
    header: decisionMarketMetricHeader.value,
  },
]);

function formatDecimalDisplay(
  value: unknown,
  maximumFractionDigits = 4,
): string {
  const normalized = Number(String(value ?? "").replace(",", "."));
  if (!Number.isFinite(normalized)) return String(value ?? "");
  return normalized.toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  });
}

function formatNumericOrDash(value: unknown): string {
  const normalized = Number(String(value ?? "").replace(",", "."));
  if (!Number.isFinite(normalized)) return "—";
  return formatDecimalDisplay(normalized);
}

const decisionTableRows = computed(() => {
  const proposals = submittedDecisionProposals.value;
  const selected = selectedWinnerByPosition.value;
  const isPurchase = true;
  return displayTenderPositions.value.map((pos) => {
    const pvList = proposals
      .map((p) => ({ proposal: p, pv: getProposalPositionValue(p, pos.id) }))
      .filter(
        (x) =>
          x.pv != null &&
          Number(x.pv.price) !== undefined &&
          !Number.isNaN(Number(x.pv.price)),
      );
    const prices = pvList.map((x) => Number(x.pv!.price));
    const currentTourMarketPrice =
      prices.length > 0
        ? prices.reduce((a, b) => a + b, 0) / prices.length
        : null;
    const firstTourMarketPriceRaw =
      firstTourMarketByPositionId.value[Number(pos.id)];
    const firstTourMarketPrice =
      firstTourMarketPriceRaw != null &&
      Number.isFinite(Number(firstTourMarketPriceRaw))
        ? Number(firstTourMarketPriceRaw)
        : null;
    const marketPrice =
      decisionMarketMode.value === "first_tour"
        ? firstTourMarketPrice
        : currentTourMarketPrice;
    const marketValue =
      estimatedMarketMethod.value === "arithmetic_mean" && marketPrice != null
        ? formatDecimalDisplay(marketPrice)
        : marketPrice != null
          ? formatDecimalDisplay(marketPrice)
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
    const bestPriceStr =
      bestPrice != null ? formatDecimalDisplay(bestPrice) : "—";

    const hasManualSelection = Object.prototype.hasOwnProperty.call(
      selected,
      pos.id,
    );
    const selectedProposalId = hasManualSelection
      ? selected[pos.id]
      : (bestProposal?.id ?? null);
    const selectedProposal =
      selectedProposalId != null
        ? proposals.find((p) => p.id === selectedProposalId)
        : null;
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
      selectedPrice != null ? formatDecimalDisplay(selectedPrice) : "—";

    const priceDiff =
      bestPrice != null && selectedPrice != null
        ? selectedPrice - bestPrice
        : null;
    const priceDiffStr =
      priceDiff != null ? formatDecimalDisplay(priceDiff) : "—";

    const economyMarket =
      marketPrice != null && selectedPrice != null
        ? marketPrice - selectedPrice
        : null;
    const economyMarketStr =
      economyMarket != null ? formatDecimalDisplay(economyMarket) : "—";

    return {
      id: pos.id,
      name: pos.name,
      quantity_value: Number(pos.quantity),
      quantity_unit: pos.unit_name
        ? `${formatDecimalDisplay(pos.quantity)} ${pos.unit_name}`
        : formatDecimalDisplay(pos.quantity),
      market_value: marketValue,
      market_value_num: marketPrice,
      best_counterparty: bestCounterparty,
      best_price: bestPriceStr,
      best_price_num: bestPrice,
      selected_counterparty: selectedCounterparty,
      selected_price: selectedPriceStr,
      selected_price_num: selectedPrice,
      price_diff: priceDiffStr,
      economy_market: economyMarketStr,
      economy_market_num: economyMarket,
    };
  });
});

const decisionSummary = computed(() => {
  let bestTotal = 0;
  let selectedTotal = 0;
  let marketTotal = 0;

  for (const row of decisionTableRows.value as any[]) {
    const qty = Number(row?.quantity_value);
    if (!Number.isFinite(qty)) continue;

    const bestPrice = Number(row?.best_price_num);
    if (Number.isFinite(bestPrice)) {
      bestTotal += qty * bestPrice;
    }

    const selectedPrice = Number(row?.selected_price_num);
    if (Number.isFinite(selectedPrice)) {
      selectedTotal += qty * selectedPrice;
    }

    const marketPrice = Number(row?.market_value_num);
    if (Number.isFinite(marketPrice)) {
      marketTotal += qty * marketPrice;
    }
  }

  return {
    bestTotal,
    selectedTotal,
    aggregateTotal: marketTotal - selectedTotal,
  };
});

function formatDecisionSummaryAmount(value: number | null) {
  if (value == null || !Number.isFinite(value)) return "—";
  return formatDecimalDisplay(value);
}

function getApprovalPositionTotal(quantityRaw: unknown, priceRaw: unknown) {
  const quantity = Number(quantityRaw);
  const price = Number(String(priceRaw ?? "").replace(",", "."));
  if (!Number.isFinite(quantity) || !Number.isFinite(price)) return "—";
  return formatDecimalDisplay(quantity * price);
}

/** Дерево для UTree: категорії (батьки) → номенклатури (діти), формат Nuxt UI TreeItem */
const nomenclatureTreeItems = computed(() => {
  const list = availableNomenclatures.value;
  const term = (nomenclatureSearch.value || "").trim().toLowerCase();
  const filtered =
    term === ""
      ? list
      : list.filter(
          (n: any) =>
            (n.name || "").toLowerCase().includes(term) ||
            (n.unit_name || "").toLowerCase().includes(term),
        );
  if (filtered.length === 0) return [];
  const categoryId = form.category;
  const cpvIds = form.cpv_ids ?? [];
  const cpvLabels = tenderCpvLabels.value ?? [];
  let label: string;
  let id: string;
  if (categoryId !== null && categoryId !== undefined) {
    label = findCategoryNameById(categoryTree.value, categoryId) || "Категорія";
    id = `cat-${categoryId}`;
  } else if (cpvIds.length > 0 && cpvLabels.length > 0) {
    label =
      cpvLabels.length === 1 ? (cpvLabels[0] ?? "") : cpvLabels.join(", ");
    id = `cpv-${cpvIds.join("-")}`;
  } else {
    label = "Номенклатури";
    id = "nomenclatures";
  }
  const children = filtered.map((n: any) => ({
    id: n.id,
    label: `${n.name || ""}${n.unit_name ? ` (${n.unit_name})` : ""}`,
  }));
  return [{ id, label, defaultExpanded: true, children }];
});

function getNomenclatureTreeKey(item: {
  id?: number | string;
  label?: string;
}) {
  return String(item.id ?? item.label ?? "");
}

function onNomenclatureTreeSelect(
  e: unknown,
  item: { id?: number | string; children?: unknown[] },
) {
  const ev = e as {
    detail?: {
      originalEvent?: { detail?: number; preventDefault?: () => void };
    };
    preventDefault?: () => void;
  };
  const orig = ev?.detail?.originalEvent ?? ev;
  const isLeaf = item && !item.children?.length;
  const isDoubleClick = (orig as { detail?: number })?.detail === 2;
  if (isLeaf && item.id != null) {
    const numId = typeof item.id === "number" ? item.id : Number(item.id);
    if (!Number.isNaN(numId)) {
      selectedNomenclatureId.value = numId;
      if (isDoubleClick) {
        addPositionFromNomenclature(numId);
      }
    }
  } else {
    selectedNomenclatureId.value = null;
  }
  if (
    typeof (orig as { preventDefault?: () => void })?.preventDefault ===
    "function"
  )
    (orig as { preventDefault: () => void }).preventDefault();
}

function addSelectedNomenclatureFromPicker() {
  if (selectedNomenclatureId.value == null) return;
  addPositionFromNomenclature(selectedNomenclatureId.value, {
    notifyAdded: true,
  });
}

const canEditStart = computed(() => {
  if (!tender.value?.start_at) return true;
  return new Date() < new Date(tender.value.start_at);
});

const canSubmitProposal = computed(() => {
  if (!tender.value || tender.value.conduct_type !== "registration")
    return false;
  const hasPositions = tenderPositions.value.length >= 1;
  const hasPriceParams =
    !!priceCriterionVat.value &&
    !!priceCriterionDelivery.value &&
    (!isVatPercentRequired.value ||
      parseVatPercentValue(priceCriterionVatPercent.value) != null);
  return hasPositions && hasPriceParams;
});

const isVatPercentRequired = computed(
  () => priceCriterionVat.value === "with_vat",
);

function toValidCriterionId(value: unknown): number | null {
  const num = Number(value);
  if (!Number.isInteger(num) || num <= 0) return null;
  return num;
}

function normalizedCriterionIds(rawIds: unknown[]): number[] {
  const unique = new Set<number>();
  for (const rawId of rawIds || []) {
    const id = toValidCriterionId(rawId);
    if (id != null) unique.add(id);
  }
  return Array.from(unique);
}

function criterionRefId(value: any): number | null {
  if (
    value &&
    typeof value === "object" &&
    Object.prototype.hasOwnProperty.call(value, "reference_criterion_id")
  ) {
    return toValidCriterionId(value.reference_criterion_id);
  }
  return toValidCriterionId(value?.id);
}

function toValidAttributeId(value: unknown): number | null {
  const num = Number(value);
  if (!Number.isInteger(num) || num <= 0) return null;
  return num;
}

function normalizedAttributeIds(rawIds: unknown[]): number[] {
  const unique = new Set<number>();
  for (const rawId of rawIds || []) {
    const id = toValidAttributeId(rawId);
    if (id != null) unique.add(id);
  }
  return Array.from(unique);
}

function attributeAccessorKey(attributeId: number | string) {
  return `attr_${attributeId}`;
}

function ensurePositionAttributeValues(position: any): Record<string, unknown> {
  if (!position || typeof position !== "object") return {};
  if (
    !position.attribute_values ||
    typeof position.attribute_values !== "object"
  ) {
    position.attribute_values = {};
  }
  return position.attribute_values as Record<string, unknown>;
}

function filterPositionAttributeValues(values: unknown) {
  if (!values || typeof values !== "object") return {};
  const allowed = new Set(
    normalizedAttributeIds(
      (tenderAttributes.value || []).map((a: any) => a?.id),
    ).map((id) => String(id)),
  );
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(
    values as Record<string, unknown>,
  )) {
    if (!allowed.has(String(key))) continue;
    cleaned[String(key)] = value;
  }
  return cleaned;
}

function getPositionWarehouseLabel(position: any) {
  if (!position) return "";
  const name = String(position.warehouse_name || "").trim();
  const address = String(position.warehouse_full_address || "").trim();
  return name || address ? [name, address].filter(Boolean).join(" - ") : "";
}

function clearPositionWarehouse(position: any) {
  if (!position || typeof position !== "object") return;
  position.warehouse_id = null;
  position.warehouse_name = "";
  position.warehouse_full_address = "";
  position.warehouse_region = "";
  position.warehouse_type = "";
  position.warehouse_type_label = "";
}

function assignPositionWarehouse(position: any, warehouse: any) {
  if (!position || !warehouse) return;
  position.warehouse_id = warehouse.id ?? null;
  position.warehouse_name = warehouse.name ?? "";
  position.warehouse_full_address = warehouse.full_address ?? "";
  position.warehouse_region = warehouse.region ?? "";
  position.warehouse_type = warehouse.warehouse_type ?? "";
  position.warehouse_type_label = warehouse.warehouse_type_label ?? "";
}

async function loadWarehousesForPositions(force = false) {
  if (loadingWarehouses.value) return;
  if (!force && availableWarehouses.value.length > 0) return;
  loadingWarehouses.value = true;
  try {
    const { data } = await fetch("/warehouses/", {
      query: {
        warehouse_type: warehouseTypeForPositions.value,
      },
      cacheTtlMs: 60_000,
    });
    availableWarehouses.value = Array.isArray(data) ? data : [];
  } finally {
    loadingWarehouses.value = false;
  }
}

function getPositionIdentity(position: any) {
  if (position?.position_local_key != null && position.position_local_key !== "") {
    return String(position.position_local_key);
  }
  const candidate = Number(position?.id ?? position?.nomenclature_id ?? 0);
  return Number.isInteger(candidate) && candidate > 0 ? String(candidate) : null;
}

function getActiveWarehousePosition() {
  const identity = activeWarehousePositionId.value;
  if (identity == null) return null;
  return (
    tenderPositions.value.find(
      (position) => getPositionIdentity(position) === identity,
    ) || null
  );
}

const selectedWarehouseIdForActivePosition = computed(() => {
  const position = getActiveWarehousePosition();
  const warehouseId = Number(position?.warehouse_id ?? 0);
  return Number.isInteger(warehouseId) && warehouseId > 0 ? warehouseId : null;
});

async function openWarehousePickerModal(position: any) {
  if (
    !position ||
    isParticipant.value ||
    isViewingPreviousTour.value ||
    !usesPositionWarehouses.value
  ) {
    return;
  }
  const identity = getPositionIdentity(position);
  if (identity == null) return;
  activeWarehousePositionId.value = identity;
  showWarehousePickerModal.value = true;
  await loadWarehousesForPositions();
}

function onWarehouseSelected(warehouse: any) {
  const position = getActiveWarehousePosition();
  if (!position || !warehouse) return;
  assignPositionWarehouse(position, warehouse);
  showWarehousePickerModal.value = false;
}

function enablePositionWarehouses() {
  if (isParticipant.value || isViewingPreviousTour.value) return;
  usesPositionWarehouses.value = true;
  void loadWarehousesForPositions();
}

function disablePositionWarehouses() {
  if (isParticipant.value || isViewingPreviousTour.value) return;
  usesPositionWarehouses.value = false;
  for (const position of tenderPositions.value) {
    clearPositionWarehouse(position);
  }
}

const priceCriteriaAutosaveInFlight = ref(false);
const priceCriteriaAutosaveQueuedPayload = ref<Record<string, unknown> | null>(
  null,
);

async function savePriceCriteriaImmediately(payload: Record<string, unknown>) {
  if (!tender.value?.id || isParticipant.value || isViewingPreviousTour.value)
    return;
  if (!Object.keys(payload).length) return;
  if (priceCriteriaAutosaveInFlight.value) {
    priceCriteriaAutosaveQueuedPayload.value = {
      ...(priceCriteriaAutosaveQueuedPayload.value || {}),
      ...payload,
    };
    return;
  }
  priceCriteriaAutosaveInFlight.value = true;
  try {
    await patchTender(payload);
  } finally {
    priceCriteriaAutosaveInFlight.value = false;
  }
  const queued = priceCriteriaAutosaveQueuedPayload.value;
  if (queued && Object.keys(queued).length) {
    priceCriteriaAutosaveQueuedPayload.value = null;
    await savePriceCriteriaImmediately(queued);
  }
}

function onPriceCriterionVatChange(value: string | undefined) {
  priceCriterionVat.value = value;
  if (value !== "with_vat") {
    priceCriterionVatPercent.value = "";
    void savePriceCriteriaImmediately({
      price_criterion_vat: value ?? "",
      price_criterion_vat_percent: null,
    });
    return;
  }
  const vatPercent = parseVatPercentValue(priceCriterionVatPercent.value);
  if (vatPercent != null) {
    void savePriceCriteriaImmediately({
      price_criterion_vat: value ?? "",
      price_criterion_vat_percent: vatPercent,
    });
  }
}

function onPriceCriterionDeliveryChange(value: string | undefined) {
  priceCriterionDelivery.value = value;
  void savePriceCriteriaImmediately({
    price_criterion_delivery: value ?? "",
  });
}

function onPriceCriterionVatPercentBlur() {
  priceCriterionVatPercent.value = normalizeVatPercentInput(
    priceCriterionVatPercent.value,
  );
  if (!isVatPercentRequired.value) return;
  const vatPercent = parseVatPercentValue(priceCriterionVatPercent.value);
  if (vatPercent == null) return;
  void savePriceCriteriaImmediately({
    price_criterion_vat: priceCriterionVat.value ?? "",
    price_criterion_vat_percent: vatPercent,
  });
}
async function savePreparation() {
  if (!tender.value?.id) return false;
  const vatPercent = parseVatPercentValue(priceCriterionVatPercent.value);
  if (
    usesPositionWarehouses.value &&
    tenderPositions.value.some((position) => !Number(position.warehouse_id))
  ) {
    useToast().add({
      title: "Заповніть склади по позиціях",
      description:
        "Якщо поле складів увімкнене, потрібно обрати склад для кожної позиції.",
      color: "error",
    });
    return false;
  }
  if (isVatPercentRequired.value && vatPercent == null) {
    useToast().add({
      title: "Заповніть % ПДВ",
      description: "Для параметра ціни «з ПДВ» вкажіть значення від 0 до 100.",
      color: "error",
    });
    return false;
  }
  if (isClassicAuctionMode.value) {
    const hasInvalidClassicParams = tenderPositions.value.some((p) => {
      const start = Number(p.start_price);
      const minStep = Number(p.min_bid_step);
      const maxStep = Number(p.max_bid_step);
      return (
        Number.isNaN(start) ||
        Number.isNaN(minStep) ||
        Number.isNaN(maxStep) ||
        start <= 0 ||
        minStep <= 0 ||
        maxStep <= 0 ||
        minStep > maxStep
      );
    });
    if (hasInvalidClassicParams) {
      useToast().add({
        title: "Некоректні параметри класичних торгів",
        description:
          "Для кожної позиції заповніть стартову ціну, мінімальний і максимальний крок ставки (значення > 0, мін. крок <= макс. крок).",
        color: "error",
      });
      return false;
    }
  }
  const payload: Record<string, unknown> = {
    positions: tenderPositions.value.map((p) => ({
      nomenclature_id: p.nomenclature_id,
      quantity: p.quantity,
      description: p.description ?? "",
      warehouse_id: Number(p.warehouse_id) || null,
      start_price:
        p.start_price !== "" && p.start_price != null
          ? Number(p.start_price)
          : null,
      min_bid_step:
        p.min_bid_step !== "" && p.min_bid_step != null
          ? Number(p.min_bid_step)
          : null,
      max_bid_step:
        p.max_bid_step !== "" && p.max_bid_step != null
          ? Number(p.max_bid_step)
          : null,
      attribute_values: filterPositionAttributeValues(
        ensurePositionAttributeValues(p),
      ),
    })),
    criterion_ids: normalizedCriterionIds(
      (tenderCriteria.value || []).map((c: any) => criterionRefId(c)),
    ),
    price_criterion_vat: priceCriterionVat.value ?? "",
    price_criterion_vat_percent:
      isVatPercentRequired.value && vatPercent != null ? vatPercent : null,
    price_criterion_delivery: priceCriterionDelivery.value ?? "",
    uses_position_warehouses: usesPositionWarehouses.value,
    auction_model: form.auction_model,
    attribute_ids: normalizedAttributeIds(
      (tenderAttributes.value || []).map((a: any) => a?.id),
    ),
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
          : !priceCriterionVat.value ||
              !priceCriterionDelivery.value ||
              (isVatPercentRequired.value &&
                parseVatPercentValue(priceCriterionVatPercent.value) == null)
            ? "Налаштуйте параметри цінового критерію (ПДВ, % ПДВ та Доставка)."
            : "";
      alert(msg || "Неможливо відкрити подачу пропозицій.");
      return;
    }
    await navigateTo(`/cabinet/tenders/proposals/${tenderId.value}`);
  } finally {
    saving.value = false;
  }
}

function formatFileDate(iso?: string) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString("uk-UA", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("uk-UA", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

async function openParticipantProposalModal(proposal: any) {
  const proposalId = Number(proposal?.id);
  const hasFullDetails = Array.isArray(proposal?.position_values);
  if (
    Number.isInteger(proposalId) &&
    proposalId > 0 &&
    !hasFullDetails &&
    tenderId.value
  ) {
    const { data } = await tendersUC.getTenderProposalDetail(
      tenderId.value,
      proposalId,
      isSales,
      { skipLoader: true },
    );
    if (data) {
      const nextById = new Map<number, any>();
      for (const item of decisionProposals.value) {
        const id = Number(item?.id);
        if (Number.isInteger(id) && id > 0) nextById.set(id, item);
      }
      nextById.set(proposalId, data);
      decisionProposals.value = Array.from(nextById.values());
      selectedParticipantProposal.value = data;
      showParticipantProposalModal.value = true;
      return;
    }
  }
  selectedParticipantProposal.value = proposal;
  showParticipantProposalModal.value = true;
}

async function loadAttachedFiles() {
  attachedFilesLoading.value = true;
  const { data, error } = await tendersUC.getTenderFiles(
    tenderId.value,
    isSales,
  );
  attachedFilesLoading.value = false;
  if (error) {
    useToast().add({
      title: "Помилка завантаження списку файлів",
      description: error,
      color: "error",
    });
    return;
  }
  attachedFilesList.value = Array.isArray(data) ? data : [];
}

function openAttachedFilesModal() {
  showAttachedFilesModal.value = true;
}

watch(showAttachedFilesModal, (open) => {
  if (open) loadAttachedFiles();
});

watch(showNomenclaturePickerModal, async (open) => {
  if (open) {
    selectedNomenclatureId.value = null;
    nomenclatureSearch.value = "";
    await loadNomenclaturesForPreparation();
  }
});

watch(showWarehousePickerModal, (open) => {
  if (!open) activeWarehousePositionId.value = null;
});

watch(showCreateNomenclatureModal, async (open) => {
  if (open) {
    createNomenclatureForm.name = "";
    createNomenclatureForm.unit = null;
    const { data } = await tendersUC.getUnits();
    createNomenclatureUnits.value = Array.isArray(data) ? data : [];
  }
});

async function submitCreateNomenclature() {
  const name = (createNomenclatureForm.name || "").trim();
  if (!name) {
    useToast().add({
      title: "Вкажіть назву номенклатури",
      color: "error",
    });
    return;
  }
  if (createNomenclatureForm.unit == null) {
    useToast().add({
      title: "Оберіть одиницю виміру",
      color: "error",
    });
    return;
  }
  const companyId = tender.value?.company;
  if (!companyId) {
    useToast().add({
      title: "Помилка",
      description: "Тендер не привʼязаний до компанії.",
      color: "error",
    });
    return;
  }
  const cpvIds = form.cpv_ids ?? [];
  createNomenclatureSaving.value = true;
  try {
    const { data: created, error: createError } =
      await tendersUC.createNomenclature({
        company: companyId,
        name,
        unit: createNomenclatureForm.unit,
        cpv_ids: cpvIds.length ? cpvIds : undefined,
      });
    if (createError || !created?.id) {
      useToast().add({
        title: "Помилка створення номенклатури",
        description: typeof createError === "string" ? createError : "",
        color: "error",
      });
      return;
    }
    if (!tenderPositions.value.some((p) => p.nomenclature_id === created.id)) {
      tenderPositions.value.push({
        nomenclature_id: created.id,
        name: created.name || name,
        unit_name: created.unit_name || "",
        quantity: 1,
        description: "",
        warehouse_id: null,
        warehouse_name: "",
        warehouse_full_address: "",
        warehouse_region: "",
        warehouse_type: "",
        warehouse_type_label: "",
        start_price: null,
        min_bid_step: null,
        max_bid_step: null,
        attribute_values: {},
      });
    }
    if (!availableNomenclatures.value.some((n: any) => n.id === created.id)) {
      availableNomenclatures.value.push({
        id: created.id,
        name: created.name || name,
        unit_name: created.unit_name || "",
      });
    }
    showCreateNomenclatureModal.value = false;
    if (isClassicAuctionMode.value) {
      useToast().add({
        title: "Номенклатуру додано до позицій",
        description:
          "Для моделі «Онлайн торги» заповніть стартову ціну та кроки ставки перед збереженням.",
        color: "warning",
      });
    } else {
      useToast().add({
        title: "Номенклатуру створено та додано до позицій",
        color: "success",
      });
    }
  } finally {
    createNomenclatureSaving.value = false;
  }
}

async function onAttachedFilesInputChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = input?.files;
  if (!files?.length) return;
  attachedFilesUploading.value = true;
  const visible = attachedFilesVisibleToParticipants.value;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const form = new FormData();
    form.append("file", file);
    form.append("visible_to_participants", String(visible));
    const { data, error } = await tendersUC.uploadTenderFile(
      tenderId.value,
      isSales,
      form,
    );
    if (error) {
      useToast().add({
        title: "Помилка завантаження",
        description: error,
        color: "error",
      });
    } else if (data) {
      attachedFilesList.value = [data, ...attachedFilesList.value];
    }
  }
  attachedFilesUploading.value = false;
  input.value = "";
}

async function deleteAttachedFile(fileId: number) {
  const { error } = await tendersUC.deleteTenderFile(
    tenderId.value,
    isSales,
    fileId,
  );
  if (error) {
    useToast().add({
      title: "Помилка видалення",
      description: error,
      color: "error",
    });
  } else {
    attachedFilesList.value = attachedFilesList.value.filter(
      (f) => f.id !== fileId,
    );
  }
}

async function toggleFileVisibility(fileId: number, visible: boolean) {
  const { data, error } = await tendersUC.patchTenderFile(
    tenderId.value,
    isSales,
    fileId,
    {
      visible_to_participants: visible,
    },
  );
  if (error) {
    useToast().add({
      title: "Помилка оновлення",
      description: error,
      color: "error",
    });
  } else if (data) {
    const idx = attachedFilesList.value.findIndex((f) => f.id === fileId);
    if (idx !== -1)
      attachedFilesList.value[idx] = {
        ...attachedFilesList.value[idx],
        ...data,
      };
  }
}

function criterionTypeLabel(type: string) {
  const map: Record<string, string> = {
    numeric: "Числовий",
    text: "Текстовий",
    date: "Дата",
    file: "Файловий",
    boolean: "Булевий",
  };
  return map[type] ?? type;
}

function criterionApplicationLabel(
  application?: string,
  explicitLabel?: string,
) {
  const label = (explicitLabel || "").trim();
  if (label) return label;
  const map: Record<string, string> = {
    general: "Загальний",
    individual: "Індивідуальний",
  };
  const key = application || "individual";
  return map[key] ?? key;
}

const tenderCriteriaGeneral = computed(() =>
  (tenderCriteria.value || []).filter(
    (c: any) => (c.application || "individual") === "general",
  ),
);
const tenderCriteriaIndividual = computed(() =>
  (tenderCriteria.value || []).filter(
    (c: any) => (c.application || "individual") === "individual",
  ),
);

const loadingReferenceCriteria = ref(false);
const showCreateCriterionModal = ref(false);
const createCriterionForm = reactive({
  name: "",
  type: "numeric",
  application: "individual",
  is_required: false,
  options: {} as Record<string, unknown>,
});
const createCriterionSaving = ref(false);
const criterionTypeOptions = [
  { value: "numeric", label: "Числовий" },
  { value: "text", label: "Текстовий" },
  { value: "date", label: "Дата" },
  { value: "file", label: "Файловий" },
  { value: "boolean", label: "Булевий (Так/Ні)" },
];
const criterionApplicationOptions = [
  { value: "general", label: "Загальний" },
  { value: "individual", label: "Індивідуальний" },
];

function openCreateCriterionModal() {
  createCriterionForm.name = "";
  createCriterionForm.type = "numeric";
  createCriterionForm.application = "individual";
  createCriterionForm.is_required = false;
  createCriterionForm.options = {};
  showCreateCriterionModal.value = true;
}

async function saveCreateCriterion() {
  const name = (createCriterionForm.name || "").trim();
  if (!name) {
    useToast().add({
      title: "Вкажіть назву критерія",
      color: "error",
    });
    return;
  }
  const companyId = tender.value?.company;
  if (!companyId) {
    useToast().add({
      title: "Тендер не привʼязаний до компанії",
      color: "error",
    });
    return;
  }
  createCriterionSaving.value = true;
  try {
    const { data: created, error } = await tendersUC.createTenderCriterion({
      company: companyId,
      name,
      type: createCriterionForm.type,
      tender_type: "procurement",
      application: createCriterionForm.application || "individual",
      is_required: Boolean(createCriterionForm.is_required),
      options: createCriterionForm.options || {},
    });
    if (error || !created?.id) {
      useToast().add({
        title: "Помилка створення критерія",
        description:
          typeof error === "string"
            ? error
            : "Критерій з такою назвою та типом вже існує.",
        color: "error",
      });
      return;
    }
    const newIds = normalizedCriterionIds([
      ...(tenderCriteria.value || []).map((c: any) => criterionRefId(c)),
      created.id,
    ]);
    const ok = await patchTender({ criterion_ids: newIds });
    if (ok && Array.isArray(tender.value?.criteria)) {
      tenderCriteria.value = tender.value.criteria;
    } else {
      tenderCriteria.value = [
        ...(tenderCriteria.value || []),
        {
          id: created.id,
          name: created.name,
          type: created.type,
          application: created.application ?? "individual",
          is_required: Boolean(created.is_required),
        },
      ];
    }
    showCreateCriterionModal.value = false;
    useToast().add({
      title: "Критерій створено та додано до тендера",
      color: "success",
    });
    await loadReferenceCriteria();
  } finally {
    createCriterionSaving.value = false;
  }
}

/** Дерево для UTree: один батьківський вузол «Критерії», діти — критерії з довідника (з фільтром пошуку) */
const criteriaTreeItems = computed(() => {
  const list = referenceCriteria.value;
  const term = (criteriaSearch.value || "").trim().toLowerCase();
  const filtered =
    term === ""
      ? list
      : list.filter(
          (c: any) =>
            (c.name || "").toLowerCase().includes(term) ||
            (criterionTypeLabel(c.type) || "").toLowerCase().includes(term),
        );
  if (filtered.length === 0) return [];
  const children = filtered.map((c: any) => ({
    id: c.id,
    label: `${c.name || ""} (${criterionTypeLabel(c.type)})`,
  }));
  return [
    {
      id: "criteria-root",
      label: "Критерії",
      defaultExpanded: true,
      children,
    },
  ];
});

function getCriteriaTreeKey(item: { id?: number | string; label?: string }) {
  return String(item.id ?? item.label ?? "");
}

function onCriteriaTreeSelect(
  e: unknown,
  item: { id?: number | string; children?: unknown[] },
) {
  const ev = e as {
    detail?: {
      originalEvent?: { detail?: number; preventDefault?: () => void };
    };
    preventDefault?: () => void;
  };
  const orig = ev?.detail?.originalEvent ?? ev;
  const isLeaf = item && !item.children?.length;
  const isDoubleClick = (orig as { detail?: number })?.detail === 2;
  if (isLeaf && isDoubleClick && item.id != null) {
    const numId = typeof item.id === "number" ? item.id : Number(item.id);
    if (!Number.isNaN(numId)) addCriterionFromTree(numId);
  }
  if (
    typeof (orig as { preventDefault?: () => void })?.preventDefault ===
    "function"
  )
    (orig as { preventDefault: () => void }).preventDefault();
}

/** Додати критерій з довідника (подвійний клік у лівій панелі). Якщо вже є — нічого не робимо. */
const tenderCriteriaAutosaveInFlight = ref(false);
const tenderCriteriaAutosaveQueued = ref(false);

function currentTenderCriterionIds() {
  return normalizedCriterionIds(
    (tenderCriteria.value || []).map((c: any) => criterionRefId(c)),
  );
}

async function persistTenderCriteriaImmediately() {
  if (!tender.value?.id || isParticipant.value || isViewingPreviousTour.value)
    return false;
  if (tenderCriteriaAutosaveInFlight.value) {
    tenderCriteriaAutosaveQueued.value = true;
    return true;
  }
  tenderCriteriaAutosaveInFlight.value = true;
  const ok = await patchTender({ criterion_ids: currentTenderCriterionIds() });
  tenderCriteriaAutosaveInFlight.value = false;
  if (tenderCriteriaAutosaveQueued.value) {
    tenderCriteriaAutosaveQueued.value = false;
    await persistTenderCriteriaImmediately();
  }
  return ok;
}
async function addCriterionFromTree(criterionId: number) {
  if (isViewingPreviousTour.value) return;
  const normalizedId = toValidCriterionId(criterionId);
  if (normalizedId == null) return;
  if (tenderCriteria.value.some((c) => criterionRefId(c) === normalizedId))
    return;
  const c = referenceCriteria.value.find(
    (x: any) => toValidCriterionId(x?.id) === normalizedId,
  );
  if (!c) return;
  const prev = [...tenderCriteria.value];
  tenderCriteria.value = [...tenderCriteria.value, c];
  const ok = await persistTenderCriteriaImmediately();
  if (!ok) tenderCriteria.value = prev;
}

async function loadReferenceCriteria() {
  loadingReferenceCriteria.value = true;
  try {
    const { data } = await tendersUC.getTenderCriteriaByType("procurement");
    referenceCriteria.value = Array.isArray(data) ? data : [];
  } finally {
    loadingReferenceCriteria.value = false;
  }
}

const attributesTreeItems = computed(() => {
  const list = referenceAttributes.value;
  const term = (attributeSearch.value || "").trim().toLowerCase();
  const filtered =
    term === ""
      ? list
      : list.filter(
          (a: any) =>
            (a.name || "").toLowerCase().includes(term) ||
            String(a.type || "")
              .toLowerCase()
              .includes(term),
        );
  if (filtered.length === 0) return [];
  const children = filtered.map((a: any) => ({
    id: a.id,
    label: `${a.name || ""} (${a.type || ""})`,
  }));
  return [
    {
      id: "attributes-root",
      label: "Атрибути",
      defaultExpanded: true,
      children,
    },
  ];
});

function getAttributesTreeKey(item: { id?: number | string; label?: string }) {
  return String(item.id ?? item.label ?? "");
}

function onAttributesTreeSelect(
  e: unknown,
  item: { id?: number | string; children?: unknown[] },
) {
  const ev = e as {
    detail?: {
      originalEvent?: { detail?: number; preventDefault?: () => void };
    };
    preventDefault?: () => void;
  };
  const orig = ev?.detail?.originalEvent ?? ev;
  const isLeaf = item && !item.children?.length;
  const isDoubleClick = (orig as { detail?: number })?.detail === 2;
  if (isLeaf && item.id != null) {
    const numId = typeof item.id === "number" ? item.id : Number(item.id);
    if (!Number.isNaN(numId)) {
      selectedAttributeId.value = numId;
      if (isDoubleClick) void addAttributeToTender(numId);
    }
  } else {
    selectedAttributeId.value = null;
  }
  if (
    typeof (orig as { preventDefault?: () => void })?.preventDefault ===
    "function"
  ) {
    (orig as { preventDefault: () => void }).preventDefault();
  }
}

async function loadReferenceAttributes() {
  loadingReferenceAttributes.value = true;
  try {
    const { data } = await tendersUC.getTenderAttributesByType("procurement");
    referenceAttributes.value = Array.isArray(data) ? data : [];
  } finally {
    loadingReferenceAttributes.value = false;
  }
}

function openCreateAttributeModal() {
  createAttributeForm.name = "";
  createAttributeForm.type = "text";
  createAttributeForm.category = null;
  createAttributeForm.is_required = false;
  createAttributeForm.options = createAttributeOptionsForType("text");
  showCreateAttributeModal.value = true;
}

async function openAttributePickerModal() {
  selectedAttributeId.value = null;
  attributeSearch.value = "";
  showAttributePickerModal.value = true;
  await loadReferenceAttributes();
}

function currentTenderAttributeIds() {
  return normalizedAttributeIds(
    (tenderAttributes.value || []).map((a: any) => a?.id),
  );
}

async function addAttributeToTender(attributeId: number) {
  const normalizedId = toValidAttributeId(attributeId);
  if (normalizedId == null || isViewingPreviousTour.value) return;
  if (currentTenderAttributeIds().includes(normalizedId)) return;
  const ok = await patchTender({
    attribute_ids: normalizedAttributeIds([
      ...currentTenderAttributeIds(),
      normalizedId,
    ]),
  });
  if (!ok) return;
  if (
    !Array.isArray(tenderAttributes.value) ||
    !tenderAttributes.value.length
  ) {
    await loadTender();
  }
  showAttributePickerModal.value = false;
}

async function addSelectedAttributeFromPicker() {
  if (selectedAttributeId.value == null) return;
  await addAttributeToTender(selectedAttributeId.value);
}

async function removeAttributeFromTender(attributeId: number) {
  const normalizedId = toValidAttributeId(attributeId);
  if (normalizedId == null || isViewingPreviousTour.value) return;
  const nextIds = currentTenderAttributeIds().filter(
    (id) => id !== normalizedId,
  );
  const ok = await patchTender({ attribute_ids: nextIds });
  if (!ok) {
    useToast().add({
      title: "Не вдалося видалити атрибут",
      color: "error",
    });
  }
}

async function submitCreateAttribute() {
  const name = (createAttributeForm.name || "").trim();
  if (!name) {
    useToast().add({ title: "Вкажіть назву атрибута", color: "error" });
    return;
  }
  const companyId = tender.value?.company;
  if (!companyId) {
    useToast().add({
      title: "Тендер не привʼязаний до компанії",
      color: "error",
    });
    return;
  }
  const options: Record<string, any> = {};
  if (createAttributeForm.type === "numeric") {
    const nums = (createAttributeForm.options.numeric_choices || [])
      .map((v) => Number(v))
      .filter((v) => Number.isFinite(v));
    if (nums.length) options.numeric_choices = nums;
  }
  if (createAttributeForm.type === "text") {
    const texts = (createAttributeForm.options.text_choices || [])
      .map((v) => String(v ?? "").trim())
      .filter(Boolean);
    if (texts.length) options.text_choices = texts;
  }
  createAttributeSaving.value = true;
  try {
    const { data: created, error } = await tendersUC.createTenderAttribute({
      company: companyId,
      name,
      type: createAttributeForm.type,
      tender_type: "procurement",
      category: createAttributeForm.category,
      is_required: Boolean(createAttributeForm.is_required),
      options,
    });
    if (error || !created?.id) {
      useToast().add({
        title: "Помилка створення атрибута",
        description: typeof error === "string" ? error : undefined,
        color: "error",
      });
      return;
    }
    await addAttributeToTender(created.id);
    showCreateAttributeModal.value = false;
    await loadReferenceAttributes();
  } finally {
    createAttributeSaving.value = false;
  }
}

async function removeCriterionFromTender(c: any) {
  if (isViewingPreviousTour.value) return;
  const criterionRef = criterionRefId(c);
  const criterionId = toValidCriterionId(c?.id);
  if (criterionRef == null && criterionId == null) return;
  const prev = [...tenderCriteria.value];
  tenderCriteria.value = tenderCriteria.value.filter(
    (x) =>
      !(
        (criterionId != null &&
          toValidCriterionId((x as any)?.id) === criterionId) ||
        (criterionRef != null && criterionRefId(x) === criterionRef)
      ),
  );
  const ok = await persistTenderCriteriaImmediately();
  if (!ok) tenderCriteria.value = prev;
}

function findCategoryNameById(tree: any[], id: number): string | null {
  for (const node of tree || []) {
    if (node.id === id) return node.name ?? node.label ?? null;
    if (node.children?.length) {
      const found = findCategoryNameById(node.children, id);
      if (found) return found;
    }
  }
  return null;
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

function findTreeNodeById(tree: any[], id: number): any | null {
  for (const node of tree || []) {
    if (Number(node?.id) === Number(id)) return node;
    if (node?.children?.length) {
      const found = findTreeNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

function collectDisabledTreeIds(items: any[]): number[] {
  const out: number[] = [];
  const walk = (nodes: any[]) => {
    for (const node of nodes || []) {
      if (node?.is_directly_assigned === false) out.push(Number(node.id));
      if (node?.children?.length) walk(node.children);
    }
  };
  walk(items);
  return out;
}

function countSelectableTreeNodes(items: any[]): number {
  let count = 0;
  const walk = (nodes: any[]) => {
    for (const node of nodes || []) {
      if (node?.is_directly_assigned !== false) count += 1;
      if (node?.children?.length) walk(node.children);
    }
  };
  walk(items);
  return count;
}

function findCategoryById(tree: any[], id: number): any | null {
  return findTreeNodeById(tree, id);
}

function applyCategoryCpvs(categoryId: number | null) {
  if (categoryId == null) return;
  const category = findCategoryById(categoryTree.value, categoryId);
  const cpvs = Array.isArray(category?.cpvs) ? category.cpvs : [];
  form.cpv_ids = cpvs
    .map((c: any) => Number(c?.id))
    .filter((id: number) => Number.isFinite(id));
  tenderCpvLabels.value = cpvs
    .map(
      (c: any) =>
        c?.label || `${c?.cpv_code || ""} - ${c?.name_ua || ""}`.trim(),
    )
    .filter((label: string) => !!label);
}

function toggleCategory(id: number) {
  form.category = form.category === id ? null : id;
  if (form.category) {
    applyCategoryCpvs(form.category);
  }
}

function toggleExpense(id: number) {
  form.expense_article = form.expense_article === id ? null : id;
}

function toggleBranch(id: number) {
  form.branch = form.branch === id ? null : id;
  if (!form.branch) return;

  const selectedDepartment = form.department
    ? findTreeNodeById(departmentTree.value, form.department)
    : null;
  if (
    selectedDepartment &&
    Number(selectedDepartment.branch) !== Number(form.branch)
  ) {
    form.department = null;
  }
}

function toggleDepartment(id: number) {
  form.department = form.department === id ? null : id;
  if (!form.department || !form.branch) return;

  const selectedDepartment = findTreeNodeById(
    departmentTree.value,
    form.department,
  );
  if (
    selectedDepartment &&
    Number(selectedDepartment.branch) !== Number(form.branch)
  ) {
    form.branch = null;
  }
}

function formatTimerDuration(ms: number) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${days} дн / ${pad(hours)} год / ${pad(minutes)} хв / ${pad(seconds)} с`;
}

const acceptanceStartAtMs = computed(() => {
  const value = tender.value?.start_at;
  if (!value) return null;
  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
});
const acceptanceEndAtMs = computed(() => {
  const value = tender.value?.end_at;
  if (!value) return null;
  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
});
const acceptanceTimerText = computed(() => {
  const now = acceptanceTimerNowMs.value;
  const start = acceptanceStartAtMs.value;
  const end = acceptanceEndAtMs.value;
  if (start != null && now < start) {
    return `До початку: ${formatTimerDuration(start - now)}`;
  }
  if (end != null && now <= end) {
    return `До завершення: ${formatTimerDuration(end - now)}`;
  }
  if (end != null && now > end) return "Прийом пропозицій завершено";
  return "Час прийому не задано";
});

function isoToInput(value?: string | null) {
  if (!value) return "";
  const d = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function inputToIso(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function dateFromInput(value?: string | null): string {
  const datePart = String(value || "")
    .trim()
    .slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return "";
  return datePart;
}

function timeFromInput(value?: string | null): string {
  const match = String(value || "")
    .trim()
    .match(/T(\d{2}:\d{2})/);
  return match?.[1] || "";
}

function normalizeDateValue(value?: string | null): string {
  const raw = String(value || "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  return "";
}

function normalizeTimeValue(value?: string | null): string {
  const raw = String(value || "").trim();
  const parsed = raw.match(/^(\d{1,2}):(\d{1,2})$/);
  if (!parsed) return "";
  const hours = Number(parsed[1]);
  const minutes = Number(parsed[2]);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return "";
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}`;
}

function formatTimeInput(value: string | number | null | undefined): string {
  const raw = String(value ?? "").replace(/[^\d:]/g, "");
  if (!raw) return "";

  const normalizeHours = (input: string): string => {
    if (!input) return "";
    const parsed = Number(input);
    if (!Number.isFinite(parsed)) return "";
    const bounded = Math.max(0, Math.min(23, parsed));
    return input.length >= 2
      ? String(bounded).padStart(2, "0")
      : String(bounded);
  };
  const normalizeMinutes = (input: string): string => {
    if (!input) return "";
    const parsed = Number(input);
    if (!Number.isFinite(parsed)) return "";
    const bounded = Math.max(0, Math.min(59, parsed));
    return input.length >= 2
      ? String(bounded).padStart(2, "0")
      : String(bounded);
  };

  if (raw.includes(":")) {
    const colonIndex = raw.indexOf(":");
    const hoursInput = raw.slice(0, colonIndex).replace(/\D/g, "").slice(0, 2);
    const minutesInput = raw
      .slice(colonIndex + 1)
      .replace(/\D/g, "")
      .slice(0, 2);
    if (!hoursInput) return "";
    const hours = normalizeHours(hoursInput);
    if (raw.endsWith(":") && !minutesInput) return `${hours}:`;
    const minutes = normalizeMinutes(minutesInput);
    return `${hours}:${minutes}`;
  }

  const digits = raw.replace(/\D/g, "").slice(0, 4);
  if (!digits) return "";
  if (digits.length <= 2) {
    const hours = normalizeHours(digits);
    return `${hours}${digits.length === 2 ? ":" : ""}`;
  }
  if (digits.length === 3) {
    const hours = normalizeHours(digits.slice(0, 1));
    const minutes = normalizeMinutes(digits.slice(1, 3));
    return `${hours}:${minutes}`;
  }
  const hours = normalizeHours(digits.slice(0, 2));
  const minutes = normalizeMinutes(digits.slice(2, 4));
  return `${hours}:${minutes}`;
}

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

function normalizeVatPercentInput(value: unknown): string {
  const parsed = parseVatPercentValue(value);
  if (parsed == null) return "";
  return Number.isInteger(parsed) ? String(parsed) : String(parsed);
}

function formatDateForInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function formatTimeForInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function buildDateTimeInput(dateValue: string, timeValue: string): string {
  const normalizedDate = normalizeDateValue(dateValue);
  const normalizedTime = normalizeTimeValue(timeValue);
  if (!normalizedDate || !normalizedTime) return "";
  return `${normalizedDate}T${normalizedTime}`;
}

function getDefaultPublishTimes() {
  const now = new Date();
  now.setSeconds(0, 0);
  const end = new Date(now.getTime() + 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  const crossesDay =
    end.getFullYear() !== now.getFullYear() ||
    end.getMonth() !== now.getMonth() ||
    end.getDate() !== now.getDate();
  return {
    start: `${pad(now.getHours())}:${pad(now.getMinutes())}`,
    end: crossesDay
      ? "23:59"
      : `${pad(end.getHours())}:${pad(end.getMinutes())}`,
  };
}

function syncPublishScheduleFromTimingForm() {
  const fallbackTimes = getDefaultPublishTimes();
  const todayDate = formatDateForInput(new Date());
  publishStartDate.value =
    normalizeDateValue(dateFromInput(timingForm.start_at)) || todayDate;
  publishEndDate.value =
    normalizeDateValue(dateFromInput(timingForm.end_at)) ||
    publishStartDate.value;
  publishStartTime.value =
    normalizeTimeValue(timeFromInput(timingForm.start_at)) ||
    fallbackTimes.start;
  publishEndTime.value =
    normalizeTimeValue(timeFromInput(timingForm.end_at)) || fallbackTimes.end;
}

function applyPublishScheduleToTimingForm() {
  const startAt = buildDateTimeInput(
    publishStartDate.value,
    publishStartTime.value,
  );
  const endAt = buildDateTimeInput(publishEndDate.value, publishEndTime.value);
  if (!startAt || !endAt) return false;
  timingForm.start_at = startAt;
  timingForm.end_at = endAt;
  return true;
}

function syncTimingScheduleFromForm() {
  const fallbackTimes = getDefaultPublishTimes();
  const nowDate = formatDateForInput(new Date());
  timingStartDate.value =
    normalizeDateValue(dateFromInput(timingForm.start_at)) || nowDate;
  timingEndDate.value =
    normalizeDateValue(dateFromInput(timingForm.end_at)) ||
    timingStartDate.value;
  timingStartTime.value =
    normalizeTimeValue(timeFromInput(timingForm.start_at)) ||
    fallbackTimes.start;
  timingEndTime.value =
    normalizeTimeValue(timeFromInput(timingForm.end_at)) || fallbackTimes.end;
}

function applyTimingScheduleToForm() {
  const startAt = buildDateTimeInput(
    timingStartDate.value,
    timingStartTime.value,
  );
  const endAt = buildDateTimeInput(timingEndDate.value, timingEndTime.value);
  if (!startAt || !endAt) return false;
  timingForm.start_at = startAt;
  timingForm.end_at = endAt;
  return true;
}

function syncResumeAcceptanceScheduleFromForm() {
  const fallbackTimes = getDefaultPublishTimes();
  const nowDate = formatDateForInput(new Date());
  resumeAcceptanceStartDate.value =
    normalizeDateValue(dateFromInput(resumeAcceptanceForm.start_at)) || nowDate;
  resumeAcceptanceEndDate.value =
    normalizeDateValue(dateFromInput(resumeAcceptanceForm.end_at)) ||
    resumeAcceptanceStartDate.value;
  resumeAcceptanceStartTime.value =
    normalizeTimeValue(timeFromInput(resumeAcceptanceForm.start_at)) ||
    fallbackTimes.start;
  resumeAcceptanceEndTime.value =
    normalizeTimeValue(timeFromInput(resumeAcceptanceForm.end_at)) ||
    fallbackTimes.end;
}

function applyResumeAcceptanceScheduleToForm() {
  const startAt = buildDateTimeInput(
    resumeAcceptanceStartDate.value,
    resumeAcceptanceStartTime.value,
  );
  const endAt = buildDateTimeInput(
    resumeAcceptanceEndDate.value,
    resumeAcceptanceEndTime.value,
  );
  if (!startAt || !endAt) return false;
  resumeAcceptanceForm.start_at = startAt;
  resumeAcceptanceForm.end_at = endAt;
  return true;
}

function syncPlannedPublicationFromTender() {
  const fallbackTimes = getDefaultPublishTimes();
  plannedStartDate.value =
    normalizeDateValue(dateFromInput(tender.value?.planned_start_at)) || "";
  plannedEndDate.value =
    normalizeDateValue(dateFromInput(tender.value?.planned_end_at)) || "";
  plannedStartTime.value =
    normalizeTimeValue(timeFromInput(tender.value?.planned_start_at)) ||
    (plannedStartDate.value ? fallbackTimes.start : "");
  plannedEndTime.value =
    normalizeTimeValue(timeFromInput(tender.value?.planned_end_at)) ||
    (plannedEndDate.value ? fallbackTimes.end : "");
}

function buildPlannedPublicationPayload() {
  const startAt = buildDateTimeInput(
    plannedStartDate.value,
    plannedStartTime.value,
  );
  const endAt = buildDateTimeInput(plannedEndDate.value, plannedEndTime.value);
  return {
    planned_start_at: startAt ? inputToIso(startAt) : null,
    planned_end_at: endAt ? inputToIso(endAt) : null,
  };
}

async function loadTender() {
  loading.value = true;
  try {
    isReadOnlyApprover.value = false;
    const loadFromParticipationList = async () => {
      const tabs: Array<"active" | "processing" | "completed"> = [
        "active",
        "processing",
        "completed",
      ];
      for (const tab of tabs) {
        const { data } = await tendersUC.getTendersForParticipation(
          isSales,
          tab,
        );
        if (!Array.isArray(data)) continue;
        const found = data.find((t: any) => Number(t?.id) === tenderId.value);
        if (found) return found as any;
      }
      return null;
    };

    const { data, error } = await tendersUC.getTender(tenderId.value, isSales);
    let tenderData: any = data;

    if ((!tenderData || error) && myCompanyId.value != null) {
      tenderData = await loadFromParticipationList();
    }

    if (!tenderData) {
      tender.value = null;
      return;
    }
    tender.value = tenderData;
    displayStage.value = normalizeStageForUi(
      tenderData.stage,
      tenderData.conduct_type,
    );
    const rawPositions = Array.isArray(tenderData.positions)
      ? tenderData.positions
      : Array.isArray((tenderData as any).tender_positions)
        ? (tenderData as any).tender_positions
        : [];
    if (rawPositions.length) {
      tenderPositions.value = rawPositions.map((p: any) => ({
        id: p.id,
        nomenclature_id: p.nomenclature_id ?? p.nomenclature,
        name: p.name,
        unit_name: p.unit_name ?? "",
        position_local_key: p.id ?? nextTenderPositionLocalKey(),
        quantity: p.quantity ?? 1,
        description: p.description ?? "",
        warehouse_id: p.warehouse_id ?? p.warehouse ?? null,
        warehouse_name: p.warehouse_name ?? "",
        warehouse_full_address: p.warehouse_full_address ?? "",
        warehouse_region: p.warehouse_region ?? "",
        warehouse_type: p.warehouse_type ?? "",
        warehouse_type_label: p.warehouse_type_label ?? "",
        start_price: p.start_price ?? null,
        min_bid_step: p.min_bid_step ?? null,
        max_bid_step: p.max_bid_step ?? null,
        attribute_values:
          p.attribute_values && typeof p.attribute_values === "object"
            ? { ...p.attribute_values }
            : {},
      }));
    } else {
      tenderPositions.value = [];
    }
    usesPositionWarehouses.value = Boolean(
      tenderData.uses_position_warehouses,
    );
    priceCriterionVat.value = tenderData.price_criterion_vat ?? undefined;
    priceCriterionVatPercent.value = normalizeVatPercentInput(
      tenderData.price_criterion_vat_percent,
    );
    priceCriterionDelivery.value =
      tenderData.price_criterion_delivery ?? undefined;
    if (Array.isArray(tenderData.criteria)) {
      tenderCriteria.value = tenderData.criteria;
    }
    if (Array.isArray(tenderData.attributes)) {
      tenderAttributes.value = tenderData.attributes;
    } else {
      tenderAttributes.value = [];
    }
    const cpvList = tenderData.cpv_categories || [];
    form.cpv_ids = cpvList.length
      ? cpvList.map((c: any) => c.id)
      : tenderData.cpv_category != null
        ? [tenderData.cpv_category]
        : [];
    tenderCpvLabels.value = cpvList.length
      ? cpvList.map(
          (c: any) =>
            c.label || `${c.cpv_code || ""} - ${c.name_ua || ""}`.trim(),
        )
      : tenderData.cpv_label
        ? [tenderData.cpv_label]
        : [];
    Object.assign(form, {
      name: tenderData.name ?? "",
      category: tenderData.category ?? null,
      expense_article: tenderData.expense_article ?? null,
      estimated_budget: tenderData.estimated_budget ?? null,
      branch: tenderData.branch ?? null,
      department: tenderData.department ?? null,
      conduct_type: tenderData.conduct_type ?? "rfx",
      auction_model: tenderData.auction_model ?? "classic_auction",
      publication_type: tenderData.publication_type ?? "open",
      currency: tenderData.currency ?? null,
      general_terms: tenderData.general_terms ?? "",
      approval_model_id: tenderData.approval_model ?? null,
    });
    invitedCompanies.value = Array.isArray(
      (tenderData as any).invited_supplier_companies,
    )
      ? (tenderData as any).invited_supplier_companies
          .map((company: any) => ({
            id: Number(company?.id || 0),
            name: company?.name ?? "",
            edrpou: company?.edrpou ?? "",
          }))
          .filter((company: any) => company.id > 0)
      : [];
    invitedEmails.value = Array.isArray((tenderData as any).invited_emails)
      ? (tenderData as any).invited_emails
          .map((email: any) => String(email || "").trim())
          .filter(Boolean)
      : [];
    await loadAvailableApprovalModels();
    timingForm.start_at = isoToInput(tenderData.start_at);
    timingForm.end_at = isoToInput(tenderData.end_at);
    syncPlannedPublicationFromTender();
    await loadTours();
    if (displayStage.value === "decision") {
      await loadDecisionMarketReference({ skipLoader: true });
    } else {
      firstTourMarketByPositionId.value = {};
      decisionMarketMode.value = "first_tour";
    }
    await autoAdvanceAcceptance();
    await loadApprovalRoute();
  } finally {
    loading.value = false;
  }
}

async function loadTours() {
  if (!tenderId.value) return;
  const { data } = await tendersUC.getTenderTours(tenderId.value, isSales);
  // API повертає [{ id, tour_number }]; тур 1 — перший (корінь), наступні — повторні проведення
  tourOptions.value = Array.isArray(data)
    ? (data as { id: number; tour_number: number }[]).map((t) => ({
        value: t.id,
        label: `Тур ${t.tour_number ?? 1}`,
      }))
    : [];
}

function normalizeDecisionMarketMode(
  value: unknown,
): "first_tour" | "current_tour" {
  return value === "current_tour" ? "current_tour" : "first_tour";
}

async function loadDecisionMarketReference(
  options: { skipLoader?: boolean } = {},
) {
  if (!tenderId.value) return;
  const { data, error } = await tendersUC.getDecisionMarketReference(
    tenderId.value,
    isSales,
    { skipLoader: options.skipLoader ?? true },
  );
  if (error || !data) {
    firstTourMarketByPositionId.value = {};
    decisionMarketMode.value = "first_tour";
    return;
  }
  const rows = Array.isArray((data as any).position_market)
    ? (data as any).position_market
    : [];
  const next: Record<number, number | null> = {};
  for (const row of rows) {
    const positionId = Number((row as any)?.position_id);
    if (!Number.isInteger(positionId) || positionId <= 0) continue;
    const numericMarket = Number((row as any)?.market_price);
    next[positionId] = Number.isFinite(numericMarket) ? numericMarket : null;
  }
  firstTourMarketByPositionId.value = next;
  decisionMarketMode.value = normalizeDecisionMarketMode(
    (data as any)?.mode_default,
  );
}

function onTourSelect(value: number | null) {
  if (value != null && value !== tenderId.value) {
    navigateTo(`/cabinet/tenders/${value}`);
  }
}

async function loadOptions() {
  const [cats, expenses, branches, departments, currencies] = await Promise.all(
    [
      tendersUC.getCategories(),
      tendersUC.getExpenses(),
      tendersUC.getBranches(),
      tendersUC.getDepartments(),
      tendersUC.getCurrencies(),
    ],
  );
  categoryTree.value = (cats.data as any[]) || [];
  expenseTree.value = (expenses.data as any[]) || [];
  branchTree.value = (branches.data as any[]) || [];
  departmentTree.value = (departments.data as any[]) || [];
  const rawCurrencies = (currencies.data as any[]) || [];
  currencyOptions.value = rawCurrencies.map((c: any) => ({
    value: c.id,
    label: String(c.code || ""),
  }));
  if (!form.currency && currencyOptions.value.length) {
    const preferredCurrency = rawCurrencies.find(
      (currency: any) => String(currency?.code || "").toUpperCase() === "UAH",
    );
    const preferredCurrencyId = Number(preferredCurrency?.id);
    if (Number.isInteger(preferredCurrencyId) && preferredCurrencyId > 0) {
      form.currency = preferredCurrencyId;
    } else {
      const firstCurrency = currencyOptions.value[0];
      if (firstCurrency) form.currency = firstCurrency.value;
    }
  }
}

async function loadNomenclaturesForPreparation() {
  loadingNomenclatures.value = true;
  try {
    let items: any[] = [];

    if ((form.cpv_ids?.length ?? 0) > 0) {
      const { data: byCpvs } = await tendersUC.getNomenclaturesByCpvs(
        form.cpv_ids,
      );
      items = (byCpvs as any[]) || [];
    } else if (form.category) {
      const [{ data: byCategory }, { data: categoryData }] = await Promise.all([
        tendersUC.getNomenclaturesByCategory(form.category),
        tendersUC.getCategory(form.category),
      ]);
      const merged = new Map<number, any>();
      for (const n of (byCategory as any[]) || []) merged.set(n.id, n);

      const cpvIds: number[] = ((categoryData as any)?.cpvs || [])
        .map((c: any) => Number(c.id))
        .filter((id: number) => Number.isInteger(id) && id > 0);
      if (cpvIds.length) {
        const { data: byCpvs } = await tendersUC.getNomenclaturesByCpvs(cpvIds);
        for (const n of (byCpvs as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    }

    availableNomenclatures.value = items;
  } finally {
    loadingNomenclatures.value = false;
  }
}

/** Додати позицію з номенклатури (подвійний клік у лівій панелі). Якщо вже є — попередження. */
function addPositionFromNomenclature(
  nomenclatureId: number,
  options: { notifyAdded?: boolean } = {},
) {
  if (isViewingPreviousTour.value) return;
  const hasSimilarPosition = tenderPositions.value.some(
    (p) => p.nomenclature_id === nomenclatureId,
  );
  if (hasSimilarPosition) {
    useToast().add({
      title: "Ви додали подібну позицію в тендер",
      color: "warning",
    });
  }
  const n = availableNomenclatures.value.find(
    (x: any) => x.id === nomenclatureId,
  );
  if (!n) return;
  tenderPositions.value.push({
    position_local_key: nextTenderPositionLocalKey(),
    nomenclature_id: n.id,
    name: n.name,
    unit_name: n.unit_name || "",
    quantity: 1,
    description: "",
    warehouse_id: null,
    warehouse_name: "",
    warehouse_full_address: "",
    warehouse_region: "",
    warehouse_type: "",
    warehouse_type_label: "",
    start_price: null,
    min_bid_step: null,
    max_bid_step: null,
    attribute_values: {},
  });
  if (options.notifyAdded && !hasSimilarPosition) {
    useToast().add({
      title: "Номенклатуру додано",
      color: "success",
    });
  }
}

/** Видалити позицію з тендера (за рядком таблиці). */
function removeTenderPositionByRow(row: {
  index?: number;
  original?: (typeof tenderPositions.value)[number];
}) {
  if (isViewingPreviousTour.value) return;
  const idx =
    typeof row.index === "number" && row.index >= 0
      ? row.index
      : tenderPositions.value.findIndex((p) => p === row.original);
  if (idx >= 0) tenderPositions.value.splice(idx, 1);
}

async function patchTender(payload: Record<string, unknown>) {
  if (!tender.value?.id) return false;
  const { data, error } = await tendersUC.patchTender(
    tender.value.id,
    isSales,
    payload,
  );
  if (error) return false;
  if (data) tender.value = { ...tender.value, ...data };
  if (typeof (data as any)?.uses_position_warehouses === "boolean") {
    usesPositionWarehouses.value = Boolean(
      (data as any).uses_position_warehouses,
    );
  }
  if (Array.isArray((data as any)?.attributes)) {
    tenderAttributes.value = (data as any).attributes;
  }
  if (data?.stage != null) {
    displayStage.value = normalizeStageForUi(
      data.stage,
      tender.value?.conduct_type ?? form.conduct_type,
    );
  }
  if (
    displayStage.value === "preparation" ||
    displayStage.value === "approval"
  ) {
    await loadApprovalRoute();
  } else {
    approvalRoutePayload.value = null;
  }
  return true;
}

function ruleLabel(value: string) {
  return value === "all" ? "Усі" : "Один зі";
}

async function loadAvailableApprovalModels() {
  const companyId = Number(tender.value?.company || myCompanyId.value || 0);
  if (!companyId || !isApprovalModelLookupReady.value) {
    availableApprovalModels.value = [];
    form.approval_model_id = null;
    return;
  }
  const { data } = await tendersUC.getAvailableApprovalModels({
    companyId,
    application: "procurement",
    categoryId: form.category,
    estimatedBudget:
      form.estimated_budget != null ? Number(form.estimated_budget) : null,
  });
  availableApprovalModels.value = data;
  if (
    form.approval_model_id != null &&
    !availableApprovalModels.value.some(
      (m: any) => Number(m.id) === Number(form.approval_model_id),
    )
  ) {
    form.approval_model_id = null;
  }
}

async function loadApprovalRoute() {
  if (!tender.value?.id) {
    approvalRoutePayload.value = null;
    isReadOnlyApprover.value = false;
    return;
  }
  const stage = displayStage.value;
  if (stage !== "preparation" && stage !== "approval") {
    approvalRoutePayload.value = null;
    isReadOnlyApprover.value = false;
    return;
  }
  const { data, error } = await tendersUC.getTenderApprovalRoute(
    tender.value.id,
    isSales,
  );
  if (error) return;
  approvalRoutePayload.value = data || null;
  isReadOnlyApprover.value = false;
  if (
    !isTenderAuthor.value &&
    currentUserId.value != null &&
    Array.isArray((data as any)?.nodes)
  ) {
    const inApproverRoute = (data as any).nodes.some((node: any) => {
      if (node?.kind !== "role" || !Array.isArray(node?.users)) return false;
      return node.users.some(
        (userNode: any) =>
          Number(userNode?.id || 0) === Number(currentUserId.value),
      );
    });
    isReadOnlyApprover.value = inApproverRoute;
  }
}

function approvalUserStatusClass(status: string | undefined) {
  if (status === "active") return "bg-yellow-100 text-yellow-700";
  if (status === "approved") return "bg-green-100 text-green-700";
  return "bg-gray-100 text-gray-500";
}

function approvalUserStatusIcon(status: string | undefined) {
  return status === "approved"
    ? "i-lucide-user-round-check"
    : "i-lucide-user-round";
}

function openApprovalSubmitModal() {
  approvalSubmitComment.value = "";
  showApprovalSubmitModal.value = true;
}

function validatePreparationReadinessBeforePublication() {
  const hasPositions = tenderPositions.value.length >= 1;
  const vatPercent = parseVatPercentValue(priceCriterionVatPercent.value);
  const hasPriceParams =
    !!priceCriterionVat.value &&
    !!priceCriterionDelivery.value &&
    (!isVatPercentRequired.value || vatPercent != null);
  if (hasPositions && hasPriceParams) return true;
  const msg = !hasPositions
    ? "Додайте хоча б одну позицію тендера."
    : "Налаштуйте параметри цінового критерію (ПДВ, % ПДВ та Доставка).";
  useToast().add({
    title: "Збереження неможливе",
    description: msg,
    color: "error",
  });
  return false;
}

async function submitApprovalSubmit() {
  if (
    approvalRouteHasApprovers.value &&
    !validatePreparationReadinessBeforePublication()
  ) {
    return;
  }
  approvalSubmitSaving.value = true;
  try {
    const preparationSaved = await savePreparation();
    if (!preparationSaved) return;

    const { data, error } = await tendersUC.submitTenderApprovalSubmit(
      tenderId.value,
      isSales,
      { comment: approvalSubmitComment.value.trim() },
    );
    if (error) {
      useToast().add({
        title: "Збереження неможливе",
        description: String(error),
        color: "error",
      });
      return;
    }
    const routePayload = (data as any)?.route;
    if (routePayload) {
      approvalRoutePayload.value = routePayload;
    }
    if ((data as any)?.stage) {
      displayStage.value = normalizeStageForUi(
        String((data as any).stage || ""),
        tender.value?.conduct_type ?? form.conduct_type,
      );
    }
    showApprovalSubmitModal.value = false;
    await loadTender();
    if (
      displayStage.value === "preparation" ||
      displayStage.value === "approval"
    ) {
      await loadApprovalRoute();
    }
  } finally {
    approvalSubmitSaving.value = false;
  }
}

async function openApprovalJournalModal() {
  const { data } = await tendersUC.getTenderApprovalJournal(
    tenderId.value,
    isSales,
  );
  approvalJournalRows.value = Array.isArray(data) ? data : [];
  showApprovalJournalModal.value = true;
}

function openApprovalActionModal(action: "approved" | "rejected") {
  pendingApprovalAction.value = action;
  approvalActionComment.value = "";
  showApprovalActionModal.value = true;
}

async function submitApprovalAction() {
  if (
    pendingApprovalAction.value === "rejected" &&
    !approvalActionComment.value.trim()
  ) {
    useToast().add({
      title: "Коментар обов'язковий",
      color: "error",
    });
    return;
  }
  approvalActionSaving.value = true;
  try {
    const { data, error } = await tendersUC.submitTenderApprovalAction(
      tenderId.value,
      isSales,
      {
        action: pendingApprovalAction.value,
        comment: approvalActionComment.value.trim(),
      },
    );
    if (error) return;
    const routePayload = (data as any)?.route;
    if (routePayload) {
      approvalRoutePayload.value = routePayload;
    }
    if ((data as any)?.stage) {
      displayStage.value = normalizeStageForUi(
        String((data as any).stage || ""),
        tender.value?.conduct_type ?? form.conduct_type,
      );
    }
    showApprovalActionModal.value = false;
    await loadTender();
    if (
      displayStage.value === "preparation" ||
      displayStage.value === "approval"
    ) {
      await loadApprovalRoute();
    }
  } finally {
    approvalActionSaving.value = false;
  }
}

async function ensureConditionTemplatesLoaded() {
  const companyId = Number(tender.value?.company || myCompanyId.value || 0);
  if (!companyId) return;
  conditionTemplatesLoading.value = true;
  try {
    const { data } = await tendersUC.getTenderConditionTemplates(companyId);
    conditionTemplates.value = Array.isArray(data) ? data : [];
  } finally {
    conditionTemplatesLoading.value = false;
  }
}

async function openConditionTemplateModal() {
  await ensureConditionTemplatesLoaded();
  showConditionTemplateModal.value = true;
}

function applyConditionTemplate(templateItem: TenderConditionTemplate) {
  form.general_terms = String(templateItem.content || "");
  showConditionTemplateModal.value = false;
}

function repeatAcceptanceInvitationNotice() {
  showAcceptanceInvitationsModal.value = false;
  useToast().add({
    title: "Функціонал у роботі",
    description:
      "Повторне сповіщення учасників буде доступне найближчим часом.",
    color: "neutral",
  });
}

async function loadProtocolPreview() {
  if (!tenderId.value) return;
  protocolPreviewLoading.value = true;
  protocolPreviewError.value = "";
  const { data, error } = await tendersUC.getTenderProtocolPreview(
    tenderId.value,
    isSales,
    {
      skipLoader: true,
      cacheTtlMs: 5_000,
    },
  );
  if (error || !data) {
    protocolPreview.value = null;
    protocolPreviewError.value = "Не вдалося сформувати протокол.";
    protocolPreviewLoading.value = false;
    return;
  }
  protocolPreview.value = data as TenderProtocolPreviewPayload;
  protocolPreviewLoading.value = false;
}

async function openProtocolModal() {
  showProtocolModal.value = true;
  await loadProtocolPreview();
}

function downloadProtocolPdf() {
  if (import.meta.client) {
    window.open(protocolPdfDownloadUrl.value, "_blank", "noopener");
  }
}

async function savePassport() {
  const cpvIds = form.cpv_ids ?? [];
  if (cpvIds.length === 0) {
    useToast().add({
      title: "Заповніть обовʼязкове поле",
      description: "Оберіть хоча б одну категорію CPV.",
      color: "error",
    });
    return;
  }
  if (isApprovalModelRequired.value && !form.approval_model_id) {
    useToast().add({
      title: "Заповніть обовʼязкове поле",
      description: "Оберіть модель погодження.",
      color: "error",
    });
    return;
  }
  if (isExpenseArticleRequired.value && !form.expense_article) {
    useToast().add({
      title: "Заповніть обовʼязкове поле",
      description: "Оберіть статтю бюджету.",
      color: "error",
    });
    return;
  }
  if (isBranchRequired.value && !form.branch) {
    useToast().add({
      title: "Заповніть обовʼязкове поле",
      description: "Оберіть філіал.",
      color: "error",
    });
    return;
  }
  if (isDepartmentRequired.value && !form.department) {
    useToast().add({
      title: "Заповніть обовʼязкове поле",
      description: "Оберіть підрозділ.",
      color: "error",
    });
    return;
  }
  saving.value = true;
  try {
    const ok = await patchTender({
      name: form.name,
      category: form.category,
      cpv_ids: form.cpv_ids,
      expense_article: form.expense_article,
      estimated_budget: form.estimated_budget,
      branch: form.branch,
      department: form.department,
      conduct_type: form.conduct_type,
      auction_model: form.auction_model,
      publication_type: form.publication_type,
      currency: form.currency,
      general_terms: form.general_terms,
      approval_model_id: form.approval_model_id,
      invited_supplier_company_ids: invitedCompanies.value.map((company) => company.id),
      invited_emails: invitedEmails.value,
      ...buildPlannedPublicationPayload(),
      stage: "preparation",
    });
    if (!ok) {
      useToast().add({
        title: "Помилка збереження",
        description: "Перевірте дані (зокрема категорію CPV).",
        color: "error",
      });
    }
  } finally {
    saving.value = false;
  }
}

function openPublishModal() {
  if (!validatePreparationReadinessBeforePublication()) {
    return;
  }
  const plannedStart = buildDateTimeInput(
    plannedStartDate.value,
    plannedStartTime.value,
  );
  const plannedEnd = buildDateTimeInput(
    plannedEndDate.value,
    plannedEndTime.value,
  );
  timingForm.start_at = isoToInput(
    tender.value?.start_at || inputToIso(plannedStart),
  );
  timingForm.end_at = isoToInput(
    tender.value?.end_at || inputToIso(plannedEnd),
  );
  syncPublishScheduleFromTimingForm();
  showPublishModal.value = true;
}

function openTimingModal() {
  timingForm.start_at = isoToInput(tender.value?.start_at);
  timingForm.end_at = isoToInput(tender.value?.end_at);
  timingComment.value = "";
  syncTimingScheduleFromForm();
  showTimingModal.value = true;
}

async function publishTender() {
  if (!applyPublishScheduleToTimingForm()) {
    useToast().add({
      title: "Заповніть період і час проведення",
      color: "error",
    });
    return;
  }
  const startDate = new Date(timingForm.start_at);
  const endDate = new Date(timingForm.end_at);
  const now = new Date();
  if (
    Number.isNaN(startDate.getTime()) ||
    Number.isNaN(endDate.getTime()) ||
    endDate <= startDate
  ) {
    useToast().add({
      title: "Час завершення має бути пізніше за час початку",
      color: "error",
    });
    return;
  }
  if (startDate < now) {
    useToast().add({
      title: "Час початку не може бути меншим від поточного",
      color: "error",
    });
    return;
  }
  const prepared = await savePreparation();
  if (!prepared) {
    useToast().add({
      title: "Не вдалося зберегти підготовку тендера",
      description:
        "Перевірте позиції, критерії та параметри цінового критерію.",
      color: "error",
    });
    return;
  }
  const ok = await patchTender({
    start_at: inputToIso(timingForm.start_at),
    end_at: inputToIso(timingForm.end_at),
    stage: "acceptance",
  });
  if (ok) showPublishModal.value = false;
}

async function saveTiming() {
  if (!applyTimingScheduleToForm()) {
    useToast().add({
      title: "Заповніть дати та час початку і завершення",
      color: "error",
    });
    return;
  }
  const nextStartAt = canEditStart.value ? inputToIso(timingForm.start_at) : undefined;
  const nextEndAt = inputToIso(timingForm.end_at);
  const startChanged =
    canEditStart.value && nextStartAt !== (tender.value?.start_at ?? null);
  const endChanged = nextEndAt !== (tender.value?.end_at ?? null);
  if ((startChanged || endChanged) && !timingComment.value.trim()) {
    useToast().add({
      title: "Заповніть коментар до зміни часу",
      color: "error",
    });
    return;
  }
  const payload: Record<string, unknown> = {
    end_at: nextEndAt,
    timing_comment: timingComment.value.trim(),
  };
  if (canEditStart.value) payload.start_at = nextStartAt;
  const ok = await patchTender(payload);
  if (ok) showTimingModal.value = false;
}

async function goToDecision() {
  await patchTender({ stage: "decision" });
}

/** Повернути тендер на етап підготовки (тільки для типу Реєстрація). */
async function goBackToPreparation() {
  if (isViewingPreviousTour.value) return;
  const ok = await patchTender({ stage: "preparation" });
  if (ok) await loadTender();
}

function openResumeAcceptanceModal() {
  const now = new Date();
  now.setMinutes(now.getMinutes() + 1, 0, 0);
  const end = new Date(now);
  end.setDate(end.getDate() + 1);
  const nowTime = formatTimeForInput(now);
  resumeAcceptanceForm.start_at = `${formatDateForInput(now)}T${nowTime}`;
  resumeAcceptanceForm.end_at = `${formatDateForInput(end)}T${nowTime}`;
  syncResumeAcceptanceScheduleFromForm();
  showResumeAcceptanceModal.value = true;
}

async function submitResumeAcceptance() {
  if (!applyResumeAcceptanceScheduleToForm()) {
    useToast().add({
      title: "Заповніть дати та час початку і завершення",
      color: "error",
    });
    return;
  }
  const startStr = (resumeAcceptanceForm.start_at || "").trim();
  const endStr = (resumeAcceptanceForm.end_at || "").trim();
  if (!startStr || !endStr) {
    useToast().add({
      title: "Заповніть час початку та завершення",
      color: "error",
    });
    return;
  }
  const start = new Date(startStr);
  const end = new Date(endStr);
  const now = new Date();
  if (start < now) {
    useToast().add({
      title: "Час початку не може бути меншим від поточного",
      color: "error",
    });
    return;
  }
  if (end <= start) {
    useToast().add({
      title: "Час завершення повинен бути пізніше за час початку",
      color: "error",
    });
    return;
  }
  resumeAcceptanceSaving.value = true;
  try {
    const ok = await patchTender({
      stage: "acceptance",
      start_at: start.toISOString(),
      end_at: end.toISOString(),
    });
    if (ok) {
      showResumeAcceptanceModal.value = false;
      useToast().add({
        title: "Прийом пропозицій відновлено",
        color: "success",
      });
      await loadTender();
    }
  } finally {
    resumeAcceptanceSaving.value = false;
  }
}

async function autoAdvanceAcceptance() {
  if (tender.value?.stage !== "acceptance" || !tender.value?.end_at) return;
  if (new Date() > new Date(tender.value.end_at)) {
    await patchTender({ stage: "decision" });
  }
}

function openDecisionModal() {
  if (!decisionModeSelectableOptions.value.length) {
    useToast().add({
      title: "Недоступні варіанти рішення",
      description: "Спочатку дочекайтесь появи пропозицій учасників.",
      color: "error",
    });
    return;
  }
  selectedDecisionMode.value = decisionModeSelectableOptions.value[0].value;
  decisionJustification.value = "";
  showDecisionModal.value = true;
}

function closeDecisionModal() {
  showDecisionModal.value = false;
}

async function confirmDecision() {
  if (!selectedDecisionMode.value) return;
  await fixDecision(selectedDecisionMode.value);
}

async function fixDecision(mode: DecisionMode) {
  showDecisionModal.value = false;
  saving.value = true;
  try {
    const body: {
      mode: DecisionMode;
      position_winners?: { position_id: number; proposal_id: number }[];
      comment?: string;
    } = { mode };
    if (mode === "winner") {
      body.position_winners = Object.entries(selectedWinnerByPosition.value)
        .filter(([, proposal_id]) => proposal_id != null)
        .map(([position_id, proposal_id]) => ({
          position_id: Number(position_id),
          proposal_id: Number(proposal_id),
        }));
    }
    const normalizedJustification = decisionJustification.value.trim();
    if (
      (mode === "winner" || mode === "cancel") &&
      normalizedJustification.length
    ) {
      body.comment = normalizedJustification;
    }
    const { data, error } = await tendersUC.fixTenderDecision(
      tenderId.value,
      isSales,
      body,
    );
    if (error || !data) return;
    if (data.id && data.stage === "preparation") {
      await navigateTo(`/cabinet/tenders/${data.id}`);
      return;
    }
    await loadTender();
  } finally {
    selectedDecisionMode.value = null;
    decisionJustification.value = "";
    saving.value = false;
  }
}

async function approveTender() {
  openApprovalActionModal("approved");
}

function refreshSelectedWinnersByPosition() {
  const hasAnyPersistedWinners = displayTenderPositions.value.some(
    (pos: any) => Number(pos?.winner_proposal_id) > 0,
  );
  const next: Record<number, number | null> = {};
  for (const pos of displayTenderPositions.value) {
    next[pos.id] = resolveWinnerSelectionForPosition(
      pos.id,
      true,
      pos?.winner_proposal_id,
      hasAnyPersistedWinners,
    );
  }
  selectedWinnerByPosition.value = next;
}

function updateDecisionProposalsDeltaCursor(proposals: any[]) {
  if (!Array.isArray(proposals) || !proposals.length) return;
  let nextCursor = decisionProposalsDeltaCursor.value;
  let nextCursorMs = Number.isNaN(Date.parse(String(nextCursor || "")))
    ? null
    : Date.parse(String(nextCursor || ""));
  for (const proposal of proposals) {
    const cursorRaw = String(proposal?.status_updated_at || "").trim();
    if (!cursorRaw) continue;
    const cursorMs = Date.parse(cursorRaw);
    if (Number.isNaN(cursorMs)) continue;
    if (nextCursorMs == null || cursorMs > nextCursorMs) {
      nextCursor = cursorRaw;
      nextCursorMs = cursorMs;
    }
  }
  decisionProposalsDeltaCursor.value = nextCursor;
}

function markDecisionProposalsSyncActivity(hasChanges: boolean) {
  if (hasChanges) {
    decisionProposalsIdleStreak.value = 0;
    return;
  }
  decisionProposalsIdleStreak.value = Math.min(
    decisionProposalsIdleStreak.value + 1,
    20,
  );
}

async function fetchChangedDecisionProposals(
  proposalIds: number[],
  loadFullDetails: boolean,
) {
  const changedProposals: any[] = [];
  for (
    let offset = 0;
    offset < proposalIds.length;
    offset += REALTIME_INCREMENTAL_SYNC_CHUNK_SIZE
  ) {
    const chunk = proposalIds.slice(
      offset,
      offset + REALTIME_INCREMENTAL_SYNC_CHUNK_SIZE,
    );
    if (!chunk.length) continue;
    const { data, error } = await tendersUC.getTenderProposals(
      tenderId.value,
      isSales,
      {
        skipLoader: true,
        proposalIds: chunk,
        statusOnly: !loadFullDetails,
      },
    );
    if (error || !Array.isArray(data)) return null;
    changedProposals.push(...data);
  }
  return changedProposals;
}

async function loadDecisionProposals(
  skipLoader = false,
  changedProposalIds: number[] = [],
  options: { forceFull?: boolean } = {},
) {
  if (!tenderId.value) return;
  if (!skipLoader) decisionProposalsIdleStreak.value = 0;
  const loadFullDetails =
    Boolean(options.forceFull) || displayStage.value !== "acceptance";
  const normalizedChangedIds = Array.from(
    new Set(
      changedProposalIds
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0),
    ),
  );
  const canIncrementalSync =
    normalizedChangedIds.length > 0 &&
    normalizedChangedIds.length <= REALTIME_MAX_INCREMENTAL_SYNC_IDS &&
    decisionProposals.value.length > 0;
  const canUseStatusDeltaBase =
    !loadFullDetails &&
    skipLoader &&
    decisionProposals.value.length > 0 &&
    !!decisionProposalsDeltaCursor.value;
  const preferStatusDeltaForManyChangedIds =
    canUseStatusDeltaBase &&
    normalizedChangedIds.length >= REALTIME_DELTA_SYNC_IDS_THRESHOLD;

  if (!canIncrementalSync || preferStatusDeltaForManyChangedIds) {
    const canStatusDeltaSync =
      canUseStatusDeltaBase &&
      (normalizedChangedIds.length === 0 || preferStatusDeltaForManyChangedIds);
    if (canStatusDeltaSync) {
      const { data: deltaProposals, error: deltaError } =
        await tendersUC.getTenderProposals(tenderId.value, isSales, {
          skipLoader: true,
          statusOnly: true,
          updatedSince: decisionProposalsDeltaCursor.value || undefined,
        });
      if (!deltaError && Array.isArray(deltaProposals)) {
        if (deltaProposals.length) {
          const mergedById = new Map<number, any>();
          for (const proposal of decisionProposals.value) {
            const id = Number(proposal?.id);
            if (Number.isInteger(id) && id > 0) mergedById.set(id, proposal);
          }
          for (const proposal of deltaProposals) {
            const id = Number(proposal?.id);
            if (!Number.isInteger(id) || id <= 0) continue;
            mergedById.set(id, {
              ...(mergedById.get(id) || {}),
              ...proposal,
            });
          }
          decisionProposals.value = Array.from(mergedById.values());
          decisionProposalsFullLoaded.value = false;
          updateDecisionProposalsDeltaCursor(deltaProposals);
        }
        markDecisionProposalsSyncActivity(deltaProposals.length > 0);
        return;
      }
    }

    const { data } = await tendersUC.getTenderProposals(
      tenderId.value,
      isSales,
      {
        skipLoader,
        statusOnly: !loadFullDetails,
      },
    );
    decisionProposals.value = Array.isArray(data) ? data : [];
    decisionProposalsFullLoaded.value = loadFullDetails;
    if (!loadFullDetails) {
      decisionProposalsDeltaCursor.value = null;
      updateDecisionProposalsDeltaCursor(decisionProposals.value);
    }
    if (loadFullDetails) refreshSelectedWinnersByPosition();
    markDecisionProposalsSyncActivity(normalizedChangedIds.length > 0);
    return;
  }

  const changedProposals = await fetchChangedDecisionProposals(
    normalizedChangedIds,
    loadFullDetails,
  );
  if (!Array.isArray(changedProposals)) {
    const { data } = await tendersUC.getTenderProposals(
      tenderId.value,
      isSales,
      {
        skipLoader: true,
        statusOnly: !loadFullDetails,
      },
    );
    decisionProposals.value = Array.isArray(data) ? data : [];
    decisionProposalsFullLoaded.value = loadFullDetails;
    if (!loadFullDetails) {
      decisionProposalsDeltaCursor.value = null;
      updateDecisionProposalsDeltaCursor(decisionProposals.value);
    }
    if (loadFullDetails) refreshSelectedWinnersByPosition();
    markDecisionProposalsSyncActivity(normalizedChangedIds.length > 0);
    return;
  }
  if (!changedProposals.length) {
    markDecisionProposalsSyncActivity(false);
    return;
  }

  const mergedById = new Map<number, any>();
  const existingIds = new Set<number>();
  for (const proposal of decisionProposals.value) {
    const id = Number(proposal?.id);
    if (Number.isInteger(id) && id > 0) {
      mergedById.set(id, proposal);
      existingIds.add(id);
    }
  }
  let hasNewIds = false;
  for (const proposal of changedProposals) {
    const id = Number(proposal?.id);
    if (!Number.isInteger(id) || id <= 0) continue;
    const currentProposal = mergedById.get(id);
    if (!existingIds.has(id)) hasNewIds = true;
    if (loadFullDetails) {
      mergedById.set(id, proposal);
      continue;
    }
    mergedById.set(id, {
      ...(currentProposal || {}),
      ...proposal,
    });
  }
  decisionProposals.value = Array.from(mergedById.values());
  if (loadFullDetails) {
    refreshSelectedWinnersByPosition();
    markDecisionProposalsSyncActivity(true);
    return;
  }
  updateDecisionProposalsDeltaCursor(changedProposals);
  if (hasNewIds) decisionProposalsFullLoaded.value = false;
  markDecisionProposalsSyncActivity(true);
}

async function ensureDecisionProposalsFullDetails(skipLoader = true) {
  if (decisionProposalsFullLoaded.value) return;
  await loadDecisionProposals(skipLoader, [], { forceFull: true });
}

function stopAcceptanceRefresh() {
  acceptanceRealtime.stop();
}

function startAcceptanceRefresh() {
  if (isParticipant.value || displayStage.value !== "acceptance") {
    stopAcceptanceRefresh();
    return;
  }
  acceptanceRealtime.start();
}

const proposalComparisonPositions = computed(
  () => tender.value?.positions ?? [],
);
const proposalComparisonPriceHeader = computed(() => {
  const v = tender.value?.price_criterion_vat;
  const d = tender.value?.price_criterion_delivery;
  const vPercent = parseVatPercentValue(
    tender.value?.price_criterion_vat_percent,
  );
  const vatLabels: Record<string, string> = {
    with_vat: "з ПДВ",
    without_vat: "без ПДВ",
  };
  const deliveryLabels: Record<string, string> = {
    with_delivery: "із урахуванням доставки",
    without_delivery: "без урахування доставки",
  };
  const vLabel = v && vatLabels[v] ? vatLabels[v] : v || "";
  const vPercentLabel =
    v === "with_vat" && vPercent != null ? `${vPercent}%` : "";
  const dLabel = d && deliveryLabels[d] ? deliveryLabels[d] : d || "";
  return ["Ціна", vLabel, vPercentLabel, dLabel].filter(Boolean).join(" ");
});

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
  return formatDecimalDisplay(qty * num);
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

function getBestWorstForProposalComparison(positionId: number) {
  const withPrice: { id: number; price: number }[] = [];
  for (const p of submittedDecisionProposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const num = Number(pv?.price);
    if (!Number.isNaN(num)) withPrice.push({ id: p.id, price: num });
  }
  if (withPrice.length === 0) return { bestId: null, worstId: null };
  const best = withPrice.reduce((a, b) => (a.price <= b.price ? a : b));
  const worst = withPrice.reduce((a, b) => (a.price >= b.price ? a : b));
  return { bestId: best.id, worstId: worst.id };
}

const proposalComparisonByPosition = computed(() => {
  const out: Record<number, { bestId: number | null; worstId: number | null }> =
    {};
  for (const pos of proposalComparisonPositions.value) {
    out[pos.id] = getBestWorstForProposalComparison(pos.id);
  }
  return out;
});

async function openProposalsModal() {
  await ensureDecisionProposalsFullDetails();
  showProposalsModal.value = true;
}

async function loadAcceptanceBidHistory() {
  if (!acceptanceBidHistoryPositionId.value || !tenderId.value) {
    acceptanceBidHistory.value = [];
    return;
  }
  acceptanceBidHistoryLoading.value = true;
  try {
    const { data } = await tendersUC.getTenderBidHistory(
      tenderId.value,
      isSales,
      acceptanceBidHistoryPositionId.value,
    );
    acceptanceBidHistory.value = Array.isArray(data) ? data : [];
  } finally {
    acceptanceBidHistoryLoading.value = false;
  }
}

function stopChatPolling() {
  if (chatPollInterval) {
    clearInterval(chatPollInterval);
    chatPollInterval = null;
  }
}

function startChatPolling() {
  stopChatPolling();
  if (!showParticipantChatModal.value && !showOrganizerChatModal.value) return;
  chatPollInterval = setInterval(() => {
    if (showOrganizerChatModal.value) {
      void loadChatThreads(false);
      if (selectedChatSupplierId.value) {
        void loadChatMessages(selectedChatSupplierId.value, false);
      }
      return;
    }
    void loadChatMessages(null, false);
  }, 15000);
}

async function loadChatThreads(resetSelection = true) {
  const { data } = await tendersUC.getTenderChatThreads(
    tenderId.value,
    isSales,
  );
  chatThreads.value = Array.isArray(data) ? data : [];
  if (!resetSelection) return;
  if (!chatThreads.value.length) {
    selectedChatSupplierId.value = null;
    return;
  }
  const firstThreadSupplierId =
    Number(chatThreads.value[0]?.supplier_company || 0) || null;
  selectedChatSupplierId.value = firstThreadSupplierId;
}

async function loadChatMessages(
  supplierCompanyId?: number | null,
  clearDraft = false,
) {
  const { data } = await tendersUC.getTenderChatMessages(
    tenderId.value,
    isSales,
    supplierCompanyId ?? myCompanyId.value ?? undefined,
  );
  chatMessages.value = Array.isArray(data) ? data : [];
  if (clearDraft) chatDraft.value = "";
}

async function openParticipantChatModal() {
  showOrganizerChatModal.value = false;
  showParticipantChatModal.value = true;
  await loadChatMessages(null, true);
  startChatPolling();
}

async function openOrganizerChatModal() {
  showParticipantChatModal.value = false;
  showOrganizerChatModal.value = true;
  await loadChatThreads(true);
  if (selectedChatSupplierId.value) {
    await loadChatMessages(selectedChatSupplierId.value, true);
    await loadChatThreads(false);
  } else {
    chatMessages.value = [];
    chatDraft.value = "";
  }
  startChatPolling();
}

async function selectOrganizerChatThread(supplierCompanyId: number) {
  selectedChatSupplierId.value = Number(supplierCompanyId) || null;
  await loadChatMessages(selectedChatSupplierId.value, true);
  await loadChatThreads(false);
}

function closeChatModals() {
  showParticipantChatModal.value = false;
  showOrganizerChatModal.value = false;
  chatDraft.value = "";
  stopChatPolling();
}

async function submitParticipantChatMessage() {
  const body = chatDraft.value.trim();
  if (!body) return;
  chatSending.value = true;
  try {
    await tendersUC.sendTenderChatMessage(tenderId.value, isSales, {
      body,
      supplier_company_id: myCompanyId.value ?? undefined,
    });
    await loadChatMessages(null, true);
  } finally {
    chatSending.value = false;
  }
}

async function submitOrganizerChatMessage() {
  const body = chatDraft.value.trim();
  if (!body || !selectedChatSupplierId.value) return;
  chatSending.value = true;
  try {
    await tendersUC.sendTenderChatMessage(tenderId.value, isSales, {
      body,
      supplier_company_id: selectedChatSupplierId.value,
    });
    await loadChatMessages(selectedChatSupplierId.value, true);
    await loadChatThreads(false);
  } finally {
    chatSending.value = false;
  }
}

function formatCriterionSummary(
  values: Record<string, unknown> | null | undefined,
) {
  if (!values || typeof values !== "object") return "—";
  const entries = Object.entries(values)
    .filter(([, value]) => value != null && value !== "")
    .map(
      ([key, value]) =>
        `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`,
    );
  return entries.length ? entries.join("; ") : "—";
}

async function openProposalChangeReportModal() {
  showProposalChangeReportModal.value = true;
  proposalChangeReportLoading.value = true;
  try {
    const { data } = await tendersUC.getTenderProposalChangeReport(
      tenderId.value,
      isSales,
    );
    proposalChangeReport.value = Array.isArray(data) ? data : [];
  } finally {
    proposalChangeReportLoading.value = false;
  }
}

function openDisqualificationModal() {
  disqualificationRows.value = submittedDecisionProposalsAll.value.map(
    (proposal: any) => ({
      proposal_id: Number(proposal.id),
      supplier_name:
        proposal.supplier_company?.name || proposal.supplier_name || "—",
      disqualify: Boolean(proposal.disqualified_at),
      comment: String(proposal.disqualification_comment || ""),
    }),
  );
  showDisqualificationModal.value = true;
}

async function submitDisqualifications() {
  disqualificationSaving.value = true;
  try {
    const items = disqualificationRows.value.map((row: any) => ({
      proposal_id: Number(row.proposal_id),
      disqualify: Boolean(row.disqualify),
      comment: String(row.comment || ""),
    }));
    const { data, error } = await tendersUC.disqualifyTenderProposals(
      tenderId.value,
      isSales,
      { items },
    );
    if (error) {
      alert(getApiErrorMessage(error));
      return;
    }
    decisionProposals.value = Array.isArray(data) ? data : [];
    showDisqualificationModal.value = false;
  } finally {
    disqualificationSaving.value = false;
  }
}

async function openProposalEditor() {
  await navigateTo(`/cabinet/tenders/proposals/${tenderId.value}`);
}

onMounted(async () => {
  await loadTender();
  if (!isParticipant.value) {
    await loadOptions();
    await loadNomenclaturesForPreparation();
  }
  acceptanceTimerNowMs.value = Date.now();
  acceptanceTimerInterval = setInterval(() => {
    acceptanceTimerNowMs.value = Date.now();
  }, 1000);
  startAcceptanceRefresh();
});

watch(tenderId, () => {
  protocolPreview.value = null;
  protocolPreviewError.value = "";
  loadTender();
});
watch(
  () => currentUserId.value,
  (next, prev) => {
    if (
      next == null ||
      next === prev ||
      !tender.value?.id ||
      (displayStage.value !== "preparation" &&
        displayStage.value !== "approval")
    ) {
      return;
    }
    void loadApprovalRoute();
  },
);
watch(displayStage, async (stage) => {
  if (stage === "preparation" && !isParticipant.value) {
    await loadNomenclaturesForPreparation();
  }
  if (stage === "acceptance" || stage === "decision" || stage === "approval") {
    await loadDecisionProposals();
  }
  if (stage === "decision") {
    await loadDecisionMarketReference({ skipLoader: true });
  }
  if (stage === "preparation" || stage === "approval") {
    await loadApprovalRoute();
  } else {
    approvalRoutePayload.value = null;
  }
  startAcceptanceRefresh();
});
watch(
  () => acceptanceTab.value,
  async (tab) => {
    if (tab !== "history" || !isOnlineAuctionTender.value) return;
    if (!acceptanceBidHistoryPositionId.value) {
      acceptanceBidHistoryPositionId.value =
        acceptanceBidHistoryPositionOptions.value[0]?.value ?? null;
    }
    await loadAcceptanceBidHistory();
  },
);
watch(
  () => acceptanceBidHistoryPositionId.value,
  async () => {
    if (acceptanceTab.value !== "history") return;
    await loadAcceptanceBidHistory();
  },
);
watch(
  () => [showParticipantChatModal.value, showOrganizerChatModal.value],
  ([participantOpen, organizerOpen]) => {
    if (participantOpen || organizerOpen) {
      startChatPolling();
      return;
    }
    stopChatPolling();
  },
);
watch(isParticipant, () => {
  startAcceptanceRefresh();
});
watch([isRegistration, () => displayStage.value], () => {
  if (isRegistration.value && displayStage.value === "acceptance") {
    displayStage.value = "decision";
  }
});
watch(
  () => [form.category, form.cpv_ids],
  async () => {
    if (!isParticipant.value && displayStage.value === "preparation") {
      await loadNomenclaturesForPreparation();
    }
  },
);
watch(
  () => [form.category, form.estimated_budget, tender.value?.company],
  () => {
    if (approvalModelsDebounceTimer) {
      clearTimeout(approvalModelsDebounceTimer);
    }
    approvalModelsDebounceTimer = setTimeout(() => {
      void loadAvailableApprovalModels();
    }, 250);
  },
);
watch(prepTab, (tab) => {
  if (tab === "criteria") loadReferenceCriteria();
});

onUnmounted(() => {
  stopAcceptanceRefresh();
  stopChatPolling();
  if (acceptanceTimerInterval) {
    clearInterval(acceptanceTimerInterval);
    acceptanceTimerInterval = null;
  }
  if (approvalModelsDebounceTimer) {
    clearTimeout(approvalModelsDebounceTimer);
    approvalModelsDebounceTimer = null;
  }
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
.prep-tabs :deep([role="tablist"]) {
  width: 50%;
  margin-inline: auto;
}
.positions-table :deep(thead th) {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--ui-bg);
}
.approval-route-scroll {
  scrollbar-gutter: stable both-edges;
}
.approval-route-scroll::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
.approval-route-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.8);
  border-radius: 9999px;
}
@media (max-width: 1024px) {
  .prep-tabs :deep([role="tablist"]) {
    width: 100%;
  }
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

/* Редактор «Опис умов та вимог»: плейсхолдер зникає при фокусі, вся область клікабельна */
.general-terms-editor-wrapper:focus-within
  :deep(.ProseMirror p.is-empty::before) {
  opacity: 0;
}
.general-terms-editor-wrapper :deep(.ProseMirror.is-editor-empty:focus::before),
.general-terms-editor-wrapper
  :deep(.ProseMirror p.is-empty:first-child:focus::before) {
  opacity: 0;
}
</style>
