<template>
  <div class="h-full grid grid-cols-1 xl:grid-cols-3 gap-4">
    <!-- РљРѕР»РѕРЅРєР° 1: Р¤С–Р»С–Р°Р»Рё -->
    <div class="min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Р¤С–Р»С–Р°Р»Рё</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-archive-box"
            size="sm"
            variant="outline"
            @click="openInactiveBranchesModal"
          >
            Р”РµР°РєС‚РёРІРѕРІР°РЅС–
          </UButton>
                    <UButton icon="i-heroicons-plus" size="sm" @click="openBranchModal()">
            Р”РѕРґР°С‚Рё
          </UButton>
        </div>
      </div>
      <div class="space-y-0 min-h-[200px]">
        <TreeItem
          v-for="branch in branches"
          :key="branch.id"
          :item="branch"
          :level="0"
          :selected-id="selectedBranch?.id"
          @select="selectBranch"
          @edit="openBranchModal"
          @deactivate="deactivateBranch"
          @delete="deleteBranch"
        />
        <div
          v-if="branches.length === 0"
          class="text-center text-gray-400 py-8"
        >
          РќРµРјР°С” С„С–Р»С–Р°Р»С–РІ
        </div>
      </div>
    </div>

    <!-- РљРѕР»РѕРЅРєР° 2: РџС–РґСЂРѕР·РґС–Р»Рё -->
    <div class="min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">РџС–РґСЂРѕР·РґС–Р»Рё</h3>
        <div class="flex gap-2">
        <UButton
          icon="i-heroicons-archive-box"
          size="sm"
          variant="outline"
          @click="openInactiveDepartmentsModal"
        >
          Р”РµР°РєС‚РёРІРѕРІР°РЅС–
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          size="sm"
          :disabled="!selectedBranch"
          @click="openDepartmentModal()"
        >
          Р”РѕРґР°С‚Рё
        </UButton>
      </div>
      </div>
      <div v-if="!selectedBranch" class="text-center text-gray-400 py-8">
        РћР±РµСЂС–С‚СЊ С„С–Р»С–Р°Р»
      </div>
      <div v-else class="space-y-0 min-h-[200px]">
        <TreeItem
          v-for="dept in departments"
          :key="dept.id"
          :item="dept"
          :level="0"
          :selected-id="selectedDepartment?.id"
          @select="selectDepartment"
          @edit="openDepartmentModal"
          @deactivate="deactivateDepartment"
          @delete="deleteDepartment"
        />
        <div
          v-if="departments.length === 0"
          class="text-center text-gray-400 py-8"
        >
          РќРµРјР°С” РїС–РґСЂРѕР·РґС–Р»С–РІ
        </div>
      </div>
    </div>

    <!-- РљРѕР»РѕРЅРєР° 3: РљРѕСЂРёСЃС‚СѓРІР°С‡С– -->
    <div class="min-h-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">РљРѕСЂРёСЃС‚СѓРІР°С‡С–</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-arrow-up-tray"
            size="sm"
            variant="outline"
            color="neutral"
            :disabled="!canCopyUsersToParent"
            title="РЎРєРѕРїС–СЋРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Сѓ Р±Р°С‚СЊРєС–РІСЃСЊРєСѓ СЃСѓС‚РЅС–СЃС‚СЊ"
            aria-label="РЎРєРѕРїС–СЋРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Сѓ Р±Р°С‚СЊРєС–РІСЃСЊРєСѓ СЃСѓС‚РЅС–СЃС‚СЊ"
            @click="copyUsers('parent')"
          />
          <UButton
            icon="i-heroicons-arrow-down-tray"
            size="sm"
            variant="outline"
            color="neutral"
            :disabled="!canCopyUsersToDescendants"
            title="РЎРєРѕРїС–СЋРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Сѓ РїС–РґР»РµРіР»С– СЃСѓС‚РЅРѕСЃС‚С–"
            aria-label="РЎРєРѕРїС–СЋРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Сѓ РїС–РґР»РµРіР»С– СЃСѓС‚РЅРѕСЃС‚С–"
            @click="copyUsers('descendants')"
          />
          <UButton
            icon="i-heroicons-plus"
            size="sm"
            :disabled="!selectedBranch && !selectedDepartment"
            @click="openAddUsersModal()"
          >
            Р”РѕРґР°С‚Рё
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            size="sm"
            variant="outline"
            color="red"
            :disabled="
              (!selectedBranch && !selectedDepartment) ||
              selectedUsers.length === 0
            "
            @click="openRemoveUsersModal()"
          >
            Р’РёРґР°Р»РёС‚Рё
          </UButton>
        </div>
      </div>
      <div
        v-if="!selectedBranch && !selectedDepartment"
        class="text-center text-gray-400 py-8"
      >
        РћР±РµСЂС–С‚СЊ С„С–Р»С–Р°Р» Р°Р±Рѕ РїС–РґСЂРѕР·РґС–Р»
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="user in currentUsers"
          :key="user.id"
          class="flex items-center justify-between p-2 rounded hover:bg-gray-100"
        >
          <div class="flex-1">
            <div class="font-medium">
              {{ user.user.first_name }} {{ user.user.last_name }}
            </div>
            <div class="text-sm text-gray-500">{{ user.user.email }}</div>
          </div>
          <UCheckbox
            :model-value="selectedUsers.includes(user.user.id)"
            @update:model-value="toggleUserSelection(user.user.id)"
          />
        </div>
        <div
          v-if="currentUsers.length === 0"
          class="text-center text-gray-400 py-8"
        >
          РќРµРјР°С” РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ
        </div>
      </div>
    </div>

    <!-- РњРѕРґР°Р»СЊРЅРµ РІС–РєРЅРѕ РґР»СЏ С„С–Р»С–Р°Р»Сѓ -->
    <UModal v-model:open="showBranchModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>{{ editingBranch ? "Р РµРґР°РіСѓРІР°С‚Рё С„С–Р»С–Р°Р»" : "Р”РѕРґР°С‚Рё С„С–Р»С–Р°Р»" }}</h3>
          </template>
          <UForm :state="branchForm" @submit="saveBranch" class="space-y-4">
            <UFormField label="РќР°Р·РІР°" name="name" required>
              <UInput v-model="branchForm.name" class="w-full" />
            </UFormField>
            <UFormField label="РљРѕРґ" name="code">
              <UInput v-model="branchForm.code" class="w-full" />
            </UFormField>
            <UFormField label="Р‘Р°С‚СЊРєС–РІСЃСЊРєРёР№ С„С–Р»С–Р°Р»" name="parent_id">
              <USelectMenu
                v-model="branchForm.parent_id"
                :items="branchParentOptions"
                value-key="value"
                placeholder="Р‘РµР· Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ С„С–Р»С–Р°Р»Сѓ"
                class="w-full"
              />
            </UFormField>
            <div class="flex gap-4">
              <UButton
                variant="outline"
                class="flex-1"
                @click="showBranchModal = false"
                >РЎРєР°СЃСѓРІР°С‚Рё</UButton
              >
              <UButton type="submit" class="flex-1" :loading="saving"
                >Р—Р±РµСЂРµРіС‚Рё</UButton
              >
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>

    <!-- РњРѕРґР°Р»СЊРЅРµ РІС–РєРЅРѕ РґР»СЏ РїС–РґСЂРѕР·РґС–Р»Сѓ -->
    <UModal v-model:open="showDepartmentModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>
              {{
                editingDepartment ? "Р РµРґР°РіСѓРІР°С‚Рё РїС–РґСЂРѕР·РґС–Р»" : "Р”РѕРґР°С‚Рё РїС–РґСЂРѕР·РґС–Р»"
              }}
            </h3>
          </template>
          <UForm
            :state="departmentForm"
            @submit="saveDepartment"
            class="space-y-4"
          >
            <UFormField label="РќР°Р·РІР°" name="name" required>
              <UInput v-model="departmentForm.name" class="w-full" />
            </UFormField>
            <UFormField label="Р‘Р°С‚СЊРєС–РІСЃСЊРєРёР№ РїС–РґСЂРѕР·РґС–Р»" name="parent_id">
              <USelectMenu
                v-model="departmentForm.parent_id"
                :items="departmentParentOptions"
                value-key="value"
                placeholder="Р‘РµР· Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ РїС–РґСЂРѕР·РґС–Р»Сѓ"
                class="w-full"
              />
            </UFormField>
            <div class="flex gap-4">
              <UButton
                variant="outline"
                class="flex-1"
                @click="showDepartmentModal = false"
                >РЎРєР°СЃСѓРІР°С‚Рё</UButton
              >
              <UButton type="submit" class="flex-1" :loading="saving"
                >Р—Р±РµСЂРµРіС‚Рё</UButton
              >
            </div>
          </UForm>
        </UCard>
      </template>
    </UModal>

    <!-- РњРѕРґР°Р»СЊРЅРµ РІС–РєРЅРѕ РґР»СЏ РґРѕРґР°РІР°РЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ -->
    <UModal v-model:open="showAddUsersModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ</h3>
          </template>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="user in availableCompanyUsers"
              :key="user.id"
              class="flex cursor-pointer items-center p-2 rounded hover:bg-gray-50"
              @click="toggleUserToAdd(user.id)"
            >
              <UCheckbox
                :model-value="usersToAdd.includes(user.id)"
                @update:model-value="toggleUserToAdd(user.id)"
                @click.stop
              />
              <div class="ml-3 flex-1">
                <div class="font-medium">
                  {{ user.first_name }} {{ user.last_name }}
                </div>
                <div class="text-sm text-gray-500">{{ user.email }}</div>
              </div>
            </div>
          </div>
          <template #footer>
            <div class="flex gap-4">
              <UButton
                variant="outline"
                class="flex-1"
                @click="showAddUsersModal = false"
                >РЎРєР°СЃСѓРІР°С‚Рё</UButton
              >
              <UButton class="flex-1" @click="addUsers" :loading="saving"
                >Р”РѕРґР°С‚Рё</UButton
              >
            </div>
          </template>
        </UCard>
      </template>
    </UModal>

    <!-- РњРѕРґР°Р»СЊРЅРµ РІС–РєРЅРѕ РґР»СЏ РІРёРґР°Р»РµРЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ -->
    <UModal v-model:open="showRemoveUsersModal">
      <template #content>
        <UCard>
          <template #header>
            <h3>Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ</h3>
          </template>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="user in currentUsers.filter((u) =>
                selectedUsers.includes(u.user.id),
              )"
              :key="user.id"
              class="flex cursor-pointer items-center p-2 rounded hover:bg-gray-50"
              @click="toggleUserToRemove(user.user.id)"
            >
              <UCheckbox
                :model-value="usersToRemove.includes(user.user.id)"
                @update:model-value="toggleUserToRemove(user.user.id)"
                @click.stop
              />
              <div class="ml-3 flex-1">
                <div class="font-medium">
                  {{ user.user.first_name }} {{ user.user.last_name }}
                </div>
                <div class="text-sm text-gray-500">{{ user.user.email }}</div>
              </div>
            </div>
          </div>
          <template #footer>
            <div class="flex gap-4">
              <UButton
                variant="outline"
                class="flex-1"
                @click="showRemoveUsersModal = false"
                >РЎРєР°СЃСѓРІР°С‚Рё</UButton
              >
              <UButton
                class="flex-1"
                color="red"
                @click="removeUsers"
                :loading="saving"
                >Р’РёРґР°Р»РёС‚Рё</UButton
              >
            </div>
          </template>
        </UCard>
      </template>
    </UModal>

    <InactiveItemsModal
      :open="showInactiveBranchesModal"
      title="Р”РµР°РєС‚РёРІРѕРІР°РЅС– С„С–Р»С–Р°Р»Рё"
      :items="inactiveBranches"
      :fields="inactiveBranchFields"
      :loading="loadingInactiveBranches"
      empty-text="РќРµРјР°С” РґРµР°РєС‚РёРІРѕРІР°РЅРёС… С„С–Р»С–Р°Р»С–РІ."
      @update:open="showInactiveBranchesModal = $event"
      @restore="restoreBranch"
      @delete="deleteInactiveBranch"
    />

    <InactiveItemsModal
      :open="showInactiveDepartmentsModal"
      title="Р”РµР°РєС‚РёРІРѕРІР°РЅС– РїС–РґСЂРѕР·РґС–Р»Рё"
      :items="inactiveDepartments"
      :fields="inactiveDepartmentFields"
      :loading="loadingInactiveDepartments"
      empty-text="РќРµРјР°С” РґРµР°РєС‚РёРІРѕРІР°РЅРёС… РїС–РґСЂРѕР·РґС–Р»С–РІ."
      @update:open="showInactiveDepartmentsModal = $event"
      @restore="restoreDepartment"
      @delete="deleteInactiveDepartment"
    />
  </div>
