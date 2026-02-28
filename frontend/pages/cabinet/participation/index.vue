<template>
  <div class="h-full min-h-0 flex flex-col overflow-hidden">
    <h2 class="text-2xl font-bold mb-4">
      {{ type === "purchase" ? "РўРµРЅРґРµСЂРё РЅР° Р·Р°РєСѓРїС–РІР»СЋ" : "РўРµРЅРґРµСЂРё РЅР° РїСЂРѕРґР°Р¶" }}
    </h2>

    <div class="flex-1 min-h-0 overflow-hidden flex gap-4 max-lg:flex-col">
      <div
        class="flex-1 min-h-0 overflow-hidden rounded-lg bg-white flex flex-col"
      >
        <div class="flex-shrink-0 p-3 pb-0">
          <UTabs v-model="activeTab" :items="tabItems" />
        </div>

        <div class="flex-1 min-h-0 overflow-auto p-3">
          <UTable
            v-if="tableData.length > 0"
            :data="tableData"
            :columns="tableColumns"
            class="w-full participation-table"
          >
            <template #number-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click="openModal(row.original)"
              >
                в„–{{ row.original.number
                }}{{ ` (С‚СѓСЂ ${row.original.tour_number || 1})` }}
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

            <template #company-cell="{ row }">
              <div class="text-sm">
                <div>{{ row.original.company?.name || "-" }}</div>
                <div class="text-xs text-gray-500">
                  {{ row.original.company?.edrpou || "" }}
                </div>
              </div>
            </template>

            <template #created_at-cell="{ row }">
              {{ formatDate(row.original.created_at) }}
            </template>

            <template #start_at-cell="{ row }">
              {{ formatDateTime(row.original.start_at) }}
            </template>

            <template #end_at-cell="{ row }">
              {{ formatDateTime(row.original.end_at) }}
            </template>
          </UTable>

          <div v-else class="text-center text-gray-400 py-12">
            РќРµРјР°С” С‚РµРЅРґРµСЂС–РІ Р·Р° РѕР±СЂР°РЅРёРјРё СѓРјРѕРІР°РјРё.
          </div>
        </div>

        <div
          class="flex-shrink-0 bg-white px-3 py-2 flex items-center justify-between gap-3"
        >
          <span class="text-sm text-gray-600">
            РџРѕРєР°Р·Р°РЅРѕ {{ tableData.length }} Р· {{ totalCount }}
          </span>

          <UPagination
            v-model:page="currentPage"
            :total="totalCount"
            :items-per-page="PAGE_SIZE"
            :sibling-count="1"
            show-edges
          />
        </div>
      </div>

      <aside
        class="w-[15vw] min-w-[240px] max-w-[360px] shrink-0 rounded-lg bg-white p-4 flex flex-col gap-4 overflow-hidden max-lg:w-full max-lg:min-w-0 max-lg:max-w-none"
      >
        <div class="w-full">
          <UButton
            type="button"
            size="sm"
            variant="outline"
            color="error"
            class="w-full"
            @click="clearFilters"
          >
            РћС‡РёСЃС‚РёС‚Рё
          </UButton>
        </div>

        <UFormField label="РќРѕРјРµСЂ С‚РµРЅРґРµСЂР°">
          <UInput
            v-model="tenderNumberFilter"
            placeholder="Р’РІРµРґС–С‚СЊ РЅРѕРјРµСЂ"
            class="w-full"
          />
        </UFormField>

        <UFormField label="РўРёРї РїСЂРѕРІРµРґРµРЅРЅСЏ">
          <USelectMenu
            v-model="conductTypeFilter"
            :items="conductTypeOptions"
            value-key="value"
            label-key="label"
            placeholder="РЈСЃС–"
            class="w-full"
          />
        </UFormField>

        <LazyContentSearch
          label="РљРѕРјРїР°РЅС–СЏ"
          placeholder="РЈСЃС– РєРѕРјРїР°РЅС–С—"
          search-placeholder="РџРѕС€СѓРє Р·Р° РЅР°Р·РІРѕСЋ Р°Р±Рѕ РєРѕРґРѕРј"
          :tree="companyFilterTree"
          :selected-ids="companySelectedIds"
          :search-term="companySearchTerm"
          @update:search-term="companySearchTerm = $event"
          @toggle="toggleCompanyFilter"
        />

        <CpvTenderModalSelect
          label="Категорія CPV"
          placeholder="Оберіть CPV"
          :selected-ids="cpvSelectedIds"
          :selected-labels="cpvSelectedLabels"
          @update:selected-ids="cpvSelectedIds = $event"
          @update:selected-labels="cpvSelectedLabels = $event"
        />

        <UCheckbox
          v-if="activeTab === 'active'"
          v-model="receptionStartedOnly"
          label="РџСЂРёР№РѕРј СЂРѕР·РїРѕС‡Р°РІСЃСЏ"
        />
      </aside>
    </div>

    <UModal
      :open="modalOpen"
      :ui="{ width: 'max-w-4xl' }"
      @update:open="(v: boolean) => (modalOpen = v)"
    >
      <template #content>
        <div class="p-4 flex flex-col max-h-[85vh]">
          <h3 class="text-lg font-semibold mb-4">
            {{ selectedTender?.name }} - СѓРјРѕРІРё РїСЂРѕРІРµРґРµРЅРЅСЏ
          </h3>

          <div class="flex gap-4 flex-1 min-h-0">
            <div class="flex-1 flex flex-col min-w-0">
              <h4 class="text-sm font-medium text-gray-600 mb-2">
                Р—Р°РіР°Р»СЊРЅС– СѓРјРѕРІРё
              </h4>
              <div
                class="border rounded p-3 overflow-y-auto bg-gray-50 flex-1 min-h-[200px] max-h-[50vh]"
              >
                <div
                  v-if="selectedTender?.general_terms"
                  class="text-sm prose prose-sm max-w-none"
                  v-html="formattedGeneralTerms"
                />
                <p v-else class="whitespace-pre-wrap text-sm">
                  РћРїРёСЃ СѓРјРѕРІ РЅРµ РґРѕРґР°РЅРѕ.
                </p>
              </div>
            </div>

            <div class="flex-1 flex flex-col min-w-0 gap-4">
              <div class="flex flex-col min-h-0">
                <h4 class="text-sm font-medium text-gray-600 mb-2">
                  РџРѕР·РёС†С–С— С‚РµРЅРґРµСЂР°
                </h4>
                <div
                  class="border rounded overflow-y-auto flex-1 min-h-[120px] max-h-[34vh]"
                >
                  <table class="w-full text-sm">
                    <thead class="bg-gray-100 sticky top-0">
                      <tr>
                        <th class="text-left p-2">РќР°Р·РІР°</th>
                        <th class="text-right p-2">РљС–Р»СЊРєС–СЃС‚СЊ</th>
                        <th class="text-left p-2">РћРґ. РІРёРј.</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="pos in tenderPositionsForModal"
                        :key="pos.id"
                        class="border-t"
                      >
                        <td class="p-2">{{ pos.name }}</td>
                        <td class="p-2 text-right">{{ pos.quantity }}</td>
                        <td class="p-2">{{ pos.unit_name ?? "-" }}</td>
                      </tr>
                      <tr v-if="!tenderPositionsForModal.length">
                        <td colspan="3" class="p-3 text-gray-500">
                          РџРѕР·РёС†С–С— Сѓ С†СЊРѕРјСѓ С‚РµРЅРґРµСЂС– РІС–РґСЃСѓС‚РЅС–.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="flex flex-col min-h-0">
                <h4 class="text-sm font-medium text-gray-600 mb-2">
                  Р—Р°РіР°Р»СЊРЅС– РєСЂРёС‚РµСЂС–С—
                </h4>
                <div
                  class="border rounded p-3 overflow-y-auto bg-gray-50 min-h-[120px] max-h-[16vh]"
                >
                  <ul
                    v-if="tenderCriteriaForModal.length"
                    class="space-y-2 text-sm"
                  >
                    <li
                      v-for="criterion in tenderCriteriaForModal"
                      :key="criterion.id"
                    >
                      <span class="font-medium">{{ criterion.name }}</span>
                      <span
                        v-if="criterion.application_label"
                        class="text-gray-500"
                      >
                        ({{ criterion.application_label }})
                      </span>
                    </li>
                  </ul>
                  <p v-else class="text-sm text-gray-500">
                    РљСЂРёС‚РµСЂС–С— РЅРµ РґРѕРґР°РЅРѕ.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-4 pt-4 border-t">
            <UButton variant="outline" @click="modalOpen = false"
              >Р’РёР№С‚Рё</UButton
            >

            <template v-if="checkingParticipation">
              <UButton disabled :loading="true">РџРµСЂРµРІС–СЂРєР°...</UButton>
            </template>

            <template v-else-if="participationAlreadyConfirmed">
              <UButton @click="goToProposalsPage"
                >РџРµСЂРµР№С‚Рё РґРѕ РїСЂРѕРїРѕР·РёС†С–С—</UButton
              >
            </template>

            <UButton
              v-else
              :loading="confirmLoading"
              @click="onConfirmParticipation"
            >
              РџС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ
            </UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "РЈС‡Р°СЃС‚СЊ РІ С‚РµРЅРґРµСЂР°С…" },
});

