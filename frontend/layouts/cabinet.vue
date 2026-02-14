<template>
  <div class="h-screen flex flex-col overflow-hidden bg-gray-50">
    <!-- Sidebar + Main: фіксована висота по екрану, окремий скрол у сайдбарі та в контенті -->
    <div class="flex flex-1 min-h-0">
      <!-- Sidebar: висота по екрану, скрол лише у навігації -->
      <aside class="w-64 flex-shrink-0 h-full flex flex-col overflow-hidden bg-white shadow-sm">
        <div class="h-16 flex-shrink-0 px-4 border-b flex items-center">
          <h2 class="text-xl font-bold text-gray-900">Bid Open</h2>
        </div>
        <nav class="flex-1 min-h-0 overflow-y-auto p-4">
          <UNavigationMenu
            orientation="vertical"
            :items="navigationItems"
            color="neutral"
            variant="link"
            highlight
            class="data-[orientation=vertical]:w-full data-[orientation=vertical]:flex-col data-[orientation=vertical]:gap-0.5"
          />
        </nav>
      </aside>

      <!-- Main: висота по екрану, скрол лише у робочій області -->
      <main class="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
        <header class="h-16 flex-shrink-0 bg-white shadow-sm border-b">
          <div class="px-6 py-4 flex justify-between items-center h-full">
            <h1 class="text-xl font-semibold text-gray-900">{{ pageTitle }}</h1>
            <div class="flex items-center gap-4">
              <UButton
                icon="i-heroicons-bell"
                variant="ghost"
                color="neutral"
                :badge="
                  unreadNotificationsCount > 0
                    ? unreadNotificationsCount
                    : undefined
                "
                @click="showNotifications = !showNotifications"
              />
              <UButton variant="ghost" @click="logoutUser">
                <UAvatar :alt="userEmail" />
              </UButton>
            </div>
          </div>
        </header>

        <div class="flex-1 min-h-0 overflow-y-auto p-6">
          <div class="h-full">
            <slot />
          </div>
        </div>
      </main>
    </div>

    <!-- Notifications Panel -->
    <UModal v-model:open="showNotifications">
      <template #content>
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
      </template>
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
// Права поки що не використовуємо: усі авторизовані користувачі бачать весь функціонал
const permissions = computed(() => me.value?.permissions || []);
const showNotifications = ref(false);

