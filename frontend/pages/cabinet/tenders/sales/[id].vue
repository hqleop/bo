<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <UIcon
      name="i-heroicons-arrow-path"
      class="animate-spin size-8 text-gray-400"
    />
  </div>
  <div v-else-if="!tender" class="text-center py-12 text-gray-500">
    РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.
  </div>
  <div v-else class="h-full flex flex-col border-0 ring-0 outline-none">
    <div class="mb-4 flex items-center justify-between gap-4">
      <h1
        v-if="tender.number"
        class="text-xl font-semibold text-gray-900 truncate min-w-0"
      >
        в„– {{ tender.number }}
        <span class="font-normal text-gray-700">{{ tender.name }}</span>
      </h1>
      <div v-if="tourOptions.length" class="flex items-center gap-2 shrink-0">
        <span class="text-sm text-gray-600">РўСѓСЂ:</span>
        <USelect
          :model-value="tenderId"
          :items="tourOptions"
          value-key="value"
          class="min-w-[120px]"
          @update:model-value="onTourSelect"
        />
      </div>
    </div>
    <div
      v-if="!isParticipant"
      class="tender-stepper tender-stepper--compact mb-6"
    >
      <UStepper
        v-model="currentStepValue"
        :items="stepperItems"
        value-key="value"
        size="sm"
      />
    </div>

    <UAlert
      v-if="isViewingPreviousTour"
      color="neutral"
      variant="subtle"
      icon="i-heroicons-eye"
      title="РџРµСЂРµРіР»СЏРґ РїРѕРїРµСЂРµРґРЅСЊРѕРіРѕ С‚СѓСЂСѓ"
      description="Р’Рё РїРµСЂРµРіР»СЏРґР°С”С‚Рµ Р·Р±РµСЂРµР¶РµРЅС– РґР°РЅС– РїРѕРїРµСЂРµРґРЅСЊРѕРіРѕ С‚СѓСЂСѓ. Р РµРґР°РіСѓРІР°РЅРЅСЏ С‚Р° Р·РјС–РЅР° РµС‚Р°РїС–РІ РЅРµРґРѕСЃС‚СѓРїРЅС– вЂ” РєРѕР¶РµРЅ С‚СѓСЂ Р·Р±РµСЂС–РіР°С”С‚СЊСЃСЏ РѕРєСЂРµРјРѕ."
      class="mb-4"
    />

    <div class="flex flex-1 min-h-0 gap-6">
      <div
        class="flex-1 min-w-0 min-h-0"
        :class="displayStage === 'preparation' ? '' : 'overflow-y-auto'"
      >
        <template v-if="displayStage === 'passport'">
          <UCard class="overflow-hidden">
            <template #header>
              <h3 class="text-lg font-semibold text-gray-900">
                РџР°СЃРїРѕСЂС‚ С‚РµРЅРґРµСЂР°
              </h3>
            </template>
            <UForm :state="form" class="space-y-6">
              <div
                class="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6 lg:gap-8"
              >
                <div class="space-y-6">
                  <UFormField
                    label="РќР°Р·РІР° С‚РµРЅРґРµСЂР°"
                    required
                    class="mb-0 w-full"
                  >
                    <UInput
                      v-model="form.name"
                      placeholder="Р’РІРµРґС–С‚СЊ РЅР°Р·РІСѓ С‚РµРЅРґРµСЂР°"
                      size="md"
                      class="w-full"
                      :disabled="isViewingPreviousTour"
                    />
                  </UFormField>

                  <div>
                    <p
                      class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                    >
                      РљР°С‚РµРіРѕСЂС–Р·Р°С†С–СЏ
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <ContentSearch
                        label="РљР°С‚РµРіРѕСЂС–СЏ"
                        placeholder="РћР±РµСЂС–С‚СЊ РєР°С‚РµРіРѕСЂС–СЋ"
                        search-placeholder="РџРѕС€СѓРє РєР°С‚РµРіРѕСЂС–С—"
                        :disabled="
                          isViewingPreviousTour ||
                          (form.cpv_ids?.length ?? 0) > 0
                        "
                        :tree="categoryTree"
                        :selected-ids="selectedCategoryIds"
                        :search-term="categorySearch"
                        @toggle="toggleCategory"
                        @update:search-term="categorySearch = $event"
                      />
                      <CpvLazyMultiSearch
                        label="РљР°С‚РµРіРѕСЂС–СЏ CPV"
                        placeholder="РћР±РµСЂС–С‚СЊ CPV"
                        required
                        :disabled="isViewingPreviousTour || !!form.category"
                        :selected-ids="form.cpv_ids"
                        :selected-labels="tenderCpvLabels"
                        @update:selected-ids="form.cpv_ids = $event"
                        @update:selected-labels="tenderCpvLabels = $event"
                      />
                    </div>
                  </div>

                  <div>
                    <p
                      class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                    >
                      Р‘СЋРґР¶РµС‚ С– РІР°Р»СЋС‚Р°
                    </p>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <UFormField label="РЎС‚Р°С‚С‚СЏ Р±СЋРґР¶РµС‚Сѓ">
                        <USelectMenu
                          v-model="form.expense_article"
                          :items="expenseOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ СЃС‚Р°С‚С‚СЋ"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                      <UFormField label="РћСЂС–С”РЅС‚РѕРІРЅРёР№ Р±СЋРґР¶РµС‚">
                        <UInput
                          v-model.number="form.estimated_budget"
                          type="number"
                          step="0.01"
                          placeholder="0"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                      <UFormField label="Р’Р°Р»СЋС‚Р°" required>
                        <USelectMenu
                          v-model="form.currency"
                          :items="currencyOptions"
                          value-key="value"
                          placeholder="Р’Р°Р»СЋС‚Сѓ"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <div>
                    <p
                      class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                    >
                      РћСЂРіР°РЅС–Р·Р°С†С–Р№РЅР° СЃС‚СЂСѓРєС‚СѓСЂР°
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <UFormField label="Р¤С–Р»С–Р°Р»">
                        <USelectMenu
                          v-model="form.branch"
                          :items="branchOptions"
                          value-key="value"
                          placeholder="Оберіть філіал"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                          @update:model-value="onBranchChange"
                        />
                      </UFormField>
                      <UFormField label="РџС–РґСЂРѕР·РґС–Р»">
                        <USelectMenu
                          v-model="form.department"
                          :items="departmentOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ РїС–РґСЂРѕР·РґС–Р»"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <div>
                    <p
                      class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                    >
                      РџР°СЂР°РјРµС‚СЂРё РїСЂРѕС†РµРґСѓСЂРё
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <UFormField label="РўРёРї РїСЂРѕРІРµРґРµРЅРЅСЏ" required>
                        <USelectMenu
                          v-model="form.conduct_type"
                          :items="conductTypeOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ С‚РёРї"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                      <UFormField label="РўРёРї РїСѓР±Р»С–РєР°С†С–С—" required>
                        <USelectMenu
                          v-model="form.publication_type"
                          :items="publicationTypeOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ С‚РёРї"
                          size="sm"
                          :disabled="isViewingPreviousTour"
                        />
                      </UFormField>
                    </div>
                  </div>
                </div>

                <div
                  class="border-t border-gray-200 pt-5 lg:border-t-0 lg:border-l lg:border-gray-200 lg:pt-0 lg:pl-6 flex flex-col min-h-[320px]"
                >
                  <p
                    class="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3"
                  >
                    Р—Р°РіР°Р»СЊРЅС– СѓРјРѕРІРё РїСЂРѕРІРµРґРµРЅРЅСЏ С‚РµРЅРґРµСЂР°
                  </p>
                  <UFormField
                    label="РћРїРёСЃ СѓРјРѕРІ С‚Р° РІРёРјРѕРі"
                    class="mb-0 flex-1 flex flex-col min-h-0"
                  >
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
                        placeholder="РћРїРёС€С–С‚СЊ Р·Р°РіР°Р»СЊРЅС– СѓРјРѕРІРё, РІРёРјРѕРіРё РґРѕ СѓС‡Р°СЃРЅРёРєС–РІ, РїРѕСЂСЏРґРѕРє РѕС†С–РЅРєРё РїСЂРѕРїРѕР·РёС†С–Р№ С‚РѕС‰Рѕ. Р¦РµР№ С‚РµРєСЃС‚ Р±СѓРґРµ РґРѕСЃС‚СѓРїРЅРёР№ СѓС‡Р°СЃРЅРёРєР°Рј."
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
          <!-- РџР°РЅРµР»СЊ Р·Р°РїСЂРѕС€РµРЅРЅСЏ СѓС‡Р°СЃРЅРёРєС–РІ: 2/3 Р»С–РІРѕСЂСѓС‡, 1/3 РїСЂР°РІРѕСЂСѓС‡ -->
          <div
            v-if="showInvitationPanel"
            class="h-full min-h-0 flex flex-col rounded-lg p-4 bg-white"
          >
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">Р—Р°РїСЂРѕС€РµРЅРЅСЏ СѓС‡Р°СЃРЅРёРєС–РІ</h3>
              <UButton
                variant="ghost"
                size="sm"
                icon="i-heroicons-arrow-left"
                @click="showInvitationPanel = false"
              >
                Р”Рѕ РїС–РґРіРѕС‚РѕРІРєРё
              </UButton>
            </div>
            <!-- РџСЂРѕРїРѕСЂС†С–С—: 2/5 РєРѕРЅС‚СЂР°РіРµРЅС‚Рё, 2/5 CPV, 1/5 email -->
            <div class="flex flex-1 min-h-0 gap-4">
              <!-- РћР±Р»Р°СЃС‚СЊ 1 (2/5) -->
              <div
                class="flex-[2] min-w-0 flex flex-col border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden"
              >
                <h4
                  class="p-3 border-b border-gray-200 text-sm font-semibold text-gray-700"
                >
                  РћР±СЂР°РЅРЅСЏ РєРѕРЅС‚СЂР°РіРµРЅС‚Р° Р·С– СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ РєРѕРјРїР°РЅС–С—
                </h4>
                <div
                  class="flex-1 min-h-0 flex flex-col min-w-0 divide-y divide-gray-200"
                >
                  <div
                    class="flex-1 min-h-0 flex flex-col p-3 overflow-hidden min-h-[200px]"
                  >
                    <UFormField label="РџРѕС€СѓРє РєРѕРЅС‚СЂР°РіРµРЅС‚Р° Р·Р° РЅР°Р·РІРѕСЋ Р°Р±Рѕ РєРѕРґРѕРј">
                      <UInput
                        v-model="invitationContractorSearch"
                        placeholder="РќР°Р·РІР° Р°Р±Рѕ Р„Р”Р РџРћРЈ"
                        size="sm"
                        class="w-full"
                      />
                    </UFormField>
                    <UFormField
                      label="Р¤С–Р»СЊС‚СЂ РїРѕСЃС‚Р°С‡Р°Р»СЊРЅРёРєС–РІ РїРѕ РєР°С‚РµРіРѕСЂС–С— CPV"
                      class="mt-2"
                    >
                      <USelectMenu
                        v-model="invitationSupplierCpvFilterIds"
                        :items="invitationCpvOptions"
                        value-key="id"
                        label-key="label"
                        placeholder="РЈСЃС– РєР°С‚РµРіРѕСЂС–С—"
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
                            "вЂ”"
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
                            Р—Р°РїСЂРѕСЃРёС‚Рё
                          </UButton>
                        </li>
                      </ul>
                      <p v-else class="text-sm text-gray-500 p-3">
                        РќРµРјР°С” РїРѕСЃС‚Р°С‡Р°Р»СЊРЅРёРєС–РІ Р·Р° РєСЂРёС‚РµСЂС–СЏРјРё РїРѕС€СѓРєСѓ.
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
                          РќР°Р·Р°Рґ
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
                          Р”Р°Р»С–
                        </UButton>
                      </div>
                      <UButton
                        size="sm"
                        :disabled="selectedContractorCompanyIds.length === 0"
                        @click="inviteSelectedContractors"
                      >
                        Р—Р°РїСЂРѕСЃРёС‚Рё
                      </UButton>
                    </div>
                  </div>
                  <div class="flex-1 min-h-0 flex flex-col p-3 min-h-[120px]">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">
                      Р—Р°РїСЂРѕС€РµРЅС– РєРѕРјРїР°РЅС–С—
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
                          company.name || company.edrpou || "вЂ”"
                        }}</span>
                        <UButton
                          icon="i-heroicons-trash"
                          size="xs"
                          variant="ghost"
                          color="error"
                          aria-label="Р’РёРґР°Р»РёС‚Рё"
                          @click="removeInvitedCompany(idx)"
                        />
                      </li>
                    </ul>
                    <p v-else class="text-sm text-gray-500 py-1">РџРѕСЂРѕР¶РЅСЊРѕ.</p>
                  </div>
                </div>
              </div>

              <!-- РћР±Р»Р°СЃС‚СЊ 2 (2/5): Р·РІРµСЂС…Сѓ РїРѕС€СѓРє + СЃРїРёСЃРѕРє CPV (СЃРёСЃС‚РµРјРЅС–) Р· РїР°РіС–РЅР°С†С–С”СЋ С‚Р° Р—Р°РїСЂРѕСЃРёС‚Рё, Р·РЅРёР·Сѓ вЂ” РєР°С‚РµРіРѕСЂС–С— РїРѕ СЏРєРёРј Р·Р°РїСЂРѕС€СѓСЋС‚СЊСЃСЏ -->
              <div
                class="flex-[2] min-w-0 flex flex-col border border-gray-200 rounded-lg bg-white overflow-hidden divide-y divide-gray-200"
              >
                <h4
                  class="p-3 border-b border-gray-200 text-sm font-semibold text-gray-700"
                >
                  РџРѕС€СѓРє РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ РїРѕ CPV
                </h4>
                <div class="flex-1 min-h-0 flex flex-col min-w-0">
                  <div
                    class="flex-1 min-h-0 flex flex-col p-3 overflow-hidden min-h-[200px]"
                  >
                    <UFormField label="РџРѕС€СѓРє РєР°С‚РµРіРѕСЂС–С— CPV">
                      <UInput
                        v-model="invitationCpvSearchTerm"
                        placeholder="РљРѕРґ Р°Р±Рѕ РЅР°Р·РІР° CPV"
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
                            Р—Р°РїСЂРѕСЃРёС‚Рё
                          </UButton>
                        </li>
                      </ul>
                      <p
                        v-else-if="cpvWithCompaniesLoading"
                        class="text-sm text-gray-500 p-3"
                      >
                        Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ...
                      </p>
                      <p v-else class="text-sm text-gray-500 p-3">
                        РќРµРјР°С” РєР°С‚РµРіРѕСЂС–Р№ Р·Р° РєСЂРёС‚РµСЂС–СЏРјРё РїРѕС€СѓРєСѓ.
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
                          РќР°Р·Р°Рґ
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
                          Р”Р°Р»С–
                        </UButton>
                      </div>
                      <UButton
                        size="sm"
                        :disabled="selectedCpvIdsForInvite.length === 0"
                        @click="inviteSelectedCpv"
                      >
                        Р—Р°РїСЂРѕСЃРёС‚Рё
                      </UButton>
                    </div>
                  </div>
                  <div class="flex-1 min-h-0 flex flex-col p-3 min-h-[120px]">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2">
                      РљР°С‚РµРіРѕСЂС–С— CPV, Р·Р° СЏРєРёРјРё Р·Р°РїСЂРѕС€СѓСЋС‚СЊСЃСЏ СѓС‡Р°СЃРЅРёРєРё
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
                          aria-label="Р’РёРґР°Р»РёС‚Рё"
                          @click="removeInvitedCpv(id)"
                        />
                      </li>
                    </ul>
                    <p v-else class="text-sm text-gray-500 py-1">
                      РћР±РµСЂС–С‚СЊ РєР°С‚РµРіРѕСЂС–С— РІРёС‰Рµ С‚Р° РЅР°С‚РёСЃРЅС–С‚СЊ Р—Р°РїСЂРѕСЃРёС‚Рё.
                    </p>
                  </div>
                </div>
              </div>

              <!-- РћР±Р»Р°СЃС‚СЊ 3 (1/5) -->
              <div
                class="flex-1 min-w-0 flex flex-col border border-gray-200 rounded-lg bg-white p-4 overflow-hidden"
              >
                <UButton
                  class="w-full shrink-0"
                  icon="i-heroicons-envelope"
                  @click="showInviteByEmailModal = true"
                >
                  Р—Р°РїСЂРѕС€РµРЅРЅСЏ РїРѕ email
                </UButton>
                <div class="mt-4 flex-1 min-h-0 overflow-auto">
                  <h4 class="text-sm font-semibold text-gray-700 mb-2">
                    Р—Р°РїСЂРѕС€РµРЅС– Р·Р° email
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
                        aria-label="Р’РёРґР°Р»РёС‚Рё"
                        @click="removeInvitedEmail(idx)"
                      />
                    </li>
                  </ul>
                  <p v-else class="text-sm text-gray-500 py-2">РџРѕСЂРѕР¶РЅСЊРѕ.</p>
                </div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="h-full min-h-0 flex flex-col rounded-lg p-4 bg-white"
          >
            <h3 class="text-lg font-semibold mb-3">РџС–РґРіРѕС‚РѕРІРєР° РїСЂРѕС†РµРґСѓСЂРё</h3>
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
                  class="h-full min-h-0 flex flex-col gap-2"
                >
                  <div
                    v-if="!isParticipant"
                    class="flex justify-end shrink-0"
                  >
                    <UButton
                      variant="outline"
                      size="sm"
                      icon="i-heroicons-plus"
                      :disabled="
                        isViewingPreviousTour || !(form.cpv_ids?.length ?? 0)
                      "
                      @click="showCreateNomenclatureModal = true"
                    >
                      РЎС‚РІРѕСЂРёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ
                    </UButton>
                  </div>
                  <div class="flex-1 min-h-0 flex gap-4">
                    <!-- Р›С–РІР° РєРѕР»РѕРЅРєР°: РїРѕС€СѓРє + РґРµСЂРµРІРѕ РєР°С‚РµРіРѕСЂС–С— в†’ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё (С‚С–Р»СЊРєРё РґР»СЏ РІР»Р°СЃРЅРёРєР°) -->
                    <aside
                      v-if="!isParticipant"
                      class="w-72 flex-shrink-0 flex flex-col min-h-0 border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden"
                    >
                      <div class="p-2 border-b border-gray-200">
                        <UInput
                          v-model="nomenclatureSearch"
                          placeholder="РџРѕС€СѓРє РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё"
                          size="sm"
                          class="w-full"
                        />
                      </div>
                      <div class="flex-1 min-h-0 overflow-auto p-2">
                        <div
                          v-if="loadingNomenclatures"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂ...
                        </div>
                        <div
                          v-else-if="!nomenclatureTreeItems.length"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          РћР±РµСЂС–С‚СЊ РєР°С‚РµРіРѕСЂС–СЋ Р°Р±Рѕ CPV Сѓ РїР°СЃРїРѕСЂС‚С– С‚РµРЅРґРµСЂР°.
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

                    <!-- РўР°Р±Р»РёС†СЏ РїРѕР·РёС†С–Р№ -->
                    <div class="flex-1 min-h-0 flex flex-col min-w-0">
                      <div class="flex-1 min-h-0 overflow-auto">
                        <UTable
                          :data="
                            isParticipant ? displayTenderPositions : tenderPositions
                          "
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
                          <template #vat-cell>
                            <UInput value="" disabled size="sm" />
                          </template>
                          <template #actions-cell="{ row }">
                            <UButton
                              v-if="!isParticipant"
                              :disabled="isViewingPreviousTour"
                              color="error"
                              variant="ghost"
                              size="xs"
                              icon="i-heroicons-trash"
                              :aria-label="'Р’РёРґР°Р»РёС‚Рё РїРѕР·РёС†С–СЋ'"
                              @click="removeTenderPositionByRow(row)"
                            />
                          </template>
                        </UTable>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else-if="item.value === 'criteria'" class="space-y-6">
                  <!-- РџР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЏ -->
                  <div class="border rounded-lg p-4 bg-gray-50/50">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3">
                      РџР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЏ
                    </h4>
                    <div class="flex flex-wrap gap-6">
                      <UFormField label="РџР”Р’" class="min-w-[200px]">
                        <USelectMenu
                          v-model="priceCriterionVat"
                          :items="vatOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ РІР°СЂС–Р°РЅС‚"
                        />
                      </UFormField>
                      <UFormField label="Р”РѕСЃС‚Р°РІРєР°" class="min-w-[260px]">
                        <USelectMenu
                          v-model="priceCriterionDelivery"
                          :items="deliveryOptions"
                          value-key="value"
                          placeholder="РћР±РµСЂС–С‚СЊ РІР°СЂС–Р°РЅС‚"
                        />
                      </UFormField>
                    </div>
                  </div>

                  <!-- Р†РЅС€С– РєСЂРёС‚РµСЂС–С— С‚РµРЅРґРµСЂР°: Р»С–РІР° РїР°РЅРµР»СЊ (РїРѕС€СѓРє + РґРµСЂРµРІРѕ) + СЃРїРёСЃРѕРє РѕР±СЂР°РЅРёС… -->
                  <div class="flex gap-4 min-h-0 flex-1">
                    <aside
                      class="w-72 flex-shrink-0 flex flex-col min-h-0 border border-gray-200 rounded-lg bg-gray-50/50 overflow-hidden"
                    >
                      <div class="p-2 border-b border-gray-200">
                        <UInput
                          v-model="criteriaSearch"
                          placeholder="РџРѕС€СѓРє РєСЂРёС‚РµСЂС–С—РІ"
                          size="sm"
                          class="w-full"
                        />
                      </div>
                      <div class="flex-1 min-h-0 overflow-auto p-2">
                        <div
                          v-if="loadingReferenceCriteria"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ РєСЂРёС‚РµСЂС–С—РІ...
                        </div>
                        <div
                          v-else-if="!criteriaTreeItems.length"
                          class="text-sm text-gray-500 py-4 text-center"
                        >
                          РќРµРјР°С” РєСЂРёС‚РµСЂС–С—РІ Сѓ РґРѕРІС–РґРЅРёРєСѓ.
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
                      class="flex-1 min-w-0 flex flex-col border rounded-lg p-4 bg-white"
                    >
                      <div class="flex items-center justify-between gap-2 mb-3">
                        <h4 class="text-sm font-semibold text-gray-700">
                          Р”РѕРґР°РЅС– РєСЂРёС‚РµСЂС–С—
                        </h4>
                        <UButton
                          size="sm"
                          variant="outline"
                          icon="i-heroicons-plus"
                          :disabled="isViewingPreviousTour"
                          @click="openCreateCriterionModal"
                        >
                          РЎС‚РІРѕСЂРёС‚Рё РєСЂРёС‚РµСЂС–Р№
                        </UButton>
                      </div>
                      <p class="text-sm text-gray-600 mb-3">
                        РџРѕРґРІС–Р№РЅРёР№ РєР»С–Рє РїРѕ РєСЂРёС‚РµСЂС–СЋ РІ СЃРїРёСЃРєСѓ Р·Р»С–РІР° РґРѕРґР°С” Р№РѕРіРѕ
                        СЃСЋРґРё. Р—Р°РіР°Р»СЊРЅС– РєСЂРёС‚РµСЂС–С— Р·Р°РїРѕРІРЅСЋСЋС‚СЊСЃСЏ РѕРґРёРЅ СЂР°Р· РЅР° С‚РµРЅРґРµСЂ,
                        С–РЅРґРёРІС–РґСѓР°Р»СЊРЅС– вЂ” РїРѕ РєРѕР¶РЅС–Р№ РїРѕР·РёС†С–С—.
                      </p>
                      <div v-if="tenderCriteriaGeneral.length > 0" class="mb-4">
                        <h5
                          class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2"
                        >
                          Р—Р°РіР°Р»СЊРЅС– РєСЂРёС‚РµСЂС–С—
                        </h5>
                        <ul class="space-y-2 text-sm">
                          <li
                            v-for="c in tenderCriteriaGeneral"
                            :key="c.id"
                            class="flex items-center justify-between gap-2 py-2 px-3 rounded-md bg-blue-50/50 border border-blue-100"
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
                              aria-label="Р’РёРґР°Р»РёС‚Рё Р· С‚РµРЅРґРµСЂР°"
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
                          Р†РЅРґРёРІС–РґСѓР°Р»СЊРЅС– РєСЂРёС‚РµСЂС–С— (РїРѕ РїРѕР·РёС†С–С—)
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
                              criterionTypeLabel(c.type)
                            }}</span>
                            <UButton
                              :disabled="isViewingPreviousTour"
                              icon="i-heroicons-trash"
                              size="xs"
                              variant="ghost"
                              color="error"
                              aria-label="Р’РёРґР°Р»РёС‚Рё Р· С‚РµРЅРґРµСЂР°"
                              @click="removeCriterionFromTender(c)"
                            />
                          </li>
                        </ul>
                      </div>
                      <p
                        v-if="tenderCriteria.length === 0"
                        class="text-sm text-gray-500 py-2"
                      >
                        РљСЂРёС‚РµСЂС–С— РЅРµ РґРѕРґР°РЅРѕ.
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
            </template>
            <div class="border rounded-lg overflow-hidden">
              <table class="w-full text-sm border-collapse">
                <thead>
                  <tr class="border-b bg-gray-50">
                    <th class="text-left p-2 font-medium">Контрагент</th>
                    <th class="text-left p-2 font-medium">Час підтвердження участі</th>
                    <th class="text-left p-2 font-medium">Час подачі пропозиції</th>
                    <th class="text-left p-2 font-medium w-40">Дія</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="proposal in decisionProposals"
                    :key="proposal.id"
                    class="border-b hover:bg-gray-50/50"
                  >
                    <td class="p-2">
                      {{ proposal.supplier_company?.name || proposal.supplier_name || "—" }}
                    </td>
                    <td class="p-2">{{ formatDateTime(proposal.created_at) }}</td>
                    <td class="p-2">{{ formatDateTime(proposal.submitted_at) }}</td>
                    <td class="p-2">
                      <UButton size="xs" variant="outline" @click="openParticipantProposalModal(proposal)">
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
          </UCard>
        </template>
        <template v-else-if="displayStage === 'decision'">
          <div class="space-y-6">
            <div class="rounded-lg p-4 bg-gray-50/50">
              <div class="flex flex-wrap items-end gap-6">
                <UFormField label="РћСЂС–С”РЅС‚РѕРІРЅР° СЂРёРЅРєРѕРІР°" class="min-w-[220px]">
                  <USelectMenu
                    v-model="estimatedMarketMethod"
                    :items="estimatedMarketOptions"
                    value-key="value"
                    placeholder="РћР±РµСЂС–С‚СЊ"
                  />
                </UFormField>
                <UFormField label="Р С–С€РµРЅРЅСЏ" class="min-w-[200px]">
                  <UInput placeholder="вЂ”" disabled />
                </UFormField>
              </div>
            </div>

            <div class="rounded-lg p-4 bg-white">
              <h4 class="text-sm font-semibold text-gray-700 mb-3">
                РџРѕР·РёС†С–С— С‚РµРЅРґРµСЂР°
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
                <h3 class="text-lg font-semibold">Р—Р°С‚РІРµСЂРґР¶РµРЅРЅСЏ</h3>
              </template>
              <p class="text-sm text-gray-600 mb-4">
                РџРµСЂРµРіР»СЏРЅСЊС‚Рµ РїРµСЂРµРјРѕР¶С†С–РІ РїРѕ РїРѕР·РёС†С–СЏС… С‚Р° РїС–РґС‚РІРµСЂРґСЊС‚Рµ СЂС–С€РµРЅРЅСЏ РґР»СЏ
                Р·Р°РІРµСЂС€РµРЅРЅСЏ С‚РµРЅРґРµСЂР°.
              </p>
              <div class="border rounded-lg overflow-hidden">
                <table class="w-full text-sm border-collapse">
                  <thead>
                    <tr class="border-b bg-gray-50">
                      <th class="text-left p-2 font-medium">РџРѕР·РёС†С–СЏ</th>
                      <th class="text-left p-2 font-medium">РљС–Р»СЊРєС–СЃС‚СЊ</th>
                      <th class="text-left p-2 font-medium">РџРµСЂРµРјРѕР¶РµС†СЊ</th>
                      <th class="text-left p-2 font-medium">Р¦С–РЅР°</th>
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
                      class="border-b hover:bg-gray-50/50"
                    >
                      <td class="p-2">{{ pos.name }}</td>
                      <td class="p-2">
                        {{ pos.quantity }} {{ pos.unit_name ?? "" }}
                      </td>
                      <td class="p-2">{{ pos.winner_supplier_name ?? "вЂ”" }}</td>
                      <td class="p-2">{{ pos.winner_price ?? "вЂ”" }}</td>
                      <td v-for="c in tenderCriteria" :key="c.id" class="p-2">
                        {{
                          (pos.winner_criterion_values &&
                            (pos.winner_criterion_values[c.id] ??
                              pos.winner_criterion_values[String(c.id)])) ??
                          "вЂ”"
                        }}
                      </td>
                    </tr>
                    <tr v-if="!displayTenderPositions.length">
                      <td colspan="100" class="p-4 text-center text-gray-500">
                        РќРµРјР°С” РїРѕР·РёС†С–Р№.
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
              <h3 class="text-lg font-semibold">Р—Р°РІРµСЂС€РµРЅРёР№</h3>
            </template>
            <p class="text-sm text-gray-600">РўРµРЅРґРµСЂ Р·Р°РІРµСЂС€РµРЅРѕ.</p>
          </UCard>
        </template>
      </div>

      <aside class="w-56 flex-shrink-0 space-y-3">
        <template v-if="displayStage === 'passport'">
          <UButton
            class="w-full"
            :loading="saving"
            :disabled="isViewingPreviousTour"
            @click="savePassport"
          >
            Р—Р±РµСЂРµРіС‚Рё
          </UButton>
        </template>

        <template v-else-if="displayStage === 'preparation'">
          <template v-if="form.conduct_type === 'registration'">
            <UButton
              class="w-full"
              :disabled="isViewingPreviousTour"
              @click="openSubmitProposal"
              :loading="saving"
            >
              РџРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ
            </UButton>
          </template>
          <template v-else>
            <UButton
              class="w-full"
              :disabled="isViewingPreviousTour"
              @click="openPublishModal"
            >
              РћРїСѓР±Р»С–РєСѓРІР°С‚Рё
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              :disabled="isViewingPreviousTour"
              @click="showInvitationPanel = true"
            >
              Р—Р°РїСЂРѕСЃРёС‚Рё СѓС‡Р°СЃРЅРёРєС–РІ
            </UButton>
          </template>
          <UButton
            class="w-full"
            variant="outline"
            @click="openAttachedFilesModal"
          >
            РџСЂРёРєСЂС–РїР»РµРЅС– С„Р°Р№Р»Рё
          </UButton>
        </template>

        <template v-else-if="displayStage === 'acceptance'">
          <UButton
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="openTimingModal"
          >
            Р—РјС–РЅРёС‚Рё С‡Р°СЃ РїСЂРѕРІРµРґРµРЅРЅСЏ
          </UButton>
          <UButton class="w-full" variant="outline" @click="openAttachedFilesModal">
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
              РџРѕРІРµСЂРЅСѓС‚РёСЃСЊ РЅР° РїС–РґРіРѕС‚РѕРІРєСѓ
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
              Р’С–РґРЅРѕРІРёС‚Рё РїСЂРёР№РѕРј РїСЂРѕРїРѕР·РёС†С–Р№
            </UButton>
          </template>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="showWinnerModal = true"
          >
            Р СѓС‡РЅРёР№ РІРёР±С–СЂ РїРµСЂРµРјРѕР¶С†СЏ
          </UButton>
          <UButton
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="showDecisionModal = true"
          >
            Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalsModal"
          >
            РЈСЃС– РїСЂРѕРїРѕР·РёС†С–С—
          </UButton>
        </template>

        <template v-else-if="displayStage === 'approval'">
          <UButton
            class="w-full"
            :disabled="isViewingPreviousTour"
            @click="approveTender"
          >
            Р—Р°С‚РІРµСЂРґРёС‚Рё
          </UButton>
          <UButton
            class="w-full"
            variant="outline"
            :disabled="isViewingPreviousTour"
            @click="openProposalsModal"
          >
            РЈСЃС– РїСЂРѕРїРѕР·РёС†С–С—
          </UButton>
        </template>
      </aside>
    </div>

    <UModal v-model:open="showPublishModal">
      <template #content>
        <UCard>
          <template #header><h3>РџРµСЂС–РѕРґ РїСЂРѕРІРµРґРµРЅРЅСЏ</h3></template>
          <div class="space-y-4">
            <UFormField label="РџРѕС‡Р°С‚РѕРє">
              <UInput v-model="timingForm.start_at" type="datetime-local" />
            </UFormField>
            <UFormField label="Р—Р°РІРµСЂС€РµРЅРЅСЏ">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="publishTender"
                >РџС–РґС‚РІРµСЂРґРёС‚Рё</UButton
              >
              <UButton
                class="flex-1"
                variant="outline"
                @click="showPublishModal = false"
                >РЎРєР°СЃСѓРІР°С‚Рё</UButton
              >
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showInviteByEmailModal">
      <template #content>
        <UCard>
          <template #header><h3>Р—Р°РїСЂРѕС€РµРЅРЅСЏ РїРѕ email</h3></template>
          <div class="space-y-4">
            <UFormField
              label="Р’РІРµРґС–С‚СЊ email (РєРѕР¶РµРЅ Р· РЅРѕРІРѕРіРѕ СЂСЏРґРєР°) Р°Р±Рѕ Р·Р°РІР°РЅС‚Р°Р¶С‚Рµ СЃРїРёСЃРѕРє"
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
                Р—Р°РІР°РЅС‚Р°Р¶РёС‚Рё СЃРїРёСЃРѕРє
              </UButton>
              <span class="text-xs text-gray-500"
                >Р¤Р°Р№Р»: РѕРґРёРЅ email РЅР° СЂСЏРґРѕРє</span
              >
            </div>
            <div class="flex gap-2">
              <UButton class="flex-1" @click="submitInviteByEmail">
                Р—Р°РїСЂРѕСЃРёС‚Рё
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showInviteByEmailModal = false"
              >
                РЎРєР°СЃСѓРІР°С‚Рё
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showTimingModal">
      <template #content>
        <UCard>
          <template #header><h3>Р—РјС–РЅРёС‚Рё С‡Р°СЃ РїСЂРѕРІРµРґРµРЅРЅСЏ</h3></template>
          <div class="space-y-4">
            <UFormField
              label="РџРѕС‡Р°С‚РѕРє"
              :help="
                canEditStart
                  ? ''
                  : 'РџС–СЃР»СЏ СЃС‚Р°СЂС‚Сѓ С‡Р°СЃ РїРѕС‡Р°С‚РєСѓ Р·РјС–РЅСЋРІР°С‚Рё РЅРµ РјРѕР¶РЅР°'
              "
            >
              <UInput
                v-model="timingForm.start_at"
                type="datetime-local"
                :disabled="!canEditStart"
              />
            </UFormField>
            <UFormField label="Р—Р°РІРµСЂС€РµРЅРЅСЏ">
              <UInput v-model="timingForm.end_at" type="datetime-local" />
            </UFormField>
            <div class="flex gap-2">
              <UButton
                class="flex-1"
                :disabled="isViewingPreviousTour"
                @click="saveTiming"
              >
                Р—Р±РµСЂРµРіС‚Рё
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                @click="showTimingModal = false"
              >
                РЎРєР°СЃСѓРІР°С‚Рё
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showResumeAcceptanceModal">
      <template #content>
        <UCard>
          <template #header><h3>Р’С–РґРЅРѕРІРёС‚Рё РїСЂРёР№РѕРј РїСЂРѕРїРѕР·РёС†С–Р№</h3></template>
          <p class="text-sm text-gray-600 mb-4">
            Р’РєР°Р¶С–С‚СЊ С‡Р°СЃ РїРѕС‡Р°С‚РєСѓ (РЅРµ СЂР°РЅС–С€Рµ РїРѕС‚РѕС‡РЅРѕРіРѕ) С‚Р° С‡Р°СЃ Р·Р°РІРµСЂС€РµРЅРЅСЏ РїСЂРёР№РѕРјСѓ
            РїСЂРѕРїРѕР·РёС†С–Р№.
          </p>
          <div class="space-y-4">
            <UFormField label="РџРѕС‡Р°С‚РѕРє РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№" required>
              <UInput
                v-model="resumeAcceptanceForm.start_at"
                type="datetime-local"
                :min="resumeAcceptanceMinStart"
              />
            </UFormField>
            <UFormField label="Р—Р°РІРµСЂС€РµРЅРЅСЏ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№" required>
              <UInput
                v-model="resumeAcceptanceForm.end_at"
                type="datetime-local"
              />
            </UFormField>
            <div class="flex gap-2">
              <UButton
                class="flex-1"
                :disabled="resumeAcceptanceSaving"
                @click="submitResumeAcceptance"
              >
                Р’С–РґРЅРѕРІРёС‚Рё
              </UButton>
              <UButton
                class="flex-1"
                variant="outline"
                :disabled="resumeAcceptanceSaving"
                @click="showResumeAcceptanceModal = false"
              >
                РЎРєР°СЃСѓРІР°С‚Рё
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showWinnerModal">
      <template #content>
        <UCard>
          <template #header><h3>Р СѓС‡РЅРёР№ РІРёР±С–СЂ РїРµСЂРµРјРѕР¶С†СЏ</h3></template>
          <p class="text-sm text-gray-600 mb-4">
            РћР±РµСЂС–С‚СЊ РїРµСЂРµРјРѕР¶С†СЏ РїРѕ РєРѕР¶РЅС–Р№ РїРѕР·РёС†С–С— Р· РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ, СЏРєС– РїРѕРґР°Р»Рё
            РїСЂРѕРїРѕР·РёС†С–С—.
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
                :items="decisionWinnerOptionsForPosition(pos.id)"
                value-key="value"
                placeholder="РћР±РµСЂС–С‚СЊ РєРѕРЅС‚СЂР°РіРµРЅС‚Р°"
                class="flex-1 min-w-[200px]"
                @update:model-value="(v) => setDecisionWinner(pos.id, v)"
              />
            </div>
          </div>
          <template #footer>
            <UButton @click="showWinnerModal = false">Р—Р°РєСЂРёС‚Рё</UButton>
          </template>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showDecisionModal">
      <template #content>
        <UCard>
          <template #header><h3>Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ</h3></template>
          <div class="space-y-2">
            <UButton class="w-full" @click="fixDecision('winner')">
              Р—Р°РєСЂРёС‚Рё С–Р· РїРµСЂРµРјРѕР¶С†СЏРјРё
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="fixDecision('next_round')"
            >
              РџРµСЂРµРЅРµСЃС‚Рё РЅР° РЅР°СЃС‚СѓРїРЅРёР№ С‚СѓСЂ
            </UButton>
            <UButton
              class="w-full"
              variant="outline"
              @click="fixDecision('cancel')"
            >
              РЎРєР°СЃСѓРІР°С‚Рё
            </UButton>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal
      v-model:open="showProposalsModal"
      :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
    >
      <template #content>
        <UCard class="flex flex-col max-h-[90vh] overflow-hidden">
          <template #header>
            <h3 class="text-lg font-semibold">РЈСЃС– РїСЂРѕРїРѕР·РёС†С–С—</h3>
          </template>
          <div
            class="overflow-auto min-h-0 flex-1 resize-y min-h-[300px]"
            style="resize: vertical"
          >
            <table
              v-if="
                proposalComparisonPositions.length && decisionProposals.length
              "
              class="w-full text-sm border-collapse"
            >
              <thead>
                <tr class="border-b bg-gray-100">
                  <th
                    class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                  >
                    РќР°Р·РІР° РїРѕР·РёС†С–С—
                  </th>
                  <th
                    class="text-left p-2 font-medium bg-gray-100 whitespace-nowrap"
                  >
                    РљС–Р»СЊРєС–СЃС‚СЊ
                  </th>
                  <template
                    v-for="proposal in decisionProposals"
                    :key="proposal.id"
                  >
                    <th
                      :colspan="2 + (tender.value?.criteria?.length ?? 0)"
                      class="text-left p-2 font-medium bg-gray-200 border-l border-gray-300"
                    >
                      {{
                        proposal.supplier_company?.name ||
                        proposal.supplier_name ||
                        "вЂ”"
                      }}
                      <span
                        v-if="proposal.supplier_company?.edrpou"
                        class="text-gray-600 font-normal"
                        >({{ proposal.supplier_company.edrpou }})</span
                      >
                    </th>
                  </template>
                </tr>
                <tr class="border-b bg-gray-50">
                  <th class="p-2 bg-gray-50"></th>
                  <th class="p-2 bg-gray-50"></th>
                  <template
                    v-for="proposal in decisionProposals"
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
                      РЎСѓРјР°
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
                  class="border-b hover:bg-gray-50/50"
                >
                  <td class="p-2 bg-white whitespace-nowrap">{{ pos.name }}</td>
                  <td class="p-2 bg-white whitespace-nowrap">
                    {{ pos.quantity }} {{ pos.unit_name || "" }}
                  </td>
                  <template
                    v-for="proposal in decisionProposals"
                    :key="proposal.id"
                  >
                    <td
                      class="p-2 border-l border-gray-200"
                      :class="
                        (proposalComparisonByPosition[pos.id]?.bestId ===
                          proposal.id &&
                          'bg-green-500/20') ||
                        (proposalComparisonByPosition[pos.id]?.worstId ===
                          proposal.id &&
                          proposalComparisonByPosition[pos.id]?.worstId !==
                            proposalComparisonByPosition[pos.id]?.bestId &&
                          'bg-red-500/20')
                      "
                    >
                      {{
                        getProposalPositionValue(proposal, pos.id)?.price ?? "вЂ”"
                      }}
                    </td>
                    <td
                      class="p-2 border-l border-gray-200"
                      :class="
                        (proposalComparisonByPosition[pos.id]?.bestId ===
                          proposal.id &&
                          'bg-green-500/20') ||
                        (proposalComparisonByPosition[pos.id]?.worstId ===
                          proposal.id &&
                          proposalComparisonByPosition[pos.id]?.worstId !==
                            proposalComparisonByPosition[pos.id]?.bestId &&
                          'bg-red-500/20')
                      "
                    >
                      {{ getProposalPositionSum(proposal, pos) ?? "вЂ”" }}
                    </td>
                    <td
                      v-for="c in tender.value?.criteria ?? []"
                      :key="c.id"
                      class="p-2 border-l border-gray-200"
                    >
                      {{
                        getProposalCriterionValue(proposal, pos.id, c.id) ?? "вЂ”"
                      }}
                    </td>
                  </template>
                </tr>
              </tbody>
            </table>
            <p v-else class="text-gray-500 py-8 text-center">
              РќРµРјР°С” РїРѕР·РёС†С–Р№ Р°Р±Рѕ РїСЂРѕРїРѕР·РёС†С–Р№ РґР»СЏ РїРѕСЂС–РІРЅСЏРЅРЅСЏ.
            </p>
          </div>
        </UCard>
      </template>
    </UModal>

        <UModal
      v-model:open="showParticipantProposalModal"
      :ui="{ width: 'max-w-[95vw]', height: 'max-h-[90vh]' }"
    >
      <template #content>
        <UCard class="flex flex-col max-h-[90vh] overflow-hidden">
          <template #header>
            <h3 class="text-lg font-semibold">
              Пропозиція:
              {{ selectedParticipantProposal?.supplier_company?.name || selectedParticipantProposal?.supplier_name || "—" }}
            </h3>
          </template>
          <div class="overflow-auto min-h-0 flex-1">
            <table class="w-full text-sm border-collapse">
              <thead>
                <tr class="border-b bg-gray-100">
                  <th class="text-left p-2 font-medium">Позиція</th>
                  <th class="text-left p-2 font-medium">Кількість</th>
                  <th class="text-left p-2 font-medium">{{ proposalComparisonPriceHeader }}</th>
                  <th
                    v-for="c in (tender.value?.criteria ?? [])"
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
                  class="border-b hover:bg-gray-50/50"
                >
                  <td class="p-2">{{ pos.name }}</td>
                  <td class="p-2">{{ pos.quantity }} {{ pos.unit_name || "" }}</td>
                  <td class="p-2">
                    {{ getProposalPositionValue(selectedParticipantProposal, pos.id)?.price ?? "—" }}
                  </td>
                  <td
                    v-for="c in (tender.value?.criteria ?? [])"
                    :key="c.id"
                    class="p-2"
                  >
                    {{ getProposalCriterionValue(selectedParticipantProposal, pos.id, c.id) ?? "—" }}
                  </td>
                </tr>
                <tr v-if="!displayTenderPositions.length">
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
      v-model:open="showAttachedFilesModal"
      :ui="{ content: 'w-[calc(100vw-2rem)] !max-w-4xl' }"
    >
      <template #content>
        <UCard class="min-w-0">
          <template #header><h3>РџСЂРёРєСЂС–РїР»РµРЅС– С„Р°Р№Р»Рё</h3></template>
          <div class="space-y-4 min-w-0">
            <div>
              <input
                ref="attachedFilesInput"
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,image/*"
                class="hidden"
                @change="onAttachedFilesInputChange"
              />
              <UButton
                variant="outline"
                icon="i-heroicons-arrow-up-tray"
                :loading="attachedFilesUploading"
                @click="attachedFilesInput?.click()"
              >
                РћР±СЂР°С‚Рё С„Р°Р№Р»Рё
              </UButton>
            </div>
            <div v-if="attachedFilesLoading" class="flex justify-center py-4">
              <UIcon
                name="i-heroicons-arrow-path"
                class="animate-spin size-6 text-gray-400"
              />
            </div>
            <div
              v-else-if="attachedFilesList.length"
              class="min-w-0 overflow-hidden"
            >
              <table class="w-full min-w-0 text-sm border-collapse table-fixed">
                <thead>
                  <tr class="border-b border-gray-200 bg-gray-50">
                    <th
                      class="text-left py-2 px-3 font-medium text-gray-700 w-10"
                    >
                      Р’РёРґРёРјС–СЃС‚СЊ
                    </th>
                    <th class="text-left py-2 px-3 font-medium text-gray-700">
                      Р¤Р°Р№Р»
                    </th>
                    <th
                      class="text-left py-2 px-3 font-medium text-gray-700 w-36"
                    >
                      Р”Р°С‚Р°
                    </th>
                    <th class="text-left py-2 px-3 font-medium text-gray-700">
                      РљРѕСЂРёСЃС‚СѓРІР°С‡
                    </th>
                    <th class="w-24" />
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="f in attachedFilesList"
                    :key="f.id"
                    class="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td class="py-2 px-3 w-10">
                      <UCheckbox
                        :model-value="f.visible_to_participants"
                        @update:model-value="toggleFileVisibility(f.id, $event)"
                      />
                    </td>
                    <td class="py-2 px-3 min-w-0 truncate" :title="f.name">
                      {{ f.name }}
                    </td>
                    <td class="py-2 px-3 text-gray-600 truncate w-36">
                      {{ formatFileDate(f.uploaded_at) }}
                    </td>
                    <td class="py-2 px-3 text-gray-600 min-w-0 truncate">
                      {{ f.uploaded_by_display || "вЂ”" }}
                    </td>
                    <td class="py-2 px-3 w-24">
                      <div class="flex items-center gap-1">
                        <UButton
                          variant="ghost"
                          size="xs"
                          icon="i-heroicons-arrow-down-tray"
                          :to="f.file_url"
                          target="_blank"
                          rel="noopener"
                          title="РЎРєР°С‡Р°С‚Рё"
                        />
                        <UButton
                          variant="ghost"
                          size="xs"
                          icon="i-heroicons-trash"
                          color="error"
                          title="Р’РёРґР°Р»РёС‚Рё"
                          @click="deleteAttachedFile(f.id)"
                        />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="text-sm text-gray-500 py-2">
              РќРµРјР°С” РїСЂРёРєСЂС–РїР»РµРЅРёС… С„Р°Р№Р»С–РІ.
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showCreateCriterionModal">
      <template #content>
        <UCard>
          <template #header><h3>РЎС‚РІРѕСЂРёС‚Рё РєСЂРёС‚РµСЂС–Р№</h3></template>
          <div class="space-y-4">
            <UFormField label="РќР°Р·РІР° РєСЂРёС‚РµСЂС–СЏ" required>
              <UInput
                v-model="createCriterionForm.name"
                placeholder="РќР°РїСЂРёРєР»Р°Рґ: Р¦С–РЅР° Р·Р° РѕРґРёРЅРёС†СЋ"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <UFormField label="РўРёРї РєСЂРёС‚РµСЂС–СЏ" required>
              <USelectMenu
                v-model="createCriterionForm.type"
                :items="criterionTypeOptions"
                value-key="value"
                placeholder="РћР±РµСЂС–С‚СЊ С‚РёРї"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <UFormField label="Р—Р°СЃС‚РѕСЃСѓРІР°РЅРЅСЏ" required>
              <USelectMenu
                v-model="createCriterionForm.application"
                :items="criterionApplicationOptions"
                value-key="value"
                placeholder="РћР±РµСЂС–С‚СЊ Р·Р°СЃС‚РѕСЃСѓРІР°РЅРЅСЏ"
                :disabled="createCriterionSaving"
              />
            </UFormField>
            <div class="flex gap-2 justify-end pt-2">
              <UButton
                variant="outline"
                :disabled="createCriterionSaving"
                @click="showCreateCriterionModal = false"
              >
                РЎРєР°СЃСѓРІР°С‚Рё
              </UButton>
              <UButton
                :loading="createCriterionSaving"
                @click="saveCreateCriterion"
              >
                РЎС‚РІРѕСЂРёС‚Рё С‚Р° РґРѕРґР°С‚Рё
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showCreateNomenclatureModal">
      <template #content>
        <UCard>
          <template #header><h3>РЎС‚РІРѕСЂРёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ</h3></template>
          <div class="space-y-4">
            <p class="text-sm text-gray-600">
              РќРѕРјРµРЅРєР»Р°С‚СѓСЂР° Р±СѓРґРµ СЃС‚РІРѕСЂРµРЅР° РІ РґРѕРІС–РґРЅРёРєСѓ, РїСЂРёРІКјСЏР·Р°РЅР° РґРѕ РєР°С‚РµРіРѕСЂС–Р№
              CPV Р· РїР°СЃРїРѕСЂС‚Р° С‚РµРЅРґРµСЂР° С‚Р° РґРѕРґР°РЅР° РґРѕ РїРѕР·РёС†С–Р№ С‚РµРЅРґРµСЂР°.
            </p>
            <UFormField label="РќР°Р·РІР° РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё" required>
              <UInput
                v-model="createNomenclatureForm.name"
                placeholder="Р’РІРµРґС–С‚СЊ РЅР°Р·РІСѓ"
                :disabled="createNomenclatureSaving"
              />
            </UFormField>
            <UFormField label="РћРґРёРЅРёС†СЏ РІРёРјС–СЂСѓ" required>
              <USelectMenu
                v-model="createNomenclatureForm.unit"
                :items="createNomenclatureUnitOptions"
                value-key="value"
                placeholder="РћР±РµСЂС–С‚СЊ РѕРґРёРЅРёС†СЋ РІРёРјС–СЂСѓ"
                :disabled="createNomenclatureSaving"
              />
            </UFormField>
            <div class="flex gap-2 justify-end">
              <UButton
                variant="outline"
                :disabled="createNomenclatureSaving"
                @click="showCreateNomenclatureModal = false"
              >
                РЎРєР°СЃСѓРІР°С‚Рё
              </UButton>
              <UButton
                :loading="createNomenclatureSaving"
                @click="submitCreateNomenclature"
              >
                РЎС‚РІРѕСЂРёС‚Рё С‚Р° РґРѕРґР°С‚Рё
              </UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { TextAlign } from "@tiptap/extension-text-align";
import { TENDER_STAGE_ITEMS } from "~/domains/tenders/tenders.constants";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "РўРµРЅРґРµСЂ РЅР° РїСЂРѕРґР°Р¶" },
});

const route = useRoute();
const tenderId = computed(() => Number(route.params.id));
const isSales = true;
const tendersUC = useTendersUseCases();
const { me } = useMe();
const myCompanyId = computed(
  () => (me.value as { memberships?: Array<{ company?: { id?: number } }> })?.memberships?.[0]?.company?.id ?? null,
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
const tourOptions = ref<{ value: number; label: string }[]>([]);
const prepTab = ref<"positions" | "criteria">("positions");
const prepTabs = [
  { label: "РџРѕР·РёС†С–С—", value: "positions" },
  { label: "РљСЂРёС‚РµСЂС–С—", value: "criteria" },
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

// РџР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЏ
const priceCriterionVat = ref<string | undefined>(undefined);
const priceCriterionDelivery = ref<string | undefined>(undefined);
const vatOptions = [
  { value: "with_vat", label: "Р· РџР”Р’" },
  { value: "without_vat", label: "Р±РµР· РџР”Р’" },
];
const deliveryOptions = [
  { value: "with_delivery", label: "Р†Р· СѓСЂР°С…СѓРІР°РЅРЅСЏРј РґРѕСЃС‚Р°РІРєРё" },
  { value: "without_delivery", label: "Р‘РµР· СѓСЂР°С…СѓРІР°РЅРЅСЏ РґРѕСЃС‚Р°РІРєРё" },
];

// РљСЂРёС‚РµСЂС–С— Р· РґРѕРІС–РґРЅРёРєР° С‚Р° РґРѕРґР°РЅС– РґРѕ С‚РµРЅРґРµСЂР°
const referenceCriteria = ref<any[]>([]);
const tenderCriteria = ref<any[]>([]);
const criteriaSearch = ref("");

const categorySearch = ref("");
const nomenclatureSearch = ref("");
const loadingNomenclatures = ref(false);
const tenderPositions = ref<any[]>([]);
/** РџРѕР·РёС†С–С— РґР»СЏ РІС–РґРѕР±СЂР°Р¶РµРЅРЅСЏ: Р· API (tender.positions) Р°Р±Рѕ Р»РѕРєР°Р»СЊРЅРёР№ ref (РґР»СЏ РІР»Р°СЃРЅРёРєР° РїС–СЃР»СЏ loadTender). */
const displayTenderPositions = computed(() => {
  const raw = tender.value?.positions;
  if (Array.isArray(raw) && raw.length > 0) {
    return raw.map((p: any) => ({
      id: p.id,
      nomenclature_id: p.nomenclature_id ?? p.nomenclature,
      name: p.name,
      unit_name: p.unit_name ?? "",
      quantity: p.quantity ?? 1,
      description: p.description ?? "",
    }));
  }
  return tenderPositions.value;
});
const availableNomenclatures = ref<any[]>([]);

