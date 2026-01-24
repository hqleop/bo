<template>
  <div class="h-full flex gap-4">
    <!-- Колонка 1: Філіали -->
    <div class="flex-1 border-r border-gray-200 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Філіали</h3>
        <UButton icon="i-heroicons-plus" size="sm" @click="openBranchModal()">Додати</UButton>
      </div>
      <div class="space-y-1">
        <div
          v-for="branch in branches"
          :key="branch.id"
          class="flex items-center justify-between p-2 rounded hover:bg-gray-100 cursor-pointer"
          :class="{ 'bg-blue-50 border border-blue-200': selectedBranch?.id === branch.id }"
          @click="selectBranch(branch)"
        >
          <div class="flex-1">
            <div class="font-medium">{{ branch.name }}</div>
            <div v-if="branch.code" class="text-xs text-gray-500">{{ branch.code }}</div>
            <div v-if="branch.user_count > 0" class="text-xs text-gray-400">
              {{ branch.user_count }} користувачів
            </div>
          </div>
          <div class="flex gap-1">
            <UButton
              icon="i-heroicons-pencil"
              size="xs"
              variant="ghost"
              @click.stop="openBranchModal(branch)"
            />
            <UButton
              icon="i-heroicons-trash"
              size="xs"
              variant="ghost"
              color="red"
              @click.stop="deleteBranch(branch)"
            />
          </div>
        </div>
        <div v-if="branches.length === 0" class="text-center text-gray-400 py-8">
          Немає філіалів
        </div>
      </div>
    </div>

    <!-- Колонка 2: Підрозділи -->
    <div class="flex-1 border-r border-gray-200 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Підрозділи</h3>
        <UButton
          icon="i-heroicons-plus"
          size="sm"
          :disabled="!selectedBranch"
          @click="openDepartmentModal()"
        >
          Додати
        </UButton>
      </div>
      <div v-if="!selectedBranch" class="text-center text-gray-400 py-8">
        Оберіть філіал
      </div>
      <div v-else class="space-y-1">
        <div
          v-for="dept in departments"
          :key="dept.id"
          class="flex items-center justify-between p-2 rounded hover:bg-gray-100 cursor-pointer"
          :class="{ 'bg-blue-50 border border-blue-200': selectedDepartment?.id === dept.id }"
          @click="selectDepartment(dept)"
        >
          <div class="flex-1">
            <div class="font-medium">{{ dept.name }}</div>
            <div v-if="dept.user_count > 0" class="text-xs text-gray-400">
              {{ dept.user_count }} користувачів
            </div>
          </div>
          <div class="flex gap-1">
            <UButton
              icon="i-heroicons-pencil"
              size="xs"
              variant="ghost"
              @click.stop="openDepartmentModal(dept)"
            />
            <UButton
              icon="i-heroicons-trash"
              size="xs"
              variant="ghost"
              color="red"
              @click.stop="deleteDepartment(dept)"
            />
          </div>
        </div>
        <div v-if="departments.length === 0" class="text-center text-gray-400 py-8">
          Немає підрозділів
        </div>
      </div>
    </div>

    <!-- Колонка 3: Користувачі -->
    <div class="flex-1 p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Користувачі</h3>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-plus"
            size="sm"
            :disabled="!selectedBranch && !selectedDepartment"
            @click="openAddUsersModal()"
          >
            Додати
          </UButton>
          <UButton
            icon="i-heroicons-trash"
            size="sm"
            variant="outline"
            color="red"
            :disabled="!selectedBranch && !selectedDepartment || selectedUsers.length === 0"
            @click="openRemoveUsersModal()"
          >
            Видалити
          </UButton>
        </div>
      </div>
      <div v-if="!selectedBranch && !selectedDepartment" class="text-center text-gray-400 py-8">
        Оберіть філіал або підрозділ
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="user in currentUsers"
          :key="user.id"
          class="flex items-center justify-between p-2 rounded hover:bg-gray-100"
        >
          <div class="flex-1">
            <div class="font-medium">{{ user.user.first_name }} {{ user.user.last_name }}</div>
            <div class="text-sm text-gray-500">{{ user.user.email }}</div>
          </div>
          <UCheckbox
            :model-value="selectedUsers.includes(user.id)"
            @update:model-value="toggleUserSelection(user.id)"
          />
        </div>
        <div v-if="currentUsers.length === 0" class="text-center text-gray-400 py-8">
          Немає користувачів
        </div>
      </div>
    </div>

    <!-- Модальне вікно для філіалу -->
    <UModal v-model="showBranchModal">
      <UCard>
        <template #header>
          <h3>{{ editingBranch ? 'Редагувати філіал' : 'Додати філіал' }}</h3>
        </template>
        <UForm :state="branchForm" @submit="saveBranch" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="branchForm.name" />
          </UFormGroup>
          <UFormGroup label="Код" name="code">
            <UInput v-model="branchForm.code" />
          </UFormGroup>
          <UFormGroup label="Батьківський філіал" name="parent_id">
            <USelect
              v-model="branchForm.parent_id"
              :options="availableParentBranches"
              option-attribute="name"
              value-attribute="id"
              placeholder="Без батьківського філіалу"
              :disabled="editingBranch && editingBranch.id === branchForm.parent_id"
            />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showBranchModal = false">Скасувати</UButton>
            <UButton type="submit" block :loading="saving">Зберегти</UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>

    <!-- Модальне вікно для підрозділу -->
    <UModal v-model="showDepartmentModal">
      <UCard>
        <template #header>
          <h3>{{ editingDepartment ? 'Редагувати підрозділ' : 'Додати підрозділ' }}</h3>
        </template>
        <UForm :state="departmentForm" @submit="saveDepartment" class="space-y-4">
          <UFormGroup label="Назва" name="name" required>
            <UInput v-model="departmentForm.name" />
          </UFormGroup>
          <UFormGroup label="Батьківський підрозділ" name="parent_id">
            <USelect
              v-model="departmentForm.parent_id"
              :options="availableParentDepartments"
              option-attribute="name"
              value-attribute="id"
              placeholder="Без батьківського підрозділу"
              :disabled="editingDepartment && editingDepartment.id === departmentForm.parent_id"
            />
          </UFormGroup>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showDepartmentModal = false">Скасувати</UButton>
            <UButton type="submit" block :loading="saving">Зберегти</UButton>
          </div>
        </UForm>
      </UCard>
    </UModal>

    <!-- Модальне вікно для додавання користувачів -->
    <UModal v-model="showAddUsersModal">
      <UCard>
        <template #header>
          <h3>Додати користувачів</h3>
        </template>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="user in companyUsers"
            :key="user.id"
            class="flex items-center p-2 rounded hover:bg-gray-50"
          >
            <UCheckbox
              :model-value="usersToAdd.includes(user.id)"
              @update:model-value="toggleUserToAdd(user.id)"
            />
            <div class="ml-3 flex-1">
              <div class="font-medium">{{ user.first_name }} {{ user.last_name }}</div>
              <div class="text-sm text-gray-500">{{ user.email }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showAddUsersModal = false">Скасувати</UButton>
            <UButton block @click="addUsers" :loading="saving">Додати</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Модальне вікно для видалення користувачів -->
    <UModal v-model="showRemoveUsersModal">
      <UCard>
        <template #header>
          <h3>Видалити користувачів</h3>
        </template>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="user in currentUsers.filter((u) => selectedUsers.includes(u.id))"
            :key="user.id"
            class="flex items-center p-2 rounded hover:bg-gray-50"
          >
            <UCheckbox
              :model-value="usersToRemove.includes(user.id)"
              @update:model-value="toggleUserToRemove(user.id)"
            />
            <div class="ml-3 flex-1">
              <div class="font-medium">{{ user.user.first_name }} {{ user.user.last_name }}</div>
              <div class="text-sm text-gray-500">{{ user.user.email }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex gap-4">
            <UButton variant="outline" block @click="showRemoveUsersModal = false">Скасувати</UButton>
            <UButton block color="red" @click="removeUsers" :loading="saving">Видалити</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'cabinet',
  middleware: 'auth',
  meta: {
    title: 'Філіали підрозділи'
  }
})

