<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar + Main -->
    <div class="flex">
      <!-- Sidebar -->
      <aside class="w-64 bg-white shadow-sm min-h-screen">
        <div class="h-16 px-4 border-b flex items-center">
          <h2 class="text-xl font-bold text-gray-900">Bid Open</h2>
        </div>
        <nav class="p-4">
          <UVerticalNavigation :links="menuLinks" />
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="flex-1">
        <!-- Top Bar -->
        <header class="bg-white shadow-sm border-b h-16">
          <div class="px-6 py-4 flex justify-between items-center">
            <h1 class="text-xl font-semibold text-gray-900">{{ pageTitle }}</h1>
            <div class="flex items-center gap-4">
              <!-- Notifications -->
              <UButton
                icon="i-heroicons-bell"
                variant="ghost"
                color="gray"
                :badge="
                  unreadNotificationsCount > 0
                    ? unreadNotificationsCount
                    : undefined
                "
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
        <div
          v-if="notifications.length === 0"
          class="text-center py-8 text-gray-500"
        >
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
            <p class="text-xs text-gray-400 mt-1">
              {{ formatDate(notification.created_at) }}
            </p>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const { isAuthenticated, checkAuth, getAuthHeaders } = useAuth();

// Перевірка автентифікації при завантаженні
await checkAuth();

// Якщо не автентифікований після перевірки - редірект на головну
if (!isAuthenticated.value) {
  await navigateTo("/");
}

const config = useRuntimeConfig();
const headers = getAuthHeaders();
const { data: me, error: meError } = await useFetch(
  `${config.public.apiBase}/auth/me/`,
  {
    headers,
  },
);

// Якщо помилка автентифікації - редірект
if (meError.value) {
  await navigateTo("/");
}

const userEmail = computed(() => me.value?.user?.email || "");
const permissions = computed(() => me.value?.permissions || []);
const showNotifications = ref(false);

// Menu links based on permissions
const menuLinks = computed(() => {
  const links = [];
  if (permissions.value.includes("dashboard.view")) {
    links.push({
      label: "Загальна аналітика",
      to: "/cabinet/dashboard",
      icon: "i-heroicons-chart-bar",
    });
  }
  if (permissions.value.includes("tenders.view")) {
    links.push({
      label: "Тендери",
      to: "/cabinet/tenders",
      icon: "i-heroicons-document-text",
    });
  }
  if (permissions.value.includes("tenders.create")) {
    links.push({
      label: "Створення тендерів",
      to: "/cabinet/tenders/create",
      icon: "i-heroicons-plus-circle",
    });
  }
  if (permissions.value.includes("participation.view")) {
    links.push({
      label: "Участь в тендерах",
      to: "/cabinet/participation",
      icon: "i-heroicons-hand-raised",
    });
  }
  if (permissions.value.includes("suppliers.view")) {
    links.push({
      label: "Постачальники",
      to: "/cabinet/suppliers",
      icon: "i-heroicons-building-office",
    });
  }
  // Довідники
  if (permissions.value.includes("nomenclature.view")) {
    links.push({
      label: "Номенклатури",
      to: "/cabinet/reference/nomenclature",
      icon: "i-heroicons-cube",
    });
  }
  if (permissions.value.includes("categories.view")) {
    links.push({
      label: "Категорії",
      to: "/cabinet/reference/categories",
      icon: "i-heroicons-folder",
    });
  }
  if (permissions.value.includes("expenses.view")) {
    links.push({
      label: "Статті витрат",
      to: "/cabinet/reference/expenses",
      icon: "i-heroicons-currency-dollar",
    });
  }
  if (permissions.value.includes("branches.view")) {
    links.push({
      label: "Філіали підрозділи",
      to: "/cabinet/reference/branches",
      icon: "i-heroicons-building-office-2",
    });
  }
  if (permissions.value.includes("templates.view")) {
    links.push({
      label: "Шаблони",
      to: "/cabinet/templates",
      icon: "i-heroicons-document-duplicate",
    });
  }
  if (permissions.value.includes("settings.view")) {
    links.push({
      label: "Налаштування",
      to: "/cabinet/settings",
      icon: "i-heroicons-cog-6-tooth",
    });
  }
  if (permissions.value.includes("users.manage")) {
    links.push({
      label: "Користувачі",
      to: "/cabinet/users",
      icon: "i-heroicons-users",
    });
  }
  // Ролі приховані - створюються виключно в рамках компанії
  // if (permissions.value.includes('roles.manage')) {
  //   links.push({ label: 'Ролі', to: '/cabinet/roles', icon: 'i-heroicons-shield-check' })
  // }
  if (permissions.value.includes("permissions.manage")) {
    links.push({
      label: "Права доступу",
      to: "/cabinet/permissions",
      icon: "i-heroicons-key",
    });
  }
  return links;
});

const userMenuItems = [
  [
    {
      label: "Профіль",
      icon: "i-heroicons-user-circle",
      to: "/cabinet/profile",
    },
    {
      label: "Вийти",
      icon: "i-heroicons-arrow-right-on-rectangle",
      click: () => {
        const { logout } = useAuth();
        logout();
      },
    },
  ],
];

const pageTitle = useRoute().meta.title || "Кабінет";

// Notifications
const { data: notifications } = await useFetch(
  `${config.public.apiBase}/notifications/`,
  {
    headers: getAuthHeaders(),
  },
);
const unreadNotificationsCount = computed(
  () => notifications.value?.filter((n: any) => !n.is_read).length || 0,
);

const formatDate = (date: string) => {
  return new Date(date).toLocaleString("uk-UA");
};
</script>