const showPublishModal = ref(false);
const showTimingModal = ref(false);
const showDecisionModal = ref(false);
const showResumeAcceptanceModal = ref(false);
const resumeAcceptanceForm = reactive({ start_at: "", end_at: "" });
const resumeAcceptanceSaving = ref(false);
const showWinnerModal = ref(false);
const showInvitationPanel = ref(false);
const showInviteByEmailModal = ref(false);
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
const attachedFilesInput = ref<HTMLInputElement | null>(null);
const showCreateNomenclatureModal = ref(false);
const createNomenclatureForm = reactive({
  name: "",
  unit: null as number | null,
});
const createNomenclatureSaving = ref(false);
const createNomenclatureUnits = ref<
  { id: number; name_ua?: string; short_name_ua?: string; name_en?: string }[]
>([]);
const timingForm = reactive({ start_at: "", end_at: "" });

// Р—Р°РїСЂРѕС€РµРЅРЅСЏ СѓС‡Р°СЃРЅРёРєС–РІ: РєРѕРЅС‚СЂР°РіРµРЅС‚Рё С‚Р° email
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

const createNomenclatureUnitOptions = computed(() =>
  createNomenclatureUnits.value.map((u) => ({
    value: u.id,
    label: u.short_name_ua || u.name_ua || u.name_en || String(u.id),
  })),
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
  return (
    invitationCpvOptions.value.find((o) => o.id === id)?.label ??
    cpvWithCompaniesList.value.find((c) => c.id === id)?.label ??
    `#${id}`
  );
}

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
const estimatedMarketMethod = ref("arithmetic_mean");
const estimatedMarketOptions = [
  { value: "arithmetic_mean", label: "РЎРµСЂРµРґРЅСЏ Р°СЂРёС„РјРµС‚РёС‡РЅР°" },
];
const selectedWinnerByPosition = ref<Record<number, number>>({});