type ParticipationTab = "active" | "processing" | "completed";

const PAGE_SIZE = 20;

const route = useRoute();
const type = computed(() =>
  route.query.type === "sales" ? "sales" : "purchase",
);
const isSales = computed(() => type.value === "sales");

const tabItems = [
  { label: "РђРєС‚РёРІРЅС–", value: "active" },
  { label: "РћРїСЂР°С†СЊРѕРІСѓСЋС‚СЊСЃСЏ", value: "processing" },
  { label: "Р—Р°РІРµСЂС€РµРЅС–", value: "completed" },
];

const activeTab = ref<ParticipationTab>("active");
const currentPage = ref(1);

const tenders = ref<any[]>([]);
const totalCount = ref(0);
const companyOptions = ref<
  Array<{ id: number; label: string; name?: string; edrpou?: string }>
>([]);

const selectedCompanyId = ref<number | null>(null);
const companySearchTerm = ref("");
const cpvSelectedIds = ref<number[]>([]);
const cpvSelectedLabels = ref<string[]>([]);
const receptionStartedOnly = ref(false);
const conductTypeFilter = ref<"all" | "rfx" | "online_auction">("all");
const tenderNumberFilter = ref("");

const modalOpen = ref(false);
const selectedTender = ref<any>(null);
const confirmLoading = ref(false);