</template>

<script setup lang="ts">
import { getApiErrorMessage } from "~/shared/api/error";

definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: {
    title: "Р¤С–Р»С–Р°Р»Рё РїС–РґСЂРѕР·РґС–Р»Рё",
  },
});

const config = useRuntimeConfig();
const { getAuthHeaders } = useAuth();
const { fetch } = useApi();
const { getCurrentCompanyId } = useCurrentCompanyId();
const toast = useToast();

// Р”Р°РЅС–
const branches = ref<any[]>([]);
const inactiveBranches = ref<any[]>([]);
const departments = ref<any[]>([]);
const inactiveDepartments = ref<any[]>([]);
const currentUsers = ref<any[]>([]);
const companyUsers = ref<any[]>([]);
// РєРѕСЂРёСЃС‚СѓРІР°С‡С– РєРѕРјРїР°РЅС–С—, СЏРєС– С‰Рµ РЅРµ РґРѕРґР°РЅС– РІ РїРѕС‚РѕС‡РЅРёР№ С„С–Р»С–Р°Р»/РїС–РґСЂРѕР·РґС–Р»
const availableCompanyUsers = computed(() => {
  const assignedIds = new Set<number>(
    currentUsers.value.map((u: any) => u.user.id),
  );
  return companyUsers.value.filter((u: any) => !assignedIds.has(u.id));
});