const stageItems = TENDER_STAGE_ITEMS;

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

const conductTypeOptions = computed(() => {
  // Р”Р»СЏ С‚РµРЅРґРµСЂС–РІ Р· С‚РёРїРѕРј "Р РµС”СЃС‚СЂР°С†С–СЏ" Р·Р°РІР¶РґРё РїРѕРєР°Р·СѓС”РјРѕ Р»РёС€Рµ С†РµР№ РІР°СЂС–Р°РЅС‚
  if (isRegistration.value) {
    return [{ value: "registration", label: "Р РµС”СЃС‚СЂР°С†С–СЏ РїСЂРѕРґР°Р¶Сѓ" }];
  }
  const tour = tender.value?.tour_number ?? 1;
  if (tour <= 1) {
    // РџРµСЂС€РёР№ С‚СѓСЂ: С‚С–Р»СЊРєРё Р—Р±С–СЂ РїСЂРѕРїРѕР·РёС†С–Р№ С‚Р° РћРЅР»Р°Р№РЅ С‚РѕСЂРіРё
    return [
      { value: "rfx", label: "Р—Р±С–СЂ РїСЂРѕРїРѕР·РёС†С–Р№ (RFx)" },
      { value: "online_auction", label: "РћРЅР»Р°Р№РЅ С‚РѕСЂРіРё" },
    ];
  }
  // 2-Р№ С‚Р° РїРѕРґР°Р»СЊС€С– С‚СѓСЂРё: СѓСЃС– С‚СЂРё РІР°СЂС–Р°РЅС‚Рё
  return [
    { value: "registration", label: "Р РµС”СЃС‚СЂР°С†С–СЏ РїСЂРѕРґР°Р¶Сѓ" },
    { value: "rfx", label: "Р—Р±С–СЂ РїСЂРѕРїРѕР·РёС†С–Р№ (RFx)" },
    { value: "online_auction", label: "РћРЅР»Р°Р№РЅ С‚РѕСЂРіРё" },
  ];
});
const publicationTypeOptions = [
  { value: "open", label: "Р’С–РґРєСЂРёС‚Р° РїСЂРѕС†РµРґСѓСЂР°" },
  { value: "closed", label: "Р—Р°РєСЂРёС‚Р° РїСЂРѕС†РµРґСѓСЂР°" },
];