const config = useRuntimeConfig()
const { getAuthHeaders } = useAuth()
const { fetch } = useApi()

// Дані
const branches = ref<any[]>([])
const departments = ref<any[]>([])
const currentUsers = ref<any[]>([])
const companyUsers = ref<any[]>([])

// Вибраний елемент
const selectedBranch = ref<any>(null)
const selectedDepartment = ref<any>(null)
const selectedUsers = ref<number[]>([])

// Модальні вікна
const showBranchModal = ref(false)
const showDepartmentModal = ref(false)
const showAddUsersModal = ref(false)
const showRemoveUsersModal = ref(false)
const saving = ref(false)

// Форми
const editingBranch = ref<any>(null)
const editingDepartment = ref<any>(null)
const branchForm = reactive({
  name: '',
  code: '',
  parent_id: null as number | null
})
const departmentForm = reactive({
  name: '',
  parent_id: null as number | null
})
const usersToAdd = ref<number[]>([])
const usersToRemove = ref<number[]>([])

// Завантаження даних
const loadBranches = async () => {
  const { data } = await fetch('/branches/', {
    headers: getAuthHeaders()
  })
  if (data) {
    branches.value = data
  }
}

const loadDepartments = async () => {
  if (!selectedBranch.value) return
  const { data } = await fetch(`/departments/?branch_id=${selectedBranch.value.id}`, {
    headers: getAuthHeaders()
  })
  if (data) {
    departments.value = data
  }
}

