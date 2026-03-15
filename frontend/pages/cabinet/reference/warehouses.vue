<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Склади</h2>
    </div>

    <div class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-hidden">
      <UCard class="h-full flex flex-col min-h-0 border border-gray-200 shadow-sm">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-semibold">Склади відвантаження</h3>
            <div class="flex items-center gap-2">
              <UButton
                size="sm"
                variant="outline"
                icon="i-heroicons-archive-box"
                @click="openInactiveWarehousesModal('shipment')"
              >
                Деактивовані
              </UButton>
              <UButton
                size="sm"
                icon="i-heroicons-plus"
                @click="openModal(undefined, 'shipment')"
              >
                Додати
              </UButton>
            </div>
          </div>
        </template>

        <div class="flex-1 min-h-0 overflow-auto">
          <UTable
            :data="shipmentTableData"
            :columns="tableColumns"
            :meta="tableMeta"
            class="w-full"
            @on-select="(_e, row) => selectWarehouse(row.original)"
          >
            <template #name-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click.stop="openModal(row.original, 'shipment')"
              >
                {{ row.original.name }}
              </button>
            </template>
            <template #actions-cell="{ row }">
              <div class="flex gap-1">
                <UButton
                  icon="i-heroicons-archive-box"
                  size="xs"
                  variant="ghost"
                  color="warning"
                  aria-label="Деактивувати"
                  @click.stop="deactivateWarehouse(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteWarehouse(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div v-if="shipmentWarehouses.length === 0" class="text-center text-gray-400 py-8">
            Немає складів відвантаження.
          </div>
        </div>
      </UCard>

      <UCard class="h-full flex flex-col min-h-0 border border-gray-200 shadow-sm">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-semibold">Склади для поставки</h3>
            <div class="flex items-center gap-2">
              <UButton
                size="sm"
                variant="outline"
                icon="i-heroicons-archive-box"
                @click="openInactiveWarehousesModal('delivery')"
              >
                Деактивовані
              </UButton>
              <UButton
                size="sm"
                icon="i-heroicons-plus"
                @click="openModal(undefined, 'delivery')"
              >
                Додати
              </UButton>
            </div>
          </div>
        </template>

        <div class="flex-1 min-h-0 overflow-auto">
          <UTable
            :data="deliveryTableData"
            :columns="tableColumns"
            :meta="tableMeta"
            class="w-full"
            @on-select="(_e, row) => selectWarehouse(row.original)"
          >
            <template #name-cell="{ row }">
              <button
                type="button"
                class="text-primary hover:underline font-medium text-left"
                @click.stop="openModal(row.original, 'delivery')"
              >
                {{ row.original.name }}
              </button>
            </template>
            <template #actions-cell="{ row }">
              <div class="flex gap-1">
                <UButton
                  icon="i-heroicons-archive-box"
                  size="xs"
                  variant="ghost"
                  color="warning"
                  aria-label="Деактивувати"
                  @click.stop="deactivateWarehouse(row.original)"
                />
                <UButton
                  icon="i-heroicons-trash"
                  size="xs"
                  variant="ghost"
                  color="red"
                  aria-label="Видалити"
                  @click.stop="deleteWarehouse(row.original)"
                />
              </div>
            </template>
          </UTable>
          <div v-if="deliveryWarehouses.length === 0" class="text-center text-gray-400 py-8">
            Немає складів для поставки.
          </div>
        </div>
      </UCard>
    </div>

    <UModal v-model:open="showModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{ editing ? "Редагувати склад" : "Додати склад" }}
              ({{ form.warehouse_type === "shipment" ? "Склад відвантаження" : "Склад для поставки" }})
            </h3>
          </template>

          <UForm :state="form" @submit="save" class="space-y-4">
            <UFormField label="Назва" name="name" required>
              <UInput v-model="form.name" class="w-full" />
            </UFormField>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UFormField label="Область" name="region" required>
                <UInput v-model="form.region" class="w-full" />
              </UFormField>
              <UFormField label="Населений пункт" name="locality" required>
                <UInput v-model="form.locality" class="w-full" />
              </UFormField>
              <UFormField label="Вулиця" name="street" required>
                <UInput v-model="form.street" class="w-full" />
              </UFormField>
              <UFormField label="Будинок" name="building" required>
                <UInput v-model="form.building" class="w-full" />
              </UFormField>
              <UFormField label="Корпус / офіс / квартира" name="unit">
                <UInput v-model="form.unit" class="w-full" />
              </UFormField>
              <UFormField label="Поштовий індекс" name="postal_code">
                <UInput
                  v-model="form.postal_code"
                  type="number"
                  min="0"
                  step="1"
                  inputmode="numeric"
                  class="w-full"
                />
              </UFormField>
            </div>

            <UFormField label="Повна адреса">
              <UTextarea :model-value="fullAddress" :rows="3" readonly />
            </UFormField>

            <div class="flex gap-4 pt-2">
              <UButton type="button" variant="outline" class="flex-1" @click="showModal = false">
                Скасувати
              </UButton>
              <UButton type="submit" class="flex-1" :loading="saving">
                {{ editing ? "Зберегти" : "Додати" }}
              </UButton>
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>

    <InactiveItemsModal
      :open="showInactiveModal"
      :title="
        inactiveWarehouseType === 'shipment'
          ? 'Деактивовані склади відвантаження'
          : 'Деактивовані склади для поставки'
      "
      :items="inactiveWarehouses"
      :fields="inactiveWarehouseFields"
      :loading="loadingInactiveWarehouses"
      empty-text="Немає деактивованих складів."
      @update:open="showInactiveModal = $event"
      @restore="restoreWarehouse"
      @delete="deleteInactiveWarehouse"
    />
  </div>