const categoryTree = ref<any[]>([]);
const expenseOptions = ref<{ value: number; label: string }[]>([]);
const branchOptions = ref<{ value: number; label: string }[]>([]);
const departmentOptions = ref<{ value: number; label: string }[]>([]);
const currencyOptions = ref<{ value: number; label: string }[]>([]);
const positionsColumns = [
  { accessorKey: "name", header: "РќР°Р·РІР°" },
  { accessorKey: "unit_name", header: "РћРґ. РІРёРјС–СЂСѓ" },
  { accessorKey: "quantity", header: "РљС–Р»СЊРєС–СЃС‚СЊ" },
  { accessorKey: "description", header: "РћРїРёСЃ" },
  { accessorKey: "vat", header: "РџР”Р’" },
  { accessorKey: "actions", header: "", cellClass: "w-12" },
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
        p.supplier_name ?? p.supplier_company?.name ?? `РџСЂРѕРїРѕР·РёС†С–СЏ #${p.id}`,
    }));
}

function setDecisionWinner(positionId: number, proposalId: number | null) {
  const next = { ...selectedWinnerByPosition.value };
  if (proposalId != null) next[positionId] = proposalId;
  else delete next[positionId];
  selectedWinnerByPosition.value = next;
}

const decisionTableColumns = [
  { accessorKey: "name", header: "РџРѕР·РёС†С–СЏ" },
  { accessorKey: "quantity_unit", header: "РљС–Р»СЊРєС–СЃС‚СЊ" },
  { accessorKey: "market_value", header: "РћСЂС–С”РЅС‚РѕРІРЅР° СЂРёРЅРєРѕРІР°" },
  { accessorKey: "best_counterparty", header: "РљСЂР°С‰РёР№ РєРѕРЅС‚СЂР°РіРµРЅС‚" },
  { accessorKey: "best_price", header: "РљСЂР°С‰Р° С†С–РЅР°" },
  { accessorKey: "selected_counterparty", header: "РљРѕРЅС‚СЂР°РіРµРЅС‚ С‰Рѕ РѕР±РёСЂР°С”С‚СЊСЃСЏ" },
  { accessorKey: "selected_price", header: "Р¦С–РЅР° С‰Рѕ РѕР±РёСЂР°С”С‚СЊСЃСЏ" },
  { accessorKey: "price_diff", header: "Р РѕР·Р±С–Р¶РЅС–СЃС‚СЊ Сѓ С†С–РЅС–" },
  { accessorKey: "profit_market", header: "РџСЂРёР±СѓС‚РѕРє РїРѕ РѕСЂС–С”РЅС‚РѕРІРЅС–Р№ СЂРёРЅРєРѕРІС–Р№" },
];

