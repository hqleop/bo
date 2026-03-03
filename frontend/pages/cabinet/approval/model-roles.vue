<template>
  <div class="h-full min-h-0 flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Ролі для моделей</h2>
      <UButton icon="i-heroicons-plus" @click="openCreateRole">Додати роль</UButton>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0 flex-1">
      <UCard class="min-h-0 flex flex-col">
        <template #header>
          <h3 class="font-semibold">Ролі</h3>
        </template>
        <div class="space-y-3">
          <UInput v-model="roleSearch" placeholder="Пошук ролі" />
          <div class="max-h-[55vh] overflow-auto border rounded">
            <UTable
              :data="filteredRoles"
              :columns="rolesColumns"
              class="w-full"
            >
              <template #name-cell="{ row }">
                <button
                  class="text-left hover:underline"
                  @click="selectRole(row.original)"
                >
                  {{ row.original.name }}
                </button>
              </template>
            </UTable>
          </div>
        </div>
      </UCard>

      <UCard class="min-h-0 flex flex-col">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-semibold">
              Користувачі ролі
              <span v-if="selectedRole">- {{ selectedRole.name }}</span>
            </h3>
            <UButton
              icon="i-heroicons-plus"
              size="sm"
              :disabled="!selectedRole"
              @click="showAddUserModal = true"
            >
              Додати
            </UButton>
          </div>
        </template>
        <div v-if="!selectedRole" class="text-sm text-gray-500">
          Оберіть роль у лівій області.
        </div>
        <div v-else class="max-h-[55vh] overflow-auto border rounded">
          <UTable :data="selectedRoleUsers" :columns="usersColumns" class="w-full">
            <template #actions-cell="{ row }">
              <UButton
                icon="i-heroicons-trash"
                color="error"
                variant="ghost"
                size="xs"
                @click="removeRoleUser(row.original.id)"
              />
            </template>
          </UTable>
        </div>
      </UCard>
    </div>

    <UModal v-model:open="showCreateRoleModal">
      <template #content>
        <UCard>
          <template #header><h3>Нова роль</h3></template>
          <div class="space-y-4">
            <UFormField label="Назва ролі" required>
              <UInput v-model="createRoleForm.name" />
            </UFormField>
            <UFormField label="Призначення" required>
              <USelectMenu
                v-model="createRoleForm.application"
                :items="applicationOptions"
                value-key="value"
              />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showCreateRoleModal = false">Скасувати</UButton>
              <UButton :loading="savingRole" @click="saveRole">Зберегти</UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="showAddUserModal">
      <template #content>
        <UCard>
          <template #header><h3>Додати користувача до ролі</h3></template>
          <div class="space-y-4">
            <UFormField label="Користувач" required>
              <USelectMenu
                v-model="selectedUserIdToAdd"
                :items="memberOptions"
                value-key="value"
                placeholder="Оберіть користувача"
              />
            </UFormField>
            <div class="flex justify-end gap-2">
              <UButton variant="outline" @click="showAddUserModal = false">Скасувати</UButton>
              <UButton :loading="savingRoleUser" @click="addUserToRole">Додати</UButton>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: "cabinet", middleware: "auth", meta: { title: "Ролі для моделей" } });

const approvalUC = useApprovalUseCases();
const usersUC = useUsersUseCases();
const { me, refreshMe } = useMe();

const roles = ref<any[]>([]);
const selectedRole = ref<any | null>(null);
const selectedRoleUsers = ref<any[]>([]);
const members = ref<any[]>([]);
const roleSearch = ref("");

const showCreateRoleModal = ref(false);
const savingRole = ref(false);
const createRoleForm = reactive({
  name: "",
  application: "procurement" as "procurement" | "sales",
});

const showAddUserModal = ref(false);
const selectedUserIdToAdd = ref<number | null>(null);
const savingRoleUser = ref(false);

const rolesColumns = [
  { accessorKey: "name", header: "Роль" },
  { accessorKey: "application_label", header: "Призначення" },
];
const usersColumns = [
  { accessorKey: "full_name", header: "ПІБ" },
  { accessorKey: "actions", header: "" },
];

const applicationOptions = [
  { value: "sales", label: "Тендер-Продаж" },
  { value: "procurement", label: "Тендер-Закупівля" },
];

const filteredRoles = computed(() => {
  const q = roleSearch.value.trim().toLowerCase();
  if (!q) return roles.value;
  return roles.value.filter((r) => `${r.name} ${r.application_label || ""}`.toLowerCase().includes(q));
});

const memberOptions = computed(() =>
  members.value.map((m) => ({
    value: Number(m?.user?.id),
    label: `${m?.user?.full_name || `${m?.user?.last_name || ""} ${m?.user?.first_name || ""}`.trim() || m?.user?.email || m?.user?.id}`,
  }))
);

async function ensureCompanyId() {
  if (!me.value?.memberships?.length) await refreshMe();
  return Number(me.value?.memberships?.[0]?.company?.id || me.value?.memberships?.[0]?.company || 0);
}

async function loadRoles() {
  const { data } = await approvalUC.getModelRoles();
  roles.value = data;
}

async function loadMembers() {
  const { data } = await usersUC.getMemberships();
  members.value = Array.isArray(data) ? data : [];
}

async function selectRole(role: any) {
  selectedRole.value = role;
  const { data } = await approvalUC.getModelRoleUsers(Number(role.id));
  selectedRoleUsers.value = data;
}

function openCreateRole() {
  createRoleForm.name = "";
  createRoleForm.application = "procurement";
  showCreateRoleModal.value = true;
}

async function saveRole() {
  const companyId = await ensureCompanyId();
  const name = createRoleForm.name.trim();
  if (!companyId || !name) return;
  savingRole.value = true;
  try {
    const { error } = await approvalUC.createModelRole({
      company: companyId,
      name,
      application: createRoleForm.application,
    });
    if (error) return;
    showCreateRoleModal.value = false;
    await loadRoles();
  } finally {
    savingRole.value = false;
  }
}

async function addUserToRole() {
  if (!selectedRole.value || !selectedUserIdToAdd.value) return;
  savingRoleUser.value = true;
  try {
    const { error } = await approvalUC.createModelRoleUser({
      role: Number(selectedRole.value.id),
      user: Number(selectedUserIdToAdd.value),
    });
    if (error) return;
    showAddUserModal.value = false;
    selectedUserIdToAdd.value = null;
    await selectRole(selectedRole.value);
  } finally {
    savingRoleUser.value = false;
  }
}

async function removeRoleUser(id: number) {
  const { error } = await approvalUC.deleteModelRoleUser(id);
  if (error || !selectedRole.value) return;
  await selectRole(selectedRole.value);
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadMembers()]);
});
</script>