const loadUsers = async () => {
  if (!selectedBranch.value && !selectedDepartment.value) {
    currentUsers.value = []
    return
  }

  if (selectedDepartment.value) {
    const { data } = await fetch(`/department-users/?department_id=${selectedDepartment.value.id}`, {
      headers: getAuthHeaders()
    })
    currentUsers.value = data || []
  } else if (selectedBranch.value) {
    const { data } = await fetch(`/branch-users/?branch_id=${selectedBranch.value.id}`, {
      headers: getAuthHeaders()
    })
    currentUsers.value = data || []
  }
}

const loadCompanyUsers = async () => {
  const { data } = await fetch('/memberships/', {
    headers: getAuthHeaders()
  })
  if (data) {
    companyUsers.value = data
      .filter((m: any) => m.status === 'approved')
      .map((m: any) => m.user)
  }
}

// Обробники подій
const selectBranch = (branch: any) => {
  selectedBranch.value = branch
  selectedDepartment.value = null
  selectedUsers.value = []
  loadDepartments()
  loadUsers()
}

const selectDepartment = (dept: any) => {
  selectedDepartment.value = dept
  selectedUsers.value = []
  loadUsers()
}

const toggleUserSelection = (userId: number) => {
  const index = selectedUsers.value.indexOf(userId)
  if (index > -1) {
    selectedUsers.value.splice(index, 1)
  } else {
    selectedUsers.value.push(userId)
  }
}

// Філіали
const openBranchModal = (branch?: any) => {
  editingBranch.value = branch || null
  if (branch) {
    branchForm.name = branch.name
    branchForm.code = branch.code || ''
    branchForm.parent_id = branch.parent || null
  } else {
    branchForm.name = ''
    branchForm.code = ''
    branchForm.parent_id = null
  }
  showBranchModal.value = true
}

const saveBranch = async () => {
  saving.value = true
  const payload: any = {
    name: branchForm.name,
    code: branchForm.code,
    company: selectedBranch.value?.company || (await getCurrentCompany())
  }
  if (branchForm.parent_id) {
    payload.parent = branchForm.parent_id
  }

  const endpoint = editingBranch.value ? `/branches/${editingBranch.value.id}/` : '/branches/'
  const method = editingBranch.value ? 'PUT' : 'POST'

  const { data, error } = await fetch(endpoint, {
    method,
    body: payload,
    headers: getAuthHeaders()
  })

  saving.value = false
  if (error) {
    alert(error.detail || 'Помилка збереження')
    return
  }

  showBranchModal.value = false
  await loadBranches()
}

const deleteBranch = async (branch: any) => {
  if (!confirm(`Видалити філіал "${branch.name}"?`)) return

  const { error } = await fetch(`/branches/${branch.id}/`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })

  if (error) {
    alert('Помилка видалення')
    return
  }

  if (selectedBranch.value?.id === branch.id) {
    selectedBranch.value = null
    selectedDepartment.value = null
  }
  await loadBranches()
}