const decisionTableRows = computed(() => {
  const proposals = decisionProposals.value;
  const selected = selectedWinnerByPosition.value;
  const isPurchase = false;
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
    const avgPrice =
      prices.length > 0
        ? prices.reduce((a, b) => a + b, 0) / prices.length
        : null;
    const marketValue =
      estimatedMarketMethod.value === "arithmetic_mean" && avgPrice != null
        ? avgPrice.toFixed(2)
        : avgPrice != null
          ? avgPrice.toFixed(2)
          : "вЂ”";

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
      "вЂ”";
    const bestPriceStr = bestPrice != null ? bestPrice.toFixed(2) : "вЂ”";

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
      "вЂ”";
    const selectedPriceStr =
      selectedPrice != null ? selectedPrice.toFixed(2) : "вЂ”";

    const priceDiff =
      bestPrice != null && selectedPrice != null
        ? selectedPrice - bestPrice
        : null;
    const priceDiffStr = priceDiff != null ? priceDiff.toFixed(2) : "вЂ”";

    const profitMarket =
      avgPrice != null && selectedPrice != null
        ? selectedPrice - avgPrice
        : null;
    const profitMarketStr =
      profitMarket != null ? profitMarket.toFixed(2) : "вЂ”";

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
      profit_market: profitMarketStr,
    };
  });
});