// Р’РёР±СЂР°РЅРёР№ РµР»РµРјРµРЅС‚
const selectedBranch = ref<any>(null);
const selectedDepartment = ref<any>(null);
const selectedUsers = ref<number[]>([]);

const activeAssignmentNode = computed(() => selectedDepartment.value || selectedBranch.value);
const activeAssignmentType = computed(() =>
  selectedDepartment.value ? "department" : selectedBranch.value ? "branch" : null,
);
const canCopyUsersToParent = computed(
  () => Boolean(activeAssignmentNode.value?.parent) && currentUsers.value.length > 0,
);
const canCopyUsersToDescendants = computed(
  () =>
    Array.isArray(activeAssignmentNode.value?.children) &&
    activeAssignmentNode.value.children.length > 0 &&
    currentUsers.value.length > 0,
);

// РњРѕРґР°Р»СЊРЅС– РІС–РєРЅР°
const inactiveBranchFields = [
  { key: "name", label: "РќР°Р·РІР°" },
  { key: "code", label: "РљРѕРґ" },
];

const inactiveDepartmentFields = [
  { key: "name", label: "РќР°Р·РІР°" },
];

const showBranchModal = ref(false);
const showDepartmentModal = ref(false);
const showAddUsersModal = ref(false);
const showRemoveUsersModal = ref(false);
const showInactiveBranchesModal = ref(false);
const showInactiveDepartmentsModal = ref(false);
const saving = ref(false);
const loadingInactiveBranches = ref(false);
const loadingInactiveDepartments = ref(false);