</template>

<script setup lang="ts">
import { getApiErrorMessage } from "~/shared/api/error";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Склади" },
});

type WarehouseType = "shipment" | "delivery";

const { getAuthHeaders } = useAuth();
const { fetch } = useApi();
const { getCurrentCompanyId } = useCurrentCompanyId();

const shipmentWarehouses = ref<any[]>([]);
const deliveryWarehouses = ref<any[]>([]);
const inactiveWarehouses = ref<any[]>([]);
const selectedWarehouse = ref<any | null>(null);
const showModal = ref(false);
const showInactiveModal = ref(false);
const saving = ref(false);
const loadingInactiveWarehouses = ref(false);
const editing = ref(false);
const inactiveWarehouseType = ref<WarehouseType>("shipment");

const form = reactive({
  id: null as number | null,
  warehouse_type: "shipment" as WarehouseType,
  name: "",
  region: "",
  locality: "",
  street: "",
  building: "",
  unit: "",
  postal_code: "",
});

const tableColumns = [
  { accessorKey: "name", header: "Назва" },
  { accessorKey: "region", header: "Область" },
  { accessorKey: "locality", header: "Населений пункт" },
  { accessorKey: "full_address", header: "Повна адреса" },
  { id: "actions", header: "Дії" },
];

const inactiveWarehouseFields = [
  { key: "name", label: "Назва" },
  { key: "region", label: "Область" },
  { key: "full_address", label: "Повна адреса" },
];

const tableMeta = computed(() => ({
  class: {
    tr: (row: any) =>
      row.original?.id === selectedWarehouse.value?.id
        ? "bg-blue-50 cursor-pointer"
        : "cursor-pointer",
  },
}));

const shipmentTableData = computed(() => shipmentWarehouses.value);
const deliveryTableData = computed(() => deliveryWarehouses.value);

const fullAddress = computed(() =>
  [
    form.region,
    form.locality,
    form.street,
    form.building,
    form.unit,
    form.postal_code,
  ]
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .join(", "),
);

function resetForm(warehouseType: WarehouseType) {
  form.id = null;
  form.warehouse_type = warehouseType;
  form.name = "";
  form.region = "";
  form.locality = "";
  form.street = "";
  form.building = "";
  form.unit = "";
  form.postal_code = "";
}

function selectWarehouse(item: any) {
  selectedWarehouse.value = item;
}

function normalizePostalCode(value: unknown) {
  return String(value ?? "")
    .replace(/\D+/g, "")
    .slice(0, 32);
}

function openModal(item?: any, warehouseType: WarehouseType = "shipment") {
  editing.value = Boolean(item);
  if (item) {
    form.id = item.id;
    form.warehouse_type = (item.warehouse_type || warehouseType) as WarehouseType;
    form.name = item.name || "";
    form.region = item.region || "";
    form.locality = item.locality || "";
    form.street = item.street || "";
    form.building = item.building || "";
    form.unit = item.unit || "";
    form.postal_code = item.postal_code || "";
  } else {
    resetForm(warehouseType);
  }
  showModal.value = true;
}