const tendersUC = useTendersUseCases();

const participationAlreadyConfirmed = ref(false);
const checkingParticipation = ref(false);
const confirmedTenderIds = ref<number[]>([]);

const tableColumns = computed(() => {
  return [
    { accessorKey: "number", header: "РќРѕРјРµСЂ" },
    { accessorKey: "name", header: "РќР°Р·РІР°" },
    { accessorKey: "company", header: "РљРѕРјРїР°РЅС–СЏ" },
    { accessorKey: "stage_label", header: "Р•С‚Р°Рї" },
    { accessorKey: "start_at", header: "РџРѕС‡Р°С‚РѕРє РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№" },
    { accessorKey: "end_at", header: "Р—Р°РІРµСЂС€РµРЅРЅСЏ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№" },
    { accessorKey: "conduct_type_label", header: "РўРёРї РїСЂРѕРІРµРґРµРЅРЅСЏ" },
  ];
});

const tableData = computed(() => tenders.value);

const companyFilterTree = computed(() =>
  companyOptions.value.map((item) => ({
    id: item.id,
    name:
      item.label ||
      `${item.name || ""}${item.edrpou ? ` (${item.edrpou})` : ""}`.trim(),
    label:
      item.label ||
      `${item.name || ""}${item.edrpou ? ` (${item.edrpou})` : ""}`.trim(),
  })),
);

const companySelectedIds = computed(() =>
  selectedCompanyId.value ? [selectedCompanyId.value] : [],
);
const conductTypeOptions = [
  { value: "all", label: "РЈСЃС–" },
  { value: "rfx", label: "Р—Р±С–СЂ РїСЂРѕРїРѕР·РёС†С–Р№" },
  { value: "online_auction", label: "РћРЅР»Р°Р№РЅ С‚РѕСЂРіРё" },
];

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("uk-UA");
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("uk-UA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const formattedGeneralTerms = computed(() => {
  const terms = String(selectedTender.value?.general_terms ?? "").trim();
  if (!terms) return "";
  const looksLikeHtml = /<[^>]+>/.test(terms);
  if (looksLikeHtml) return terms;
  return escapeHtml(terms).replace(/\r?\n/g, "<br>");
});

const tenderPositionsForModal = computed(() => {
  const positions = selectedTender.value?.positions;
  return Array.isArray(positions) ? positions : [];
});

const tenderCriteriaForModal = computed(() => {
  const criteria = selectedTender.value?.criteria;
  return Array.isArray(criteria) ? criteria : [];
});

async function loadList() {
  const { data } = await tendersUC.getTendersForParticipation(
    isSales.value,
    activeTab.value,
    {
      page: currentPage.value,
      companyId: selectedCompanyId.value,
      cpvIds: cpvSelectedIds.value,
      receptionStarted:
        activeTab.value === "active" && receptionStartedOnly.value,
      conductType: conductTypeFilter.value,
      tenderNumber: tenderNumberFilter.value,
    },
  );

  const payload = (data as any) || {};
  tenders.value = Array.isArray(payload.results) ? payload.results : [];
  totalCount.value = Number(payload.count || 0);
  companyOptions.value = Array.isArray(payload.companies)
    ? payload.companies
    : [];
}