// Р¤РѕСЂРјРё
const editingBranch = ref<any>(null);
const editingDepartment = ref<any>(null);
const branchForm = reactive({
  name: "",
  code: "",
  parent_id: null as number | null,
});
const departmentForm = reactive({
  name: "",
  parent_id: null as number | null,
});
const usersToAdd = ref<number[]>([]);
const usersToRemove = ref<number[]>([]);

// Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ РґР°РЅРёС…
const loadBranches = async () => {
  const { data } = await fetch("/branches/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    branches.value = data;
  }
};

const loadInactiveBranches = async () => {
  loadingInactiveBranches.value = true;
  const { data } = await fetch("/branches/?inactive_only=1&flat=1", {
    headers: getAuthHeaders(),
  });
  inactiveBranches.value = Array.isArray(data) ? data : [];
  loadingInactiveBranches.value = false;
};

const loadDepartments = async () => {
  if (!selectedBranch.value) return;
  const { data } = await fetch(
    `/departments/?branch_id=${selectedBranch.value.id}`,
    {
      headers: getAuthHeaders(),
    },
  );
  if (data) {
    departments.value = data;
  }
};

const loadInactiveDepartments = async () => {
  loadingInactiveDepartments.value = true;
  const branchId = Number(selectedBranch.value?.id || 0);
  const query = branchId
    ? `/departments/?branch_id=${branchId}&inactive_only=1&flat=1`
    : "/departments/?inactive_only=1&flat=1";
  const { data } = await fetch(query, {
    headers: getAuthHeaders(),
  });
  inactiveDepartments.value = Array.isArray(data) ? data : [];
  loadingInactiveDepartments.value = false;
};