// Підрозділи
const openDepartmentModal = (dept?: any) => {
  editingDepartment.value = dept || null
  if (dept) {
    departmentForm.name = dept.name
    departmentForm.parent_id = dept.parent || null
  } else {
    departmentForm.name = ''
    departmentForm.parent_id = null
  }
  showDepartmentModal.value = true
}

const saveDepartment = async () => {
  if (!selectedBranch.value) return

  saving.value = true
  const payload: any = {
    name: departmentForm.name,
    branch: selectedBranch.value.id
  }
  if (departmentForm.parent_id) {
    payload.parent = departmentForm.parent_id
  }

  const endpoint = editingDepartment.value
    ? `/departments/${editingDepartment.value.id}/`
    : '/departments/'
  const method = editingDepartment.value ? 'PUT' : 'POST'

  const { data, error } = await fetch(endpoint, {
    method,
    body: payload,
    headers: getAuthHeaders()
  })

  saving.value = false
  if (error) {
    alert(error.detail || 'Помилка збереження')
    return
  }

  showDepartmentModal.value = false
  await loadDepartments()
}

const deleteDepartment = async (dept: any) => {
  if (!confirm(`Видалити підрозділ "${dept.name}"?`)) return

  const { error } = await fetch(`/departments/${dept.id}/`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })

  if (error) {
    alert('Помилка видалення')
    return
  }

  if (selectedDepartment.value?.id === dept.id) {
    selectedDepartment.value = null
  }
  await loadDepartments()
}

// Користувачі
const openAddUsersModal = async () => {
  usersToAdd.value = []
  await loadCompanyUsers()
  showAddUsersModal.value = true
}

const toggleUserToAdd = (userId: number) => {
  const index = usersToAdd.value.indexOf(userId)
  if (index > -1) {
    usersToAdd.value.splice(index, 1)
  } else {
    usersToAdd.value.push(userId)
  }
}

const addUsers = async () => {
  if (usersToAdd.value.length === 0) return

  saving.value = true
  const endpoint = selectedDepartment.value
    ? '/department-users/'
    : '/branch-users/'
  const payload: any = {
    user_ids: usersToAdd.value
  }

  if (selectedDepartment.value) {
    payload.department = selectedDepartment.value.id
  } else if (selectedBranch.value) {
    payload.branch = selectedBranch.value.id
  }

  const { error } = await fetch(endpoint, {
    method: 'POST',
    body: payload,
    headers: getAuthHeaders()
  })

  saving.value = false
  if (error) {
    alert(error.detail || 'Помилка додавання')
    return
  }

  showAddUsersModal.value = false
  await loadUsers()
}

const openRemoveUsersModal = () => {
  usersToRemove.value = [...selectedUsers.value]
  showRemoveUsersModal.value = true
}

const toggleUserToRemove = (userId: number) => {
  const index = usersToRemove.value.indexOf(userId)
  if (index > -1) {
    usersToRemove.value.splice(index, 1)
  } else {
    usersToRemove.value.push(userId)
  }
}

const removeUsers = async () => {
  if (usersToRemove.value.length === 0) return

  saving.value = true
  const endpoint = selectedDepartment.value ? '/department-users/' : '/branch-users/'

  // Видаляємо по одному
  for (const userId of usersToRemove.value) {
    const userItem = currentUsers.value.find((u) => u.user.id === userId)
    if (userItem) {
      await fetch(`${endpoint}${userItem.id}/`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
    }
  }

  saving.value = false
  showRemoveUsersModal.value = false
  selectedUsers.value = []
  await loadUsers()
}

// Computed
const availableParentBranches = computed(() => {
  return branches.value.filter((b) => !editingBranch.value || b.id !== editingBranch.value.id)
})

const availableParentDepartments = computed(() => {
  return departments.value.filter(
    (d) => !editingDepartment.value || d.id !== editingDepartment.value.id
  )
})

const getCurrentCompany = async () => {
  const { data } = await fetch('/auth/me/', {
    headers: getAuthHeaders()
  })
  if (data?.memberships?.[0]) {
    return data.memberships[0].company.id
  }
  return null
}

// Ініціалізація
onMounted(async () => {
  await loadBranches()
  await loadCompanyUsers()
})
</script>