function toggleCompanyFilter(id: number) {
  selectedCompanyId.value = selectedCompanyId.value === id ? null : id;
}

async function openModal(tender: any) {
  const tenderId = tender?.id != null ? Number(tender.id) : null;
  if (tenderId == null) return;

  checkingParticipation.value = true;
  modalOpen.value = false;
  selectedTender.value = tender;
  participationAlreadyConfirmed.value =
    tender?.current_user_has_proposal === true;

  if (participationAlreadyConfirmed.value) {
    checkingParticipation.value = false;
    goToProposalsPage();
    return;
  }

  try {
    const { data: detail } = await tendersUC.getTender(tenderId, isSales.value);
    if (detail) {
      selectedTender.value = { ...selectedTender.value, ...detail };
    }

    if (detail?.current_user_has_proposal === true) {
      participationAlreadyConfirmed.value = true;
    }

    if (confirmedTenderIds.value.includes(tenderId)) {
      participationAlreadyConfirmed.value = true;
      selectedTender.value = {
        ...(selectedTender.value || {}),
        current_user_has_proposal: true,
      };
    }

    if (participationAlreadyConfirmed.value) {
      if (!confirmedTenderIds.value.includes(tenderId)) {
        confirmedTenderIds.value = [...confirmedTenderIds.value, tenderId];
      }
      goToProposalsPage();
      return;
    }

    modalOpen.value = true;
  } finally {
    checkingParticipation.value = false;
  }
}

function goToProposalsPage() {
  if (!selectedTender.value?.id) return;
  const tenderId = selectedTender.value.id;
  modalOpen.value = false;
  selectedTender.value = null;

  if (isSales.value) {
    navigateTo(`/cabinet/tenders/sales/proposals/${tenderId}`);
  } else {
    navigateTo(`/cabinet/tenders/proposals/${tenderId}`);
  }
}

async function onConfirmParticipation() {
  if (!selectedTender.value?.id) return;
  const tenderId = selectedTender.value.id;
  confirmLoading.value = true;

  try {
    const { error } = await tendersUC.confirmParticipation(
      tenderId,
      isSales.value,
    );
    if (error) {
      const msg = error || "РќРµ РІРґР°Р»РѕСЃСЏ РїС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ.";
      useToast().add({ title: msg, color: "error" });
      return;
    }

    participationAlreadyConfirmed.value = true;
    if (!confirmedTenderIds.value.includes(tenderId)) {
      confirmedTenderIds.value = [...confirmedTenderIds.value, tenderId];
    }

    await loadList();
    modalOpen.value = false;
    selectedTender.value = null;

    if (isSales.value) {
      await navigateTo(`/cabinet/tenders/sales/proposals/${tenderId}`);
    } else {
      await navigateTo(`/cabinet/tenders/proposals/${tenderId}`);
    }
  } catch (e: any) {
    const msg =
      e?.data?.detail || e?.message || "РќРµ РІРґР°Р»РѕСЃСЏ РїС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ.";
    useToast().add({ title: msg, color: "error" });
    console.error(msg);
  } finally {
    confirmLoading.value = false;
  }
}

function clearFilters() {
  selectedCompanyId.value = null;
  companySearchTerm.value = "";
  cpvSelectedIds.value = [];
  cpvSelectedLabels.value = [];
  receptionStartedOnly.value = false;
  conductTypeFilter.value = "all";
  tenderNumberFilter.value = "";
  currentPage.value = 1;
}

onMounted(() => {
  if (!route.query.type) {
    navigateTo({ path: "/cabinet/participation", query: { type: "purchase" } });
    return;
  }
  loadList();
});

onActivated(() => {
  if (route.query.type) loadList();
});

watch([activeTab, type], () => {
  currentPage.value = 1;
  if (activeTab.value !== "active") {
    receptionStartedOnly.value = false;
  }
});

watch(
  () => [
    selectedCompanyId.value,
    receptionStartedOnly.value,
    conductTypeFilter.value,
    tenderNumberFilter.value,
    cpvSelectedIds.value.join(","),
  ],
  () => {
    currentPage.value = 1;
  },
);

watch(
  () => [
    route.query.type,
    activeTab.value,
    currentPage.value,
    selectedCompanyId.value,
    receptionStartedOnly.value,
    conductTypeFilter.value,
    tenderNumberFilter.value,
    cpvSelectedIds.value.join(","),
  ],
  () => {
    if (route.query.type) loadList();
  },
);
</script>

<style scoped>
.participation-table :deep(thead th) {
  position: sticky;
  top: 0;
  z-index: 5;
  background: white;
}
</style>