// Меню кабінету згідно цільової структури
// Тимчасово БЕЗ обмежень по правах доступу: кожен авторизований користувач бачить усі пункти
const menuLinks = computed(() => {
  const links: any[] = [];

  // Аналітика
  const analyticsChildren: any[] = [
    {
      label: "Персональна аналітика",
      to: "/cabinet/dashboard?view=personal",
      icon: "i-heroicons-user-circle",
    },
    {
      label: "Зведена аналітика",
      to: "/cabinet/dashboard?view=summary",
      icon: "i-heroicons-chart-bar",
    },
  ];
  links.push({
    label: "Аналітика",
    icon: "i-heroicons-chart-bar",
    children: analyticsChildren,
  });

  // Участь в тендерах
  const participationChildren: any[] = [
    {
      label: "Закупівлі",
      to: "/cabinet/participation?type=purchase",
      icon: "i-heroicons-shopping-cart",
    },
    {
      label: "Продажі",
      to: "/cabinet/participation?type=sales",
      icon: "i-heroicons-banknotes",
    },
  ];
  links.push({
    label: "Участь в тендерах",
    icon: "i-heroicons-hand-raised",
    children: participationChildren,
  });

  // Продажі
  const salesChildren: any[] = [
    {
      label: "Створити процедуру",
      to: "/cabinet/tenders/create/sales",
      icon: "i-heroicons-plus-circle",
    },
    {
      label: "Журнал продажів",
      to: "/cabinet/tenders?view=sales",
      icon: "i-heroicons-document-text",
    },
  ];
  links.push({
    label: "Продажі",
    icon: "i-heroicons-banknotes",
    children: salesChildren,
  });

  // Закупівлі
  const purchaseChildren: any[] = [
    {
      label: "Створити процедуру",
      to: "/cabinet/tenders/create/purchase",
      icon: "i-heroicons-plus-circle",
    },
    {
      label: "Журнал закупівель",
      to: "/cabinet/tenders?view=purchase",
      icon: "i-heroicons-document-text",
    },
  ];
  links.push({
    label: "Закупівлі",
    icon: "i-heroicons-shopping-cart",
    children: purchaseChildren,
  });

  // Контрагенти
  links.push({
    label: "Контрагенти",
    to: "/cabinet/suppliers",
    icon: "i-heroicons-building-office",
  });

  // Довідники
  const referenceChildren: any[] = [];
  referenceChildren.push(
    {
      label: "Номенклатури",
      to: "/cabinet/reference/nomenclature",
      icon: "i-heroicons-cube",
    },
    {
      label: "Категорії",
      to: "/cabinet/reference/categories",
      icon: "i-heroicons-folder",
    },
    {
      label: "Статті витрат",
      to: "/cabinet/reference/expenses",
      icon: "i-heroicons-currency-dollar",
    },
    {
      label: "Філіали підрозділи",
      to: "/cabinet/reference/branches",
      icon: "i-heroicons-building-office-2",
    },
    {
      label: "Критерії тендерів",
      to: "/cabinet/reference/criteria",
      icon: "i-heroicons-adjustments-horizontal",
    },
    {
      label: "Атрибути тендерів",
      to: "/cabinet/reference/attributes",
      icon: "i-heroicons-bars-3",
    },
  );
  if (referenceChildren.length) {
    links.push({
      label: "Довідники",
      icon: "i-heroicons-book-open",
      children: referenceChildren,
    });
  }

  // Моделі погодження (поки що як плейсхолдери для налаштувань)
  links.push({
    label: "Моделі погодження",
    icon: "i-heroicons-clipboard-document-check",
    children: [
      {
        label: "Довідник моделей",
        to: "/cabinet/approval/models",
        icon: "i-heroicons-clipboard-document-list",
      },
      {
        label: "Матриця діапазонів",
        to: "/cabinet/approval/range-matrix",
        icon: "i-heroicons-squares-2x2",
      },
      {
        label: "Ролі для моделей",
        to: "/cabinet/approval/model-roles",
        icon: "i-heroicons-user-group",
      },
    ],
  });

  // Налаштування
  const settingsChildren: any[] = [];
  settingsChildren.push(
    {
      label: "Користувачі",
      to: "/cabinet/users",
      icon: "i-heroicons-users",
    },
    {
      label: "Групи для прав доступу",
      to: "/cabinet/roles",
      icon: "i-heroicons-shield-check",
    },
    {
      label: "Права доступу",
      to: "/cabinet/permissions",
      icon: "i-heroicons-key",
    },
    {
      label: "Системні налаштування",
      to: "/cabinet/settings",
      icon: "i-heroicons-cog-6-tooth",
    },
  );
  if (settingsChildren.length) {
    links.push({
      label: "Налаштування",
      icon: "i-heroicons-cog-8-tooth",
      children: settingsChildren,
    });
  }

  return links;
});

const route = useRoute();

const isPathActive = (to: string | undefined) => {
  if (!to) return false;
  const [pathOnly] = String(to).split("?");
  return route.path === pathOnly;
};

// Пункти меню для UNavigationMenu з позначкою активного та defaultOpen для розділу з активним дочірнім
const navigationItems = computed(() => {
  return menuLinks.value.map((item: any) => {
    const hasChildren = Array.isArray(item.children) && item.children.length;
    const children = hasChildren
      ? item.children.map((child: any) => ({
          ...child,
          active: isPathActive(child.to),
        }))
      : undefined;
    const hasActiveChild = hasChildren && children.some((c: any) => c.active);
    return {
      ...item,
      ...(children && { children }),
      active: hasChildren ? false : isPathActive(item.to),
      defaultOpen: hasActiveChild,
    };
  });
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

function logoutUser() {
  const { logout } = useAuth();
  logout();
}

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