const loadUsers = async () => {
  if (!selectedBranch.value && !selectedDepartment.value) {
    currentUsers.value = [];
    return;
  }

  if (selectedDepartment.value) {
    const { data } = await fetch(
      `/department-users/?department_id=${selectedDepartment.value.id}`,
      {
        headers: getAuthHeaders(),
      },
    );
    currentUsers.value = data || [];
  } else if (selectedBranch.value) {
    const { data } = await fetch(
      `/branch-users/?branch_id=${selectedBranch.value.id}`,
      {
        headers: getAuthHeaders(),
      },
    );
    currentUsers.value = data || [];
  }
};

const loadCompanyUsers = async () => {
  const { data } = await fetch("/memberships/", {
    headers: getAuthHeaders(),
  });
  if (data) {
    companyUsers.value = data
      .filter((m: any) => m.status === "approved")
      .map((m: any) => m.user);
  }
};

// РћР±СЂРѕР±РЅРёРєРё РїРѕРґС–Р№
const selectBranch = (branch: any) => {
  selectedBranch.value = branch;
  selectedDepartment.value = null;
  selectedUsers.value = [];
  loadDepartments();
  loadUsers();
};

const selectDepartment = (dept: any) => {
  selectedDepartment.value = dept;
  selectedUsers.value = [];
  loadUsers();
};

const toggleUserSelection = (userId: number) => {
  const index = selectedUsers.value.indexOf(userId);
  if (index > -1) {
    selectedUsers.value.splice(index, 1);
  } else {
    selectedUsers.value.push(userId);
  }
};

// Р¤С–Р»С–Р°Р»Рё
const openBranchModal = (branch?: any) => {
  editingBranch.value = branch || null;
  if (branch) {
    branchForm.name = branch.name;
    branchForm.code = branch.code || "";
    branchForm.parent_id = branch.parent || null;
  } else {
    branchForm.name = "";
    branchForm.code = "";
    branchForm.parent_id = null;
  }
  showBranchModal.value = true;
};

const saveBranch = async () => {
  saving.value = true;
  const payload: any = {
    name: branchForm.name,
    code: branchForm.code,
    company: selectedBranch.value?.company || (await getCurrentCompanyId()),
  };
  if (branchForm.parent_id) {
    payload.parent = branchForm.parent_id;
  }

  const endpoint = editingBranch.value
    ? `/branches/${editingBranch.value.id}/`
    : "/branches/";
  const method = editingBranch.value ? "PUT" : "POST";

  const { data, error } = await fetch(endpoint, {
    method,
    body: payload,
    headers: getAuthHeaders(),
  });

  saving.value = false;
  if (error) {
    alert(getApiErrorMessage(error, "РџРѕРјРёР»РєР° Р·Р±РµСЂРµР¶РµРЅРЅСЏ"));
    return;
  }

  showBranchModal.value = false;
  await loadBranches();
};

