<template>
  <div
    class="cabinet-density h-screen flex flex-col overflow-hidden bg-gradient-to-b from-gray-50 to-gray-100/60"
  >
    <!-- Sidebar + Main: фіксована висота по екрану, окремий скрол у сайдбарі та в контенті -->
    <div class="flex flex-1 min-h-0">
      <!-- Sidebar: висота по екрану, скрол лише у навігації -->
      <UDashboardSidebar
        :items="navigationItems"
        :collapsed="isSidebarCollapsed"
        title="Bid Open"
        compact-title="BO"
        @toggle="toggleSidebar"
      />

      <!-- Main: висота по екрану, скрол лише у робочій області -->
      <main class="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
        <header class="h-14 flex-shrink-0 bg-white shadow-sm border-b border-gray-200">
          <div class="px-4 py-2 flex justify-between items-center h-full">
            <h1 class="text-lg font-semibold text-gray-900">{{ pageTitle }}</h1>
            <div class="flex items-center gap-3">
              <UButton
                icon="i-heroicons-clipboard-document-list"
                variant="ghost"
                color="neutral"
                :chip="hasUnseenActiveTasks ? { inset: true } : undefined"
                title="Завдання користувача"
                @click="openTasksPage"
              />
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
              <NuxtLink
                to="/cabinet/profile"
                class="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-gray-100 ring-1 ring-transparent hover:ring-gray-200 transition shrink-0"
              >
                <UAvatar
                  :src="headerAvatar"
                  :alt="headerName || userEmail"
                  size="sm"
                  class="flex-shrink-0"
                />
                <span
                  class="text-sm font-medium text-gray-700 whitespace-nowrap"
                >
                  {{
                    meLoading ? "…" : headerName || userEmail || "Користувач"
                  }}
                </span>
              </NuxtLink>
              <UButton
                variant="outline"
                color="neutral"
                size="sm"
                @click="logoutUser"
              >
                Вийти
              </UButton>
            </div>
          </div>
        </header>

        <div class="flex-1 min-h-0 overflow-y-auto p-4">
          <div
            class="h-full border-0 ring-0 outline-none"
            :key="route.fullPath"
          >
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
                class="p-3 border border-gray-200 rounded-lg"
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
const { me, refreshMe } = useMe();

// Завантажуємо me одразу після перевірки авторизації (на клієнті), щоб ім'я та аватар були при першому рендері
const meLoading = ref(true);
if (import.meta.client) {
  try {
    const mePayload = await refreshMe();
    const registrationStep = Number((mePayload as any)?.registration_step ?? 4);
    if (registrationStep < 4) {
      await navigateTo(`/register?step=${Math.min(Math.max(registrationStep, 1), 3)}`);
    } else {
      const hasMemberships =
        Array.isArray(mePayload?.memberships) && mePayload.memberships.length > 0;
      if (!hasMemberships) {
        await navigateTo("/register?step=2");
      }
    }
  } finally {
    meLoading.value = false;
  }
}

