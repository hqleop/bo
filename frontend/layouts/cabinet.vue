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
        <header
          class="h-14 flex-shrink-0 bg-white shadow-sm border-b border-gray-200"
        >
          <div class="px-4 py-2 flex justify-between items-center h-full">
            <h1 class="text-lg font-semibold text-gray-900">{{ pageTitle }}</h1>
            <div class="flex items-center gap-3">
              <UButton
                icon="i-heroicons-clipboard-document-list"
                variant="ghost"
                color="neutral"
                size="sm"
                :chip="hasUnseenActiveTasks ? { inset: true } : undefined"
                title="Завдання користувача"
                @click="openTasksPage"
              >
                {{ `Завдання (${activeTasksCount})` }}
              </UButton>
              <UButton
                icon="i-heroicons-bell"
                variant="ghost"
                color="neutral"
                size="sm"
                :badge="
                  unreadNotificationsCount > 0
                    ? unreadNotificationsCount
                    : undefined
                "
                @click="showNotifications = !showNotifications"
              >
                {{ `Сповіщення (${unreadNotificationsCount})` }}
              </UButton>
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
          <div
            v-else
            class="space-y-2"
            :class="
              notifications.length > 3 ? 'max-h-[26rem] overflow-y-auto pr-1' : ''
            "
          >
            <div
              v-for="notification in notifications"
              :key="notification.id"
              class="rounded-lg border border-gray-200 p-3"
              :class="{ 'bg-gray-50': notification.is_read }"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <p class="text-xs text-gray-400">
                    {{ formatDate(notification.created_at) }}
                  </p>
                  <h4 class="mt-1 font-semibold text-gray-900">
                    {{ notification.title || "Сповіщення" }}
                  </h4>
                  <p
                    v-if="notification.meta?.event"
                    class="mt-1 text-sm text-gray-700"
                  >
                    Подія: {{ getNotificationEventLabel(notification) }}
                  </p>
                  <p
                    v-if="notification.body"
                    class="mt-1 text-sm text-gray-600 overflow-hidden"
                    style="
                      display: -webkit-box;
                      -webkit-box-orient: vertical;
                      -webkit-line-clamp: 2;
                    "
                  >
                    {{ notification.body }}
                  </p>
                  <NuxtLink
                    v-if="getNotificationDocumentUrl(notification)"
                    :to="getNotificationDocumentUrl(notification)!"
                    class="mt-2 inline-flex text-sm font-medium text-primary-600 hover:text-primary-700 underline underline-offset-2"
                    @click="showNotifications = false"
                  >
                    {{ getNotificationDocumentName(notification) }}
                  </NuxtLink>
                  <p
                    v-else-if="getNotificationDocumentName(notification)"
                    class="mt-2 text-sm font-medium text-gray-700"
                  >
                    {{ getNotificationDocumentName(notification) }}
                  </p>
                </div>
                <UButton
                  icon="i-heroicons-trash"
                  variant="ghost"
                  color="neutral"
                  size="sm"
                  title="Видалити сповіщення"
                  @click="removeNotification(notification.id)"
                />
              </div>
            </div>
          </div>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { getAnalyticsMenuItems } from "~/domains/analytics/analytics.navigation";
