<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar + Main -->
    <div class="flex">
      <!-- Sidebar -->
      <aside class="w-64 bg-white shadow-sm min-h-screen flex flex-col">
        <div class="p-4 border-b">
          <h2 class="text-xl font-bold text-gray-900">Bid Open</h2>
        </div>
        <nav class="p-4 flex-1 overflow-y-auto space-y-1">
          <div
            v-for="item in menuLinks"
            :key="item.label"
            class="space-y-1"
          >
            <!-- Рівень 1 -->
            <button
              type="button"
              class="w-full flex items-center justify-between px-2.5 py-2 text-sm rounded-md hover:bg-gray-100 focus:outline-none group"
              :class="{
                'bg-gray-100 text-gray-900': isItemActive(item)
              }"
              @click="handleMenuClick(item)"
            >
              <div class="flex items-center gap-2 min-w-0">
                <UIcon
                  v-if="item.icon"
                  :name="item.icon"
                  class="shrink-0 size-5 text-gray-500 group-hover:text-gray-700"
                />
                <span class="truncate text-left">
                  {{ item.label }}
                </span>
              </div>
              <UIcon
                v-if="item.children && item.children.length"
                name="i-heroicons-chevron-down"
                class="size-4 text-gray-400 transition-transform duration-200"
                :class="{ '-rotate-90': !isExpanded(item) }"
              />
            </button>

            <!-- Підрівень -->
            <div
              v-if="item.children && item.children.length && isExpanded(item)"
              class="ms-4 border-s border-gray-200 ps-2 space-y-0.5"
            >
              <button
                v-for="child in item.children"
                :key="child.label"
                type="button"
                class="w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-md hover:bg-gray-50 focus:outline-none group"
                :class="{
                  'bg-gray-100 text-gray-900': isItemActive(child)
                }"
                @click="handleMenuClick(child)"
              >
                <UIcon
                  v-if="child.icon"
                  :name="child.icon"
                  class="shrink-0 size-4 text-gray-400 group-hover:text-gray-600"
                />
                <span class="truncate text-left">
                  {{ child.label }}
                </span>
              </button>
            </div>
          </div>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="flex-1">
        <!-- Top Bar -->
        <header class="bg-white shadow-sm border-b">
          <div class="px-6 py-4 flex justify-between items-center">
            <h1 class="text-xl font-semibold text-gray-900">{{ pageTitle }}</h1>
            <div class="flex items-center gap-4">
              <!-- Notifications -->
              <UButton
                icon="i-heroicons-bell"
                variant="ghost"
                color="gray"
                :badge="unreadNotificationsCount > 0 ? unreadNotificationsCount : undefined"
                @click="showNotifications = !showNotifications"
              />
              <!-- User Menu -->
              <UDropdown :items="userMenuItems">
                <UAvatar :alt="userEmail" />
              </UDropdown>
            </div>
          </div>
        </header>

        <!-- Content -->
        <div class="p-6">
          <slot />
        </div>
      </main>
    </div>

    <!-- Notifications Panel -->
    <UModal v-model="showNotifications">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Сповіщення</h3>
        </template>
        <div v-if="notifications.length === 0" class="text-center py-8 text-gray-500">
          Немає сповіщень
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="notification in notifications"
            :key="notification.id"
            class="p-3 border rounded"
            :class="{ 'bg-gray-50': notification.is_read }"
          >
            <h4 class="font-semibold">{{ notification.title }}</h4>
            <p class="text-sm text-gray-600">{{ notification.body }}</p>
            <p class="text-xs text-gray-400 mt-1">{{ formatDate(notification.created_at) }}</p>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const { isAuthenticated, checkAuth, getAuthHeaders } = useAuth()

// Перевірка автентифікації при завантаженні
await checkAuth()

// Якщо не автентифікований після перевірки - редірект на головну
if (!isAuthenticated.value) {
  await navigateTo('/')
}

const config = useRuntimeConfig()
const headers = getAuthHeaders()
const { data: me, error: meError } = await useFetch(`${config.public.apiBase}/auth/me/`, {
  headers
})

// Якщо помилка автентифікації - редірект
if (meError.value) {
  await navigateTo('/')
}

const userEmail = computed(() => me.value?.user?.email || '')
// Права поки що не використовуємо: усі авторизовані користувачі бачать весь функціонал
const permissions = computed(() => me.value?.permissions || [])
const showNotifications = ref(false)