// Локальні computed безпосередньо від me — гарантована реактивність у шапці
const headerName = computed(() => {
  const u = me.value?.user;
  if (!u) return "";
  const name = [u.first_name, u.last_name].filter(Boolean).join(" ").trim();
  return name || u.email || "";
});
const headerAvatar = computed(() => me.value?.user?.avatar ?? null);
const userEmail = computed(() => me.value?.user?.email ?? "");
const permissions = computed(() => me.value?.permissions || []);
const showNotifications = ref(false);
const isSidebarCollapsed = ref(true);

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
      label: "Продажі",
      to: "/cabinet/participation?type=sales",
      icon: "i-heroicons-banknotes",
    },
    {
      label: "Закупівлі",
      to: "/cabinet/participation?type=purchase",
      icon: "i-heroicons-shopping-cart",
    },
    {
      label: "Журнал участей",
      to: "/cabinet/participation/journal",
      icon: "i-heroicons-clipboard-document-check",
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
      label: "Створити тендер",
      to: "/cabinet/tenders/create/sales",
      icon: "i-heroicons-plus-circle",
    },
    {
      label: "Реєстрація продажів",
      to: "/cabinet/tenders/create/sales?mode=registration",
      icon: "i-heroicons-clipboard-document-check",
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
      label: "Створити тендер",
      to: "/cabinet/tenders/create/purchase",
      icon: "i-heroicons-plus-circle",
    },
    {
      label: "Реєстрація закупівель",
      to: "/cabinet/tenders/create/purchase?mode=registration",
      icon: "i-heroicons-clipboard-document-check",
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
      label: "Статті бюджету",
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

const getNavItemId = (item: any, index: number) =>
  String(item.to || item.label || `item-${index}`);

const isPathActive = (to: string | undefined) => {
  if (!to) return false;
  const target = String(to);
  const [pathOnly, queryString] = target.split("?");
  if (route.path !== pathOnly) return false;
  if (!queryString) return true;

  const search = new URLSearchParams(queryString);
  for (const [key, expected] of search.entries()) {
    const current = route.query[key];
    if (Array.isArray(current)) {
      if (!current.includes(expected)) return false;
    } else if (String(current ?? "") !== expected) {
      return false;
    }
  }
  return true;
};

// Пункти меню для UNavigationMenu з позначкою активного та defaultOpen для розділу з активним дочірнім
const navigationItems = computed(() => {
  return menuLinks.value.map((item: any, index: number) => {
    const id = getNavItemId(item, index);
    const hasChildren = Array.isArray(item.children) && item.children.length;
    const children = hasChildren
      ? item.children.map((child: any) => ({
          ...child,
          active: isPathActive(child.to),
        }))
      : undefined;
    const hasActiveChild = hasChildren && children.some((c: any) => c.active);
    return {
      id,
      ...item,
      ...(children && { children }),
      active: hasChildren ? false : isPathActive(item.to),
      defaultOpen: hasActiveChild,
    };
  });
});

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

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

function openTasksPage() {
  markActiveTasksSeen();
  void navigateTo("/cabinet/tasks");
}

const companyName = computed(
  () =>
    (me.value as { memberships?: Array<{ company?: { name?: string } }> })
      ?.memberships?.[0]?.company?.name ?? "",
);
const pageTitle = computed(
  () => (route.meta.title as string) || companyName.value || "Кабінет",
);

// Notifications (via users useCases)
const usersUC = useUsersUseCases();
const tendersUC = useTendersUseCases();
const notifications = ref<{ id: number; is_read?: boolean }[]>([]);
const activeTasksCount = ref(0);
const seenActiveTasksCount = ref(0);
let activeTasksRefreshTimer: ReturnType<typeof setInterval> | null = null;
const activeTasksSeenStorageKey = computed(
  () => `cabinet.tasks.seen-count:${String(me.value?.user?.id ?? "0")}`,
);
const hasUnseenActiveTasks = computed(
  () =>
    activeTasksCount.value > 0 &&
    activeTasksCount.value > seenActiveTasksCount.value,
);

function readSeenActiveTasksCountFromStorage() {
  if (!import.meta.client) return;
  try {
    const raw = localStorage.getItem(activeTasksSeenStorageKey.value);
    const parsed = Number(raw ?? 0);
    seenActiveTasksCount.value =
      Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
  } catch {
    seenActiveTasksCount.value = 0;
  }
}

function markActiveTasksSeen() {
  seenActiveTasksCount.value = activeTasksCount.value;
  if (!import.meta.client) return;
  try {
    localStorage.setItem(
      activeTasksSeenStorageKey.value,
      String(seenActiveTasksCount.value),
    );
  } catch {}
}

async function loadActiveTasksCount() {
  if (!me.value?.user?.id) {
    activeTasksCount.value = 0;
    return;
  }

  try {
    const [{ data: purchase }, { data: sales }] = await Promise.all([
      tendersUC.getTenderActiveTasksCount(false, { skipLoader: true }),
      tendersUC.getTenderActiveTasksCount(true, { skipLoader: true }),
    ]);
    activeTasksCount.value =
      Number((purchase as { count?: number } | null)?.count ?? 0) +
      Number((sales as { count?: number } | null)?.count ?? 0);
  } catch {
    activeTasksCount.value = 0;
  }
}

onMounted(async () => {
  readSeenActiveTasksCountFromStorage();
  const [{ data }] = await Promise.all([
    usersUC.getNotifications(),
    loadActiveTasksCount(),
  ]);
  notifications.value = data ?? [];
  if (route.path === "/cabinet/tasks") {
    markActiveTasksSeen();
  }

  if (!activeTasksRefreshTimer) {
    activeTasksRefreshTimer = setInterval(() => {
      void loadActiveTasksCount();
    }, 60_000);
  }
});

onBeforeUnmount(() => {
  if (activeTasksRefreshTimer) {
    clearInterval(activeTasksRefreshTimer);
    activeTasksRefreshTimer = null;
  }
});
watch(
  () => me.value?.user?.id,
  () => {
    readSeenActiveTasksCountFromStorage();
  },
);
watch(
  () => route.path,
  (path) => {
    if (path === "/cabinet/tasks") {
      markActiveTasksSeen();
    }
  },
);
const unreadNotificationsCount = computed(
  () => notifications.value?.filter((n) => !n.is_read).length || 0,
);

const formatDate = (date: string) => {
  return new Date(date).toLocaleString("uk-UA");
};
</script>