/** Р”РµСЂРµРІРѕ РґР»СЏ UTree (Nuxt UI): РєР°С‚РµРіРѕСЂС–С— (Р±Р°С‚СЊРєРё) в†’ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё (РґС–С‚Рё), С„РѕСЂРјР°С‚ TreeItem */
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
    label = findCategoryNameById(categoryTree.value, categoryId) || "РљР°С‚РµРіРѕСЂС–СЏ";
    id = `cat-${categoryId}`;
  } else if (cpvIds.length > 0 && cpvLabels.length > 0) {
    label =
      cpvLabels.length === 1 ? (cpvLabels[0] ?? "") : cpvLabels.join(", ");
    id = `cpv-${cpvIds.join("-")}`;
  } else {
    label = "РќРѕРјРµРЅРєР»Р°С‚СѓСЂРё";
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
  if (isLeaf && isDoubleClick && item.id != null) {
    const numId = typeof item.id === "number" ? item.id : Number(item.id);
    if (!Number.isNaN(numId)) addPositionFromNomenclature(numId);
  }
  if (
    typeof (orig as { preventDefault?: () => void })?.preventDefault ===
    "function"
  )
    (orig as { preventDefault: () => void }).preventDefault();
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
          ? "Р”РѕРґР°Р№С‚Рµ С…РѕС‡Р° Р± РѕРґРЅСѓ РїРѕР·РёС†С–СЋ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё РІ С‚РµРЅРґРµСЂ."
          : !priceCriterionVat.value || !priceCriterionDelivery.value
            ? "РќР°Р»Р°С€С‚СѓР№С‚Рµ РїР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЏ (РџР”Р’ С‚Р° Р”РѕСЃС‚Р°РІРєР°)."
            : "";
      alert(msg || "РќРµРјРѕР¶Р»РёРІРѕ РІС–РґРєСЂРёС‚Рё РїРѕРґР°С‡Сѓ РїСЂРѕРїРѕР·РёС†С–Р№.");
      return;
    }
    await navigateTo(`/cabinet/tenders/sales/proposals/${tenderId.value}`);
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