import { resolveRegistrationStep } from "~/shared/registrationFlow";

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
    const registrationStep = resolveRegistrationStep(mePayload as any);
    if (registrationStep < 4) {
      await navigateTo(
        `/register?step=${Math.min(Math.max(registrationStep, 1), 3)}`,
      );
    } else {
      const hasMemberships =
        Array.isArray(mePayload?.memberships) &&
        mePayload.memberships.length > 0;
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
  links.push({
    label: "Аналітика",
    icon: "i-heroicons-chart-bar",
    children: getAnalyticsMenuItems(),
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
  const suppliersChildren: any[] = [
    {
      label: "Журнал контрагентів",
      to: "/cabinet/suppliers",
      icon: "i-heroicons-document-text",
    },
  ];
  links.push({
    label: "Контрагенти",
    icon: "i-heroicons-building-office",
    children: suppliersChildren,
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
    {
      label: "Шаблони умов",
      to: "/cabinet/templates",
      icon: "i-heroicons-document-duplicate",
    },
  );
  referenceChildren.splice(4, 0, {
    label: "Склади",
    to: "/cabinet/reference/warehouses",
    icon: "i-heroicons-building-library",
  });
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

const getNavItemId = (item: any, index: number, parentId = "root") =>
  String(item.to || `${parentId}:${item.label || `item-${index}`}`);

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
function buildNavigationItems(items: any[], parentId = "root"): any[] {
  return items.map((item: any, index: number) => {
    const id = getNavItemId(item, index, parentId);
    const children =
      Array.isArray(item.children) && item.children.length
        ? buildNavigationItems(item.children, id)
        : undefined;
    const selfActive = isPathActive(item.to);
    const hasActiveChild = Boolean(
      children?.some((child: any) => child.active || child.defaultOpen),
    );
    return {
      id,
      ...item,
      ...(children ? { children } : {}),
      active: selfActive,
      defaultOpen: hasActiveChild,
    };
  });
}

const navigationItems = computed(() => buildNavigationItems(menuLinks.value));

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
type CabinetNotification = {
  id: number;
  type?: string;
  title?: string;
  body?: string;
  is_read?: boolean;
  created_at?: string;
  meta?: Record<string, any> | null;
};
const notifications = ref<CabinetNotification[]>([]);
const activeTasksCount = ref(0);
const seenActiveTasksCount = ref(0);
let activeTasksRefreshTimer: ReturnType<typeof setInterval> | null = null;
let notificationsRefreshTimer: ReturnType<typeof setInterval> | null = null;
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

async function loadNotifications() {
  try {
    const { data } = await usersUC.getNotifications({
      skipLoader: true,
      cacheTtlMs: 15_000,
    });
    notifications.value = Array.isArray(data) ? data : [];
  } catch {
    notifications.value = [];
  }
}

async function removeNotification(notificationId: number) {
  const { error } = await usersUC.removeNotification(notificationId);
  if (error) return;
  notifications.value = notifications.value.filter(
    (notification) => notification.id !== notificationId,
  );
}

onMounted(async () => {
  readSeenActiveTasksCountFromStorage();
  await Promise.all([loadNotifications(), loadActiveTasksCount()]);
  if (route.path === "/cabinet/tasks") {
    markActiveTasksSeen();
  }

  if (!activeTasksRefreshTimer) {
    activeTasksRefreshTimer = setInterval(() => {
      void loadActiveTasksCount();
    }, 60_000);
  }
  if (!notificationsRefreshTimer) {
    notificationsRefreshTimer = setInterval(() => {
      void loadNotifications();
    }, 60_000);
  }
});

onBeforeUnmount(() => {
  if (activeTasksRefreshTimer) {
    clearInterval(activeTasksRefreshTimer);
    activeTasksRefreshTimer = null;
  }
  if (notificationsRefreshTimer) {
    clearInterval(notificationsRefreshTimer);
    notificationsRefreshTimer = null;
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
watch(
  () => showNotifications.value,
  (isOpen) => {
    if (isOpen) {
      void loadNotifications();
    }
  },
);
const unreadNotificationsCount = computed(
  () => notifications.value?.filter((n) => !n.is_read).length || 0,
);

const formatDate = (date: string) => {
  return new Date(date).toLocaleString("uk-UA");
};
const getNotificationDocumentName = (notification: CabinetNotification) =>
  String(notification.meta?.document_name || "").trim();
const getNotificationDocumentUrl = (notification: CabinetNotification) => {
  const value = String(notification.meta?.document_url || "").trim();
  return value || null;
};
const getNotificationEventLabel = (notification: CabinetNotification) => {
  const event = String(
    notification.meta?.event || notification.type || "",
  ).trim();
  const labels: Record<string, string> = {
    chat_message: "Нове повідомлення в чаті",
    tender_to_decision: "Тендер перейшов на етап вибору рішення",
    tender_completed: "Тендер перейшов на етап завершення",
  };
  return labels[event] || notification.title || "Подія системи";
};
</script>
