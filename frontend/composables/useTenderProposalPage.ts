type SupplierOption = {
  value: number;
  label: string;
  edrpou?: string;
};

type InitProposalLike = {
  supplier_company_id?: number | null;
  supplier_company?: {
    id?: number | null;
    name?: string | null;
    edrpou?: string | null;
  } | null;
};

export function useTenderProposalPage(options: {
  onSupplierSelect: (id: number | null) => Promise<void> | void;
}) {
  const suppliersUC = useSuppliersUseCases();
  const selectedSupplierId = ref<number | null>(null);
  const selectedSupplier = ref<SupplierOption | null>(null);
  const showSupplierModal = ref(false);
  const supplierSearch = ref("");
  const supplierOptions = ref<SupplierOption[]>([]);

  const filteredSuppliers = computed(() => {
    const query = (supplierSearch.value || "").trim().toLowerCase();
    if (!query) return supplierOptions.value;
    return supplierOptions.value.filter(
      (supplier) =>
        (supplier.label && supplier.label.toLowerCase().includes(query)) ||
        (supplier.edrpou && String(supplier.edrpou).toLowerCase().includes(query)),
    );
  });

  async function loadSuppliers() {
    const { data } = await suppliersUC.getSupplierRelations();
    if (!data || !Array.isArray(data)) {
      supplierOptions.value = [];
      return;
    }
    supplierOptions.value = data
      .filter((relation: any) => relation.supplier_company)
      .map((relation: any) => ({
        value: relation.supplier_company.id,
        label:
          relation.supplier_company.name ||
          String(relation.supplier_company.edrpou || ""),
        edrpou: relation.supplier_company.edrpou,
      }));
  }

  async function selectSupplier(option: SupplierOption) {
    selectedSupplierId.value = option.value;
    selectedSupplier.value = option;
    showSupplierModal.value = false;
    supplierSearch.value = "";
    await options.onSupplierSelect(option.value);
  }

  async function initSelectedSupplierFromProposals(proposals: InitProposalLike[]) {
    if (!Array.isArray(proposals) || proposals.length === 0 || selectedSupplierId.value) {
      return;
    }
    const firstProposal = proposals[0];
    const supplierId =
      firstProposal.supplier_company?.id ?? firstProposal.supplier_company_id ?? null;
    if (!supplierId) return;
    selectedSupplierId.value = supplierId;
    selectedSupplier.value =
      supplierOptions.value.find((supplier) => supplier.value === supplierId) || {
        value: supplierId,
        label:
          firstProposal.supplier_company?.name ||
          String(firstProposal.supplier_company?.edrpou || ""),
        edrpou: firstProposal.supplier_company?.edrpou || undefined,
      };
    await options.onSupplierSelect(supplierId);
  }

  return {
    selectedSupplierId,
    selectedSupplier,
    showSupplierModal,
    supplierSearch,
    filteredSuppliers,
    loadSuppliers,
    selectSupplier,
    initSelectedSupplierFromProposals,
  };
}