function openParticipantProposalModal(proposal: any) {
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
      title: "РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ СЃРїРёСЃРєСѓ С„Р°Р№Р»С–РІ",
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
      title: "Р’РєР°Р¶С–С‚СЊ РЅР°Р·РІСѓ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё",
      color: "error",
    });
    return;
  }
  if (createNomenclatureForm.unit == null) {
    useToast().add({
      title: "РћР±РµСЂС–С‚СЊ РѕРґРёРЅРёС†СЋ РІРёРјС–СЂСѓ",
      color: "error",
    });
    return;
  }
  const companyId = tender.value?.company;
  if (!companyId) {
    useToast().add({
      title: "РџРѕРјРёР»РєР°",
      description: "РўРµРЅРґРµСЂ РЅРµ РїСЂРёРІКјСЏР·Р°РЅРёР№ РґРѕ РєРѕРјРїР°РЅС–С—.",
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
        title: "РџРѕРјРёР»РєР° СЃС‚РІРѕСЂРµРЅРЅСЏ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё",
        description: typeof createError === "string" ? createError : "",
        color: "error",
      });
      return;
    }
    const newPositions = [
      ...tenderPositions.value.map((p) => ({
        nomenclature_id: p.nomenclature_id,
        quantity: p.quantity ?? 1,
        description: p.description ?? "",
      })),
      {
        nomenclature_id: created.id,
        quantity: 1,
        description: "",
      },
    ];
    const ok = await patchTender({ positions: newPositions });
    if (ok && Array.isArray(tender.value?.positions)) {
      tenderPositions.value = tender.value.positions.map((p: any) => ({
        id: p.id,
        nomenclature_id: p.nomenclature,
        name: p.name,
        unit_name: p.unit_name ?? "",
        quantity: p.quantity ?? 1,
        description: p.description ?? "",
      }));
    }
    showCreateNomenclatureModal.value = false;
    useToast().add({
      title: "РќРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ СЃС‚РІРѕСЂРµРЅРѕ С‚Р° РґРѕРґР°РЅРѕ РґРѕ РїРѕР·РёС†С–Р№",
      color: "success",
    });
    await loadNomenclaturesForPreparation();
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
        title: "РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ",
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
      title: "РџРѕРјРёР»РєР° РІРёРґР°Р»РµРЅРЅСЏ",
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
      title: "РџРѕРјРёР»РєР° РѕРЅРѕРІР»РµРЅРЅСЏ",
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
    numeric: "Р§РёСЃР»РѕРІРёР№",
    text: "РўРµРєСЃС‚РѕРІРёР№",
    file: "Р¤Р°Р№Р»РѕРІРёР№",
    boolean: "Р‘СѓР»РµРІРёР№",
  };
  return map[type] ?? type;
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
  options: {} as Record<string, unknown>,
});
const createCriterionSaving = ref(false);
const criterionTypeOptions = [
  { value: "numeric", label: "Р§РёСЃР»РѕРІРёР№" },
  { value: "text", label: "РўРµРєСЃС‚РѕРІРёР№" },
  { value: "file", label: "Р¤Р°Р№Р»РѕРІРёР№" },
  { value: "boolean", label: "Р‘СѓР»РµРІРёР№ (РўР°Рє/РќС–)" },
];
const criterionApplicationOptions = [
  { value: "general", label: "Р—Р°РіР°Р»СЊРЅРёР№" },
  { value: "individual", label: "Р†РЅРґРёРІС–РґСѓР°Р»СЊРЅРёР№" },
];

function openCreateCriterionModal() {
  createCriterionForm.name = "";
  createCriterionForm.type = "numeric";
  createCriterionForm.application = "individual";
  createCriterionForm.options = {};
  showCreateCriterionModal.value = true;
}

async function saveCreateCriterion() {
  const name = (createCriterionForm.name || "").trim();
  if (!name) {
    useToast().add({ title: "Р’РєР°Р¶С–С‚СЊ РЅР°Р·РІСѓ РєСЂРёС‚РµСЂС–СЏ", color: "error" });
    return;
  }
  const companyId = tender.value?.company;
  if (!companyId) {
    useToast().add({
      title: "РўРµРЅРґРµСЂ РЅРµ РїСЂРёРІКјСЏР·Р°РЅРёР№ РґРѕ РєРѕРјРїР°РЅС–С—",
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
      application: createCriterionForm.application || "individual",
      options: createCriterionForm.options || {},
    });
    if (error || !created?.id) {
      useToast().add({
        title: "РџРѕРјРёР»РєР° СЃС‚РІРѕСЂРµРЅРЅСЏ РєСЂРёС‚РµСЂС–СЏ",
        description:
          typeof error === "string"
            ? error
            : "РљСЂРёС‚РµСЂС–Р№ Р· С‚Р°РєРѕСЋ РЅР°Р·РІРѕСЋ С‚Р° С‚РёРїРѕРј РІР¶Рµ С–СЃРЅСѓС”.",
        color: "error",
      });
      return;
    }
    const newIds = [
      ...(tenderCriteria.value || []).map((c: any) => c.id),
      created.id,
    ];
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
        },
      ];
    }
    showCreateCriterionModal.value = false;
    useToast().add({
      title: "РљСЂРёС‚РµСЂС–Р№ СЃС‚РІРѕСЂРµРЅРѕ С‚Р° РґРѕРґР°РЅРѕ РґРѕ С‚РµРЅРґРµСЂР°",
      color: "success",
    });
    await loadReferenceCriteria();
  } finally {
    createCriterionSaving.value = false;
  }
}

/** Р”РµСЂРµРІРѕ РґР»СЏ UTree: РѕРґРёРЅ Р±Р°С‚СЊРєС–РІСЃСЊРєРёР№ РІСѓР·РѕР» В«РљСЂРёС‚РµСЂС–С—В», РґС–С‚Рё вЂ” РєСЂРёС‚РµСЂС–С— Р· РґРѕРІС–РґРЅРёРєР° (Р· С„С–Р»СЊС‚СЂРѕРј РїРѕС€СѓРєСѓ) */
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
    { id: "criteria-root", label: "РљСЂРёС‚РµСЂС–С—", defaultExpanded: true, children },
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

/** Р”РѕРґР°С‚Рё РєСЂРёС‚РµСЂС–Р№ Р· РґРѕРІС–РґРЅРёРєР° (РїРѕРґРІС–Р№РЅРёР№ РєР»С–Рє Сѓ Р»С–РІС–Р№ РїР°РЅРµР»С–). РЇРєС‰Рѕ РІР¶Рµ С” вЂ” РЅС–С‡РѕРіРѕ РЅРµ СЂРѕР±РёРјРѕ. */
function addCriterionFromTree(criterionId: number) {
  if (isViewingPreviousTour.value) return;
  if (tenderCriteria.value.some((c) => c.id === criterionId)) return;
  const c = referenceCriteria.value.find((x: any) => x.id === criterionId);
  if (c) tenderCriteria.value = [...tenderCriteria.value, c];
}

async function loadReferenceCriteria() {
  loadingReferenceCriteria.value = true;
  try {
    const { data } = await tendersUC.getTenderCriteria();
    referenceCriteria.value = Array.isArray(data) ? data : [];
  } finally {
    loadingReferenceCriteria.value = false;
  }
}

function removeCriterionFromTender(c: any) {
  if (isViewingPreviousTour.value) return;
  tenderCriteria.value = tenderCriteria.value.filter((x) => x.id !== c.id);
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
    const loadFromParticipationList = async () => {
      const tabs: Array<"active" | "processing" | "completed"> = ["active", "processing", "completed"];
      for (const tab of tabs) {
        const { data } = await tendersUC.getTendersForParticipation(isSales, tab);
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
    const stage = tenderData.stage ?? "passport";
    displayStage.value =
      tenderData.conduct_type === "registration" && stage === "acceptance"
        ? "decision"
        : stage;
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
        quantity: p.quantity ?? 1,
        description: p.description ?? "",
      }));
    } else {
      tenderPositions.value = [];
    }
    priceCriterionVat.value = tenderData.price_criterion_vat ?? undefined;
    priceCriterionDelivery.value = tenderData.price_criterion_delivery ?? undefined;
    if (Array.isArray(tenderData.criteria)) {
      tenderCriteria.value = tenderData.criteria;
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
      publication_type: tenderData.publication_type ?? "open",
      currency: tenderData.currency ?? null,
      general_terms: tenderData.general_terms ?? "",
    });
    timingForm.start_at = isoToInput(tenderData.start_at);
    timingForm.end_at = isoToInput(tenderData.end_at);
    await loadTours();
    await autoAdvanceAcceptance();
  } finally {
    loading.value = false;
  }
}

async function loadTours() {
  if (!tenderId.value) return;
  const { data } = await tendersUC.getTenderTours(tenderId.value, isSales);
  // API РїРѕРІРµСЂС‚Р°С” [{ id, tour_number }]; С‚СѓСЂ 1 вЂ” РїРµСЂС€РёР№ (РєРѕСЂС–РЅСЊ), РЅР°СЃС‚СѓРїРЅС– вЂ” РїРѕРІС‚РѕСЂРЅС– РїСЂРѕРІРµРґРµРЅРЅСЏ
  tourOptions.value = Array.isArray(data)
    ? (data as { id: number; tour_number: number }[]).map((t) => ({
        value: t.id,
        label: `РўСѓСЂ ${t.tour_number ?? 1}`,
      }))
    : [];
}

function onTourSelect(value: number | null) {
  if (value != null && value !== tenderId.value) {
    navigateTo(`/cabinet/tenders/sales/${value}`);
  }
}