// Меню кабінету згідно цільової структури
// Тимчасово БЕЗ обмежень по правах доступу: кожен авторизований користувач бачить усі пункти
const menuLinks = computed(() => {
  const links: any[] = []

  // Аналітика
  const analyticsChildren: any[] = [
    {
      label: 'Персональна аналітика',
      to: '/cabinet/dashboard?view=personal',
      icon: 'i-heroicons-user-circle'
    },
    {
      label: 'Зведена аналітика',
      to: '/cabinet/dashboard?view=summary',
      icon: 'i-heroicons-chart-bar'
    }
  ]
  links.push({
    label: 'Аналітика',
    icon: 'i-heroicons-chart-bar',
    children: analyticsChildren
  })

  // Участь в тендерах
  const participationChildren: any[] = [
    {
      label: 'Закупівлі',
      to: '/cabinet/participation?type=purchase',
      icon: 'i-heroicons-shopping-cart'
    },
    {
      label: 'Продажі',
      to: '/cabinet/participation?type=sales',
      icon: 'i-heroicons-banknotes'
    }
  ]
  links.push({
    label: 'Участь в тендерах',
    icon: 'i-heroicons-hand-raised',
    children: participationChildren
  })

  // Продажі
  const salesChildren: any[] = [
    {
      label: 'Створити процедуру',
      to: '/cabinet/tenders/create?type=sales',
      icon: 'i-heroicons-plus-circle'
    },
    {
      label: 'Журнал продажів',
      to: '/cabinet/tenders?view=sales',
      icon: 'i-heroicons-document-text'
    }
  ]
  links.push({
    label: 'Продажі',
    icon: 'i-heroicons-banknotes',
    children: salesChildren
  })

  // Закупівлі
  const purchaseChildren: any[] = [
    {
      label: 'Створити процедуру',
      to: '/cabinet/tenders/create?type=purchase',
      icon: 'i-heroicons-plus-circle'
    },
    {
      label: 'Журнал закупівель',
      to: '/cabinet/tenders?view=purchase',
      icon: 'i-heroicons-document-text'
    }
  ]
  links.push({
    label: 'Закупівлі',
    icon: 'i-heroicons-shopping-cart',
    children: purchaseChildren
  })

  // Постачальники
  links.push({
    label: 'Постачальники',
    to: '/cabinet/suppliers',
    icon: 'i-heroicons-building-office'
  })

  // Довідники
  const referenceChildren: any[] = []
  referenceChildren.push(
    {
      label: 'Номенклатури',
      to: '/cabinet/reference/nomenclature',
      icon: 'i-heroicons-cube'
    },
    {
      label: 'Категорії',
      to: '/cabinet/reference/categories',
      icon: 'i-heroicons-folder'
    },
    {
      label: 'Статті витрат',
      to: '/cabinet/reference/expenses',
      icon: 'i-heroicons-currency-dollar'
    },
    {
      label: 'Філіали підрозділи',
      to: '/cabinet/reference/branches',
      icon: 'i-heroicons-building-office-2'
    },
    {
      label: 'Критерії тендерів',
      to: '/cabinet/reference/criteria',
      icon: 'i-heroicons-adjustments-horizontal'
    },
    {
      label: 'Атрибути тендерів',
      to: '/cabinet/reference/attributes',
      icon: 'i-heroicons-bars-3'
    }
  )
  if (referenceChildren.length) {
    links.push({
      label: 'Довідники',
      icon: 'i-heroicons-book-open',
      children: referenceChildren
    })
  }

  // Моделі погодження (поки що як плейсхолдери для налаштувань)
  links.push({
    label: 'Моделі погодження',
    icon: 'i-heroicons-clipboard-document-check',
    children: [
      {
        label: 'Довідник моделей',
        to: '/cabinet/approval/models',
        icon: 'i-heroicons-clipboard-document-list'
      },
      {
        label: 'Матриця діапазонів',
        to: '/cabinet/approval/range-matrix',
        icon: 'i-heroicons-squares-2x2'
      },
      {
        label: 'Ролі для моделей',
        to: '/cabinet/approval/model-roles',
        icon: 'i-heroicons-user-group'
      }
    ]
  })

  // Налаштування
  const settingsChildren: any[] = []
  settingsChildren.push(
    {
      label: 'Користувачі',
      to: '/cabinet/users',
      icon: 'i-heroicons-users'
    },
    {
      label: 'Групи для прав доступу',
      to: '/cabinet/roles',
      icon: 'i-heroicons-shield-check'
    },
    {
      label: 'Права доступу',
      to: '/cabinet/permissions',
      icon: 'i-heroicons-key'
    },
    {
      label: 'Системні налаштування',
      to: '/cabinet/settings',
      icon: 'i-heroicons-cog-6-tooth'
    }
  )
  if (settingsChildren.length) {
    links.push({
      label: 'Налаштування',
      icon: 'i-heroicons-cog-8-tooth',
      children: settingsChildren
    })
  }

  return links
})

// Розгортання пунктів меню з підпунктами
const expandedSections = ref<string[]>([])

const isExpanded = (item: any) => {
  return expandedSections.value.includes(item.label)
}

const toggleSection = (item: any) => {
  const label = item.label
  if (!label) return
  const idx = expandedSections.value.indexOf(label)
  if (idx > -1) {
    expandedSections.value.splice(idx, 1)
  } else {
    expandedSections.value.push(label)
  }
}

const route = useRoute()

const isItemActive = (item: any) => {
  if (!item.to) {
    // активний, якщо будь-який дочірній активний
    return Array.isArray(item.children) && item.children.some((child: any) => isItemActive(child))
  }
  const [pathOnly] = String(item.to).split('?')
  return route.path === pathOnly
}

const handleMenuClick = (item: any) => {
  if (item.children && item.children.length) {
    // пункт з підменю — просто розгортаємо/згортаємо
    toggleSection(item)
    return
  }
  if (item.to) {
    navigateTo(item.to)
  }
}

const userMenuItems = [
  [
    {
      label: 'Профіль',
      icon: 'i-heroicons-user-circle',
      to: '/cabinet/profile'
    },
    {
      label: 'Вийти',
      icon: 'i-heroicons-arrow-right-on-rectangle',
      click: () => {
        const { logout } = useAuth()
        logout()
      }
    }
  ]
]

const pageTitle = useRoute().meta.title || 'Кабінет'

// Notifications
const { data: notifications } = await useFetch(`${config.public.apiBase}/notifications/`, {
  headers: getAuthHeaders()
})
const unreadNotificationsCount = computed(() => notifications.value?.filter((n: any) => !n.is_read).length || 0)

const formatDate = (date: string) => {
  return new Date(date).toLocaleString('uk-UA')
}
</script>