const deleteBranch = async (branch: any) => {
  if (!confirm(`Р’РёРґР°Р»РёС‚Рё С„С–Р»С–Р°Р» "${branch.name}"?`)) return;

  const { error } = await fetch(`/branches/${branch.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert("РџРѕРјРёР»РєР° РІРёРґР°Р»РµРЅРЅСЏ");
    return;
  }

  if (selectedBranch.value?.id === branch.id) {
    selectedBranch.value = null;
    selectedDepartment.value = null;
  }
  await loadBranches();
};

const deactivateBranch = async (branch: any) => {
  if (!confirm(`Р”РµР°РєС‚РёРІСѓРІР°С‚Рё С„С–Р»С–Р°Р» "${branch.name}"?`)) return;

  const { error } = await fetch(`/branches/${branch.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РґРµР°РєС‚РёРІСѓРІР°С‚Рё С„С–Р»С–Р°Р»"));
    return;
  }

  if (selectedBranch.value?.id === branch.id) {
    selectedBranch.value = null;
    selectedDepartment.value = null;
    departments.value = [];
    currentUsers.value = [];
    selectedUsers.value = [];
  }

  await loadBranches();
};

const openInactiveBranchesModal = async () => {
  showInactiveBranchesModal.value = true;
  await loadInactiveBranches();
};

const restoreBranch = async (branch: any) => {
  const { error } = await fetch(`/branches/${branch.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РІС–РґРЅРѕРІРёС‚Рё С„С–Р»С–Р°Р»"));
    return;
  }

  await Promise.all([loadBranches(), loadInactiveBranches()]);
};

const deleteInactiveBranch = async (branch: any) => {
  if (!confirm(`Р’РёРґР°Р»РёС‚Рё С„С–Р»С–Р°Р» "${branch.name}" РѕСЃС‚Р°С‚РѕС‡РЅРѕ?`)) return;

  const { error } = await fetch(`/branches/${branch.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РІРёРґР°Р»РёС‚Рё С„С–Р»С–Р°Р»"));
    return;
  }

  await Promise.all([loadBranches(), loadInactiveBranches()]);
};

// РџС–РґСЂРѕР·РґС–Р»Рё
const openDepartmentModal = (dept?: any) => {
  editingDepartment.value = dept || null;
  if (dept) {
    departmentForm.name = dept.name;
    departmentForm.parent_id = dept.parent || null;
  } else {
    departmentForm.name = "";
    departmentForm.parent_id = null;
  }
  showDepartmentModal.value = true;
};

const saveDepartment = async () => {
  if (!selectedBranch.value) return;

  saving.value = true;
  const payload: any = {
    name: departmentForm.name,
    branch: selectedBranch.value.id,
  };
  if (departmentForm.parent_id) {
    payload.parent = departmentForm.parent_id;
  }

  const endpoint = editingDepartment.value
    ? `/departments/${editingDepartment.value.id}/`
    : "/departments/";
  const method = editingDepartment.value ? "PUT" : "POST";

  const { data, error } = await fetch(endpoint, {
    method,
    body: payload,
    headers: getAuthHeaders(),
  });

  saving.value = false;
  if (error) {
    alert(getApiErrorMessage(error, "РџРѕРјРёР»РєР° Р·Р±РµСЂРµР¶РµРЅРЅСЏ"));
    return;
  }

  showDepartmentModal.value = false;
  await loadDepartments();
};

const deleteDepartment = async (dept: any) => {
  if (!confirm(`Р’РёРґР°Р»РёС‚Рё РїС–РґСЂРѕР·РґС–Р» "${dept.name}"?`)) return;

  const { error } = await fetch(`/departments/${dept.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert("РџРѕРјРёР»РєР° РІРёРґР°Р»РµРЅРЅСЏ");
    return;
  }

  if (selectedDepartment.value?.id === dept.id) {
    selectedDepartment.value = null;
  }
  await loadDepartments();
};

const deactivateDepartment = async (dept: any) => {
  if (!confirm(`Р”РµР°РєС‚РёРІСѓРІР°С‚Рё РїС–РґСЂРѕР·РґС–Р» "${dept.name}"?`)) return;

  const { error } = await fetch(`/departments/${dept.id}/deactivate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РґРµР°РєС‚РёРІСѓРІР°С‚Рё РїС–РґСЂРѕР·РґС–Р»"));
    return;
  }

  if (selectedDepartment.value?.id === dept.id) {
    selectedDepartment.value = null;
    currentUsers.value = [];
    selectedUsers.value = [];
  }

  await loadDepartments();
};

const openInactiveDepartmentsModal = async () => {
  showInactiveDepartmentsModal.value = true;
  await loadInactiveDepartments();
};

const restoreDepartment = async (dept: any) => {
  const { error } = await fetch(`/departments/${dept.id}/activate/`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РІС–РґРЅРѕРІРёС‚Рё РїС–РґСЂРѕР·РґС–Р»"));
    return;
  }

  await Promise.all([loadDepartments(), loadInactiveDepartments()]);
};

const deleteInactiveDepartment = async (dept: any) => {
  if (!confirm(`Р’РёРґР°Р»РёС‚Рё РїС–РґСЂРѕР·РґС–Р» "${dept.name}" РѕСЃС‚Р°С‚РѕС‡РЅРѕ?`)) return;

  const { error } = await fetch(`/departments/${dept.id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (error) {
    alert(getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ РІРёРґР°Р»РёС‚Рё РїС–РґСЂРѕР·РґС–Р»"));
    return;
  }

  await Promise.all([loadDepartments(), loadInactiveDepartments()]);
};

// РљРѕСЂРёСЃС‚СѓРІР°С‡С–
const openAddUsersModal = async () => {
  usersToAdd.value = [];
  await loadCompanyUsers();
  showAddUsersModal.value = true;
};

const toggleUserToAdd = (userId: number) => {
  const index = usersToAdd.value.indexOf(userId);
  if (index > -1) {
    usersToAdd.value.splice(index, 1);
  } else {
    usersToAdd.value.push(userId);
  }
};

const addUsers = async () => {
  if (usersToAdd.value.length === 0) return;

  saving.value = true;
  const endpoint = selectedDepartment.value
    ? "/department-users/"
    : "/branch-users/";
  const payload: any = {
    user_ids: usersToAdd.value,
  };

  if (selectedDepartment.value) {
    payload.department = selectedDepartment.value.id;
  } else if (selectedBranch.value) {
    payload.branch = selectedBranch.value.id;
  }

  const { error } = await fetch(endpoint, {
    method: "POST",
    body: payload,
    headers: getAuthHeaders(),
  });

  saving.value = false;
  if (error) {
    alert(getApiErrorMessage(error, "РџРѕРјРёР»РєР° РґРѕРґР°РІР°РЅРЅСЏ"));
    return;
  }

  showAddUsersModal.value = false;
  await loadUsers();
};

const openRemoveUsersModal = () => {
  usersToRemove.value = [...selectedUsers.value];
  showRemoveUsersModal.value = true;
};

const toggleUserToRemove = (userId: number) => {
  const index = usersToRemove.value.indexOf(userId);
  if (index > -1) {
    usersToRemove.value.splice(index, 1);
  } else {
    usersToRemove.value.push(userId);
  }
};

const removeUsers = async () => {
  if (usersToRemove.value.length === 0) return;

  saving.value = true;
  if (selectedDepartment.value) {
    // РњР°СЃРѕРІРµ РІРёРґР°Р»РµРЅРЅСЏ Р· РїС–РґСЂРѕР·РґС–Р»Сѓ Р·Р° department + user_ids
    await fetch("/department-users/bulk-delete/", {
      method: "POST",
      body: {
        department: selectedDepartment.value.id,
        user_ids: usersToRemove.value,
      },
      headers: getAuthHeaders(),
    });
  } else {
    // РЎС‚Р°СЂРёР№ РјРµС…Р°РЅС–Р·Рј РґР»СЏ С„С–Р»С–Р°Р»С–РІ вЂ” РІРёРґР°Р»СЏС”РјРѕ РїРѕ РѕРґРЅРѕРјСѓ
    const endpoint = "/branch-users/";
    for (const userId of usersToRemove.value) {
      const userItem = currentUsers.value.find((u) => u.user.id === userId);
      if (userItem) {
        await fetch(`${endpoint}${userItem.id}/`, {
          method: "DELETE",
          headers: getAuthHeaders(),
        });
      }
    }
  }

  saving.value = false;
  showRemoveUsersModal.value = false;
  selectedUsers.value = [];
  await loadUsers();
};

const copyUsers = async (direction: "parent" | "descendants") => {
  if (!activeAssignmentNode.value || !activeAssignmentType.value) return;

  saving.value = true;
  const isDepartment = activeAssignmentType.value === "department";
  const endpoint = isDepartment
    ? direction === "parent"
      ? "/department-users/copy-parent/"
      : "/department-users/copy-descendants/"
    : direction === "parent"
      ? "/branch-users/copy-parent/"
      : "/branch-users/copy-descendants/";

  const { data, error } = await fetch(endpoint, {
    method: "POST",
    body: isDepartment
      ? { department: activeAssignmentNode.value.id }
      : { branch: activeAssignmentNode.value.id },
    headers: getAuthHeaders(),
  });
  saving.value = false;

  if (error) {
    toast.add({
      title: getApiErrorMessage(error, "РќРµ РІРґР°Р»РѕСЃСЏ СЃРєРѕРїС–СЋРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ"),
      color: "error",
    });
    return;
  }

  toast.add({
    title:
      Number((data as any)?.created_count || 0) > 0
        ? `РЎРєРѕРїС–Р№РѕРІР°РЅРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ: ${(data as any)?.created_count || 0}`
        : "РќРѕРІРёС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґР»СЏ РєРѕРїС–СЋРІР°РЅРЅСЏ РЅРµ Р·РЅР°Р№РґРµРЅРѕ",
    color: "success",
  });
};

// Р”РѕРїРѕРјС–Р¶РЅС–: СЃРїР»РѕС‰РµРЅРЅСЏ РґРµСЂРµРІР° С‚Р° Р·Р±С–СЂ id РЅР°С‰Р°РґРєС–РІ
function flattenBranches(
  branchList: any[],
): { id: number; name: string; level: number }[] {
  const out: { id: number; name: string; level: number }[] = [];
  function walk(items: any[], level: number) {
    if (!items?.length) return;
    for (const item of items) {
      out.push({ id: item.id, name: item.name, level });
      walk(item.children || [], level + 1);
    }
  }
  walk(branchList, 0);
  return out;
}

function getBranchDescendantIds(branch: any): number[] {
  const ids: number[] = [branch.id];
  for (const child of branch.children || []) {
    ids.push(...getBranchDescendantIds(child));
  }
  return ids;
}

function flattenDepartments(
  deptList: any[],
): { id: number; name: string; level: number }[] {
  const out: { id: number; name: string; level: number }[] = [];
  function walk(items: any[], level: number) {
    if (!items?.length) return;
    for (const item of items) {
      out.push({ id: item.id, name: item.name, level });
      walk(item.children || [], level + 1);
    }
  }
  walk(deptList, 0);
  return out;
}

function getDepartmentDescendantIds(dept: any): number[] {
  const ids: number[] = [dept.id];
  for (const child of dept.children || []) {
    ids.push(...getDepartmentDescendantIds(child));
  }
  return ids;
}

// РћРїС†С–С— РґР»СЏ Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ С„С–Р»С–Р°Р»Сѓ: РїР»РѕСЃРєРёР№ СЃРїРёСЃРѕРє, Р±РµР· РїРѕС‚РѕС‡РЅРѕРіРѕ С‚Р° Р№РѕРіРѕ РЅР°С‰Р°РґРєС–РІ
const branchParentOptions = computed(() => {
  const flat = flattenBranches(branches.value);
  const excludeIds = new Set<number>();
  if (editingBranch.value) {
    getBranchDescendantIds(editingBranch.value).forEach((id) =>
      excludeIds.add(id),
    );
  }
  const options = flat.filter((b) => !excludeIds.has(b.id));
  const withPrefix = options.map((b) => ({
    value: b.id,
    label: (b.level ? "  ".repeat(b.level) : "") + b.name,
  }));
  return [{ value: null, label: "Р‘РµР· Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ С„С–Р»С–Р°Р»Сѓ" }, ...withPrefix];
});

// РћРїС†С–С— РґР»СЏ Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ РїС–РґСЂРѕР·РґС–Р»Сѓ
const departmentParentOptions = computed(() => {
  const flat = flattenDepartments(departments.value);
  const excludeIds = new Set<number>();
  if (editingDepartment.value) {
    getDepartmentDescendantIds(editingDepartment.value).forEach((id) =>
      excludeIds.add(id),
    );
  }
  const options = flat.filter((d) => !excludeIds.has(d.id));
  const withPrefix = options.map((d) => ({
    value: d.id,
    label: (d.level ? "  ".repeat(d.level) : "") + d.name,
  }));
  return [
    { value: null, label: "Р‘РµР· Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ РїС–РґСЂРѕР·РґС–Р»Сѓ" },
    ...withPrefix,
  ];
});

// Р†РЅС–С†С–Р°Р»С–Р·Р°С†С–СЏ
onMounted(async () => {
  await loadBranches();
  await loadCompanyUsers();
});
</script>