async function loadWarehouses() {
  const [shipmentRes, deliveryRes] = await Promise.all([
    fetch("/warehouses/?warehouse_type=shipment", { headers: getAuthHeaders() }),
    fetch("/warehouses/?warehouse_type=delivery", { headers: getAuthHeaders() }),
  ]);

  shipmentWarehouses.value = Array.isArray(shipmentRes.data) ? shipmentRes.data : [];
  deliveryWarehouses.value = Array.isArray(deliveryRes.data) ? deliveryRes.data : [];
}

async function loadInactiveWarehouses(warehouseType: WarehouseType) {
  loadingInactiveWarehouses.value = true;
  const { data } = await fetch(
    `/warehouses/?warehouse_type=${warehouseType}&inactive_only=1`,
    { headers: getAuthHeaders() },
  );
  inactiveWarehouses.value = Array.isArray(data) ? data : [];
  loadingInactiveWarehouses.value = false;
}

async function save() {
  const companyId = await getCurrentCompanyId();
  if (!companyId) {
    alert("Не вдалося визначити компанію.");
    return;
  }

  const name = form.name.trim();
  const region = form.region.trim();
  const locality = form.locality.trim();
  const street = form.street.trim();
  const building = form.building.trim();

  if (!name || !region || !locality || !street || !building) {
    alert("Заповніть назву та адресу складу.");
    return;
  }

  const payload = {
    company: companyId,
    warehouse_type: form.warehouse_type,
    name,
    region,
    locality,
    street,
    building,
    unit: form.unit.trim(),
    postal_code: normalizePostalCode(form.postal_code),
  };

  saving.value = true;
  try {
    if (editing.value && form.id) {
      const { error } = await fetch(`/warehouses/${form.id}/`, {
        method: "PATCH",
        body: payload,
        headers: getAuthHeaders(),
      });
      if (error) {
        alert(getApiErrorMessage(error, "Помилка збереження складу"));
        return;
      }
    } else {
      const { error } = await fetch("/warehouses/", {
        method: "POST",
        body: payload,
        headers: getAuthHeaders(),
      });
      if (error) {
        alert(getApiErrorMessage(error, "Помилка створення складу"));
        return;
      }
    }

    showModal.value = false;
    await loadWarehouses();
  } finally {
    saving.value = false;
  }
}

async function deleteWarehouse(item: any) {
  if (!item?.id) return;
  if (!confirm(`Видалити склад "${item.name}"?`)) return;

  const { error } = await fetch(`/warehouses/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert(getApiErrorMessage(error, "Помилка видалення складу"));
    return;
  }

  if (selectedWarehouse.value?.id === item.id) selectedWarehouse.value = null;
  await loadWarehouses();
}

async function deactivateWarehouse(item: any) {
  if (!item?.id) return;
  if (!confirm(`Деактивувати склад "${item.name}"?`)) return;

  const { error } = await fetch(`/warehouses/${item.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося деактивувати склад"));
    return;
  }

  if (selectedWarehouse.value?.id === item.id) selectedWarehouse.value = null;
  await loadWarehouses();
}

async function openInactiveWarehousesModal(warehouseType: WarehouseType) {
  inactiveWarehouseType.value = warehouseType;
  showInactiveModal.value = true;
  await loadInactiveWarehouses(warehouseType);
}

async function restoreWarehouse(item: any) {
  const { error } = await fetch(`/warehouses/${item.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося відновити склад"));
    return;
  }
  await Promise.all([
    loadWarehouses(),
    loadInactiveWarehouses(inactiveWarehouseType.value),
  ]);
}

async function deleteInactiveWarehouse(item: any) {
  if (!confirm(`Видалити склад "${item.name}" остаточно?`)) return;
  const { error } = await fetch(`/warehouses/${item.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (error) {
    alert(getApiErrorMessage(error, "Не вдалося видалити склад"));
    return;
  }
  await Promise.all([
    loadWarehouses(),
    loadInactiveWarehouses(inactiveWarehouseType.value),
  ]);
}

onMounted(() => {
  void loadWarehouses();
});
</script>