async function loadOptions() {
  const [cats, expenses, branches, currencies] = await Promise.all([
    tendersUC.getCategories(),
    tendersUC.getExpenses(),
    tendersUC.getBranches(),
    tendersUC.getCurrencies(),
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
    let items: any[] = [];

    if ((form.cpv_ids?.length ?? 0) > 0) {
      const merged = new Map<number, any>();
      for (const cpvId of form.cpv_ids) {
        const { data: byCpv } = await tendersUC.getNomenclaturesByCpv(cpvId);
        for (const n of (byCpv as any[]) || []) merged.set(n.id, n);
      }
      items = Array.from(merged.values());
    } else if (form.category) {
      const { data: byCategory } = await tendersUC.getNomenclaturesByCategory(
        form.category,
      );
      const merged = new Map<number, any>();
      for (const n of (byCategory as any[]) || []) merged.set(n.id, n);

      const { data: categoryData } = await tendersUC.getCategory(form.category);
      const cpvIds: number[] = ((categoryData as any)?.cpvs || []).map(
        (c: any) => c.id,
      );
      for (const cpvId of cpvIds) {
        const { data: byCpv } = await tendersUC.getNomenclaturesByCpv(cpvId);
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

/** Р”РѕРґР°С‚Рё РїРѕР·РёС†С–СЋ Р· РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё (РїРѕРґРІС–Р№РЅРёР№ РєР»С–Рє Сѓ Р»С–РІС–Р№ РїР°РЅРµР»С–). РЇРєС‰Рѕ РІР¶Рµ С” вЂ” РЅС–С‡РѕРіРѕ РЅРµ СЂРѕР±РёРјРѕ. */
function addPositionFromNomenclature(nomenclatureId: number) {
  if (isViewingPreviousTour.value) return;
  if (tenderPositions.value.some((p) => p.nomenclature_id === nomenclatureId)) {
    useToast().add({
      title: "Р¦СЏ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂР° РІР¶Рµ РґРѕРґР°РЅР° РґРѕ РїРѕР·РёС†С–Р№ С‚РµРЅРґРµСЂР°",
      color: "warning",
    });
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

/** Р’РёРґР°Р»РёС‚Рё РїРѕР·РёС†С–СЋ Р· С‚РµРЅРґРµСЂР° (Р·Р° СЂСЏРґРєРѕРј С‚Р°Р±Р»РёС†С–). */
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

async function loadDepartments() {
  if (!form.branch) {
    departmentOptions.value = [];
    return;
  }
  const { data } = await tendersUC.getDepartments(form.branch);
  departmentOptions.value = flattenTree((data as any[]) || []);
}

function onBranchChange() {
  form.department = null;
  loadDepartments();
}

async function patchTender(payload: Record<string, unknown>) {
  if (!tender.value?.id) return false;
  const { data, error } = await tendersUC.patchTender(
    tender.value.id,
    isSales,
    payload,
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
  const cpvIds = form.cpv_ids ?? [];
  if (cpvIds.length === 0) {
    useToast().add({
      title: "Р—Р°РїРѕРІРЅС–С‚СЊ РѕР±РѕРІКјСЏР·РєРѕРІРµ РїРѕР»Рµ",
      description: "РћР±РµСЂС–С‚СЊ С…РѕС‡Р° Р± РѕРґРЅСѓ РєР°С‚РµРіРѕСЂС–СЋ CPV.",
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
      publication_type: form.publication_type,
      currency: form.currency,
      general_terms: form.general_terms,
      stage: "preparation",
    });
    if (!ok) {
      useToast().add({
        title: "РџРѕРјРёР»РєР° Р·Р±РµСЂРµР¶РµРЅРЅСЏ",
        description: "РџРµСЂРµРІС–СЂС‚Рµ РґР°РЅС– (Р·РѕРєСЂРµРјР° РєР°С‚РµРіРѕСЂС–СЋ CPV).",
        color: "error",
      });
    }
  } finally {
    saving.value = false;
  }
}

const toast = useToast();
function openPublishModal() {
  const hasPositions = tenderPositions.value.length >= 1;
  const hasPriceParams =
    !!priceCriterionVat.value && !!priceCriterionDelivery.value;
  if (!hasPositions || !hasPriceParams) {
    const msg = !hasPositions
      ? "РџСѓР±Р»С–РєР°С†С–СЏ РЅРµРјРѕР¶Р»РёРІР°: РґРѕРґР°Р№С‚Рµ С…РѕС‡Р° Р± РѕРґРЅСѓ РїРѕР·РёС†С–СЋ С‚РµРЅРґРµСЂР°."
      : "РџСѓР±Р»С–РєР°С†С–СЏ РЅРµРјРѕР¶Р»РёРІР°: РЅР°Р»Р°С€С‚СѓР№С‚Рµ РїР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЏ (РџР”Р’ С‚Р° Р”РѕСЃС‚Р°РІРєР°).";
    toast.add({
      title: "РџСѓР±Р»С–РєР°С†С–СЏ РЅРµРјРѕР¶Р»РёРІР°",
      description: msg,
      color: "error",
    });
    return;
  }
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
  const prepared = await savePreparation();
  if (!prepared) {
    useToast().add({
      title: "РќРµ РІРґР°Р»РѕСЃСЏ Р·Р±РµСЂРµРіС‚Рё РїС–РґРіРѕС‚РѕРІРєСѓ С‚РµРЅРґРµСЂР°",
      description: "РџРµСЂРµРІС–СЂС‚Рµ РїРѕР·РёС†С–С—, РєСЂРёС‚РµСЂС–С— С‚Р° РїР°СЂР°РјРµС‚СЂРё С†С–РЅРѕРІРѕРіРѕ РєСЂРёС‚РµСЂС–СЋ.",
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

async function goBackToPreparation() {
  if (isViewingPreviousTour.value) return;
  const ok = await patchTender({ stage: "preparation" });
  if (ok) await loadTender();
}

const resumeAcceptanceMinStart = computed(() => {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 1, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
});

function openResumeAcceptanceModal() {
  const now = new Date();
  const end = new Date(now);
  end.setDate(end.getDate() + 1);
  const pad = (n: number) => String(n).padStart(2, "0");
  resumeAcceptanceForm.start_at = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  resumeAcceptanceForm.end_at = `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}T${pad(end.getHours())}:${pad(end.getMinutes())}`;
  showResumeAcceptanceModal.value = true;
}

async function submitResumeAcceptance() {
  const startStr = (resumeAcceptanceForm.start_at || "").trim();
  const endStr = (resumeAcceptanceForm.end_at || "").trim();
  if (!startStr || !endStr) {
    useToast().add({
      title: "Р—Р°РїРѕРІРЅС–С‚СЊ С‡Р°СЃ РїРѕС‡Р°С‚РєСѓ С‚Р° Р·Р°РІРµСЂС€РµРЅРЅСЏ",
      color: "error",
    });
    return;
  }
  const start = new Date(startStr);
  const end = new Date(endStr);
  const now = new Date();
  if (start < now) {
    useToast().add({
      title: "Р§Р°СЃ РїРѕС‡Р°С‚РєСѓ РЅРµ РјРѕР¶Рµ Р±СѓС‚Рё РјРµРЅС€РёРј РІС–Рґ РїРѕС‚РѕС‡РЅРѕРіРѕ",
      color: "error",
    });
    return;
  }
  if (end <= start) {
    useToast().add({
      title: "Р§Р°СЃ Р·Р°РІРµСЂС€РµРЅРЅСЏ РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РїС–Р·РЅС–С€Рµ Р·Р° С‡Р°СЃ РїРѕС‡Р°С‚РєСѓ",
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
        title: "РџСЂРёР№РѕРј РїСЂРѕРїРѕР·РёС†С–Р№ РІС–РґРЅРѕРІР»РµРЅРѕ",
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

async function fixDecision(mode: "winner" | "cancel" | "next_round") {
  showDecisionModal.value = false;
  saving.value = true;
  try {
    const body: {
      mode: string;
      position_winners?: { position_id: number; proposal_id: number }[];
    } = { mode };
    if (mode === "winner") {
      body.position_winners = Object.entries(
        selectedWinnerByPosition.value,
      ).map(([position_id, proposal_id]) => ({
        position_id: Number(position_id),
        proposal_id,
      }));
    }
    const { data, error } = await tendersUC.fixTenderDecision(
      tenderId.value,
      isSales,
      body,
    );
    if (error || !data) return;
    if (data.id && data.stage === "preparation") {
      await navigateTo(`/cabinet/tenders/sales/${data.id}`);
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
  const { data } = await tendersUC.getTenderProposals(tenderId.value, isSales);
  decisionProposals.value = Array.isArray(data) ? data : [];
  const next: Record<number, number> = {};
  for (const pos of displayTenderPositions.value) {
    const bestId = getBestProposalIdForPosition(pos.id, false);
    if (bestId != null) next[pos.id] = bestId;
  }
  selectedWinnerByPosition.value = next;
}

const proposalComparisonPositions = computed(
  () => tender.value?.positions ?? [],
);
const proposalComparisonPriceHeader = computed(() => {
  const v = tender.value?.price_criterion_vat;
  const d = tender.value?.price_criterion_delivery;
  const vatLabels: Record<string, string> = {
    with_vat: "Р· РџР”Р’",
    without_vat: "Р±РµР· РџР”Р’",
  };
  const deliveryLabels: Record<string, string> = {
    with_delivery: "С–Р· СѓСЂР°С…СѓРІР°РЅРЅСЏРј РґРѕСЃС‚Р°РІРєРё",
    without_delivery: "Р±РµР· СѓСЂР°С…СѓРІР°РЅРЅСЏ РґРѕСЃС‚Р°РІРєРё",
  };
  const vLabel = v && vatLabels[v] ? vatLabels[v] : v || "";
  const dLabel = d && deliveryLabels[d] ? deliveryLabels[d] : d || "";
  return ["Р¦С–РЅР°", vLabel, dLabel].filter(Boolean).join(" ");
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
  return (qty * num).toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
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
  for (const p of decisionProposals.value) {
    const pv = getProposalPositionValue(p, positionId);
    const num = Number(pv?.price);
    if (!Number.isNaN(num)) withPrice.push({ id: p.id, price: num });
  }
  if (withPrice.length === 0) return { bestId: null, worstId: null };
  const best = withPrice.reduce((a, b) => (a.price >= b.price ? a : b));
  const worst = withPrice.reduce((a, b) => (a.price <= b.price ? a : b));
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
  if (!decisionProposals.value?.length) await loadDecisionProposals();
  showProposalsModal.value = true;
}

onMounted(async () => {
  await loadTender();
  if (!isParticipant.value) {
    await loadOptions();
    await loadNomenclaturesForPreparation();
    if (form.branch) await loadDepartments();
  }
  if (["acceptance", "decision", "approval"].includes(displayStage.value)) {
    await loadDecisionProposals();
  }
});

watch(tenderId, () => loadTender());
watch(displayStage, async (stage) => {
  if (stage === "acceptance" || stage === "decision" || stage === "approval") {
    await loadDecisionProposals();
  }
});
watch([isRegistration, () => displayStage.value], () => {
  if (isRegistration.value && displayStage.value === "acceptance") {
    displayStage.value = "decision";
  }
});
watch(
  () => [form.category, form.cpv_ids, tender.value?.stage],
  async () => {
    if (!isParticipant.value && tender.value?.stage === "preparation") {
      await loadNomenclaturesForPreparation();
    }
  },
);
watch(prepTab, (tab) => {
  if (tab === "criteria") loadReferenceCriteria();
});
</script>

<style scoped>
/* РљРѕРјРїР°РєС‚РЅРёР№ СЃС‚РµРїРµСЂ */
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
/* РџСЂРѕРіСЂРµСЃ: РїСЂРѕР№РґРµРЅС– РєСЂРѕРєРё С‚Р° РїРѕС‚РѕС‡РЅРёР№ РµС‚Р°Рї С‚РµРЅРґРµСЂР° вЂ” Р°РєС†РµРЅС‚РЅРёР№ РєРѕР»С–СЂ */
.tender-stepper :deep(.tender-step-done [data-slot="trigger"]),
.tender-stepper :deep(.tender-step-progress-current [data-slot="trigger"]) {
  background-color: var(--color-primary-500, #3b82f6);
  color: white;
}
.tender-stepper :deep(.tender-step-done [data-slot="separator"]) {
  background-color: var(--color-primary-500, #3b82f6);
}
/* РљСЂРѕРє, РЅР° СЏРєРѕРјСѓ Р·Р°СЂР°Р· РєРѕСЂРёСЃС‚СѓРІР°С‡ (РїРµСЂРµРіР»СЏРґ) вЂ” СЃРІС–С‚Р»С–С€РёР№ */
.tender-stepper :deep(.tender-step-viewing [data-slot="trigger"]) {
  background-color: var(--color-primary-400, #60a5fa);
  color: white;
}

/* Р РµРґР°РєС‚РѕСЂ В«РћРїРёСЃ СѓРјРѕРІ С‚Р° РІРёРјРѕРіВ»: РїР»РµР№СЃС…РѕР»РґРµСЂ Р·РЅРёРєР°С” РїСЂРё С„РѕРєСѓСЃС–, РІСЃСЏ РѕР±Р»Р°СЃС‚СЊ РєР»С–РєР°Р±РµР»СЊРЅР° */
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

