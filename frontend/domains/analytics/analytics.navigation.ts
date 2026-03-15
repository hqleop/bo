import type {
  AnalyticsMode,
  AnalyticsTenderType,
} from "./analytics.types";

export type AnalyticsPageKey = "sales" | "purchases";
export type FixedAnalyticsTenderType = Exclude<AnalyticsTenderType, "all">;

type AnalyticsMenuItem = {
  label: string;
  icon?: string;
  to?: string;
  children?: AnalyticsMenuItem[];
};

type AnalyticsSectionDefinition = {
  mode: AnalyticsMode;
  label: string;
  icon: string;
  basePath: string;
};

type AnalyticsPageDefinition = {
  key: AnalyticsPageKey;
  label: string;
  routeSegment: string;
  fixedTenderType: FixedAnalyticsTenderType;
  icon: string;
};

type AnalyticsPageConfig = {
  mode: AnalyticsMode;
  label: string;
  pageTitle: string;
  metaTitle: string;
  to: string;
  fixedTenderType: FixedAnalyticsTenderType;
  tabs: Array<{ label: string; to: string }>;
};

const ANALYTICS_PAGES: AnalyticsPageDefinition[] = [
  {
    key: "sales",
    label: "Продажі",
    routeSegment: "sales",
    fixedTenderType: "sales",
    icon: "i-heroicons-banknotes",
  },
  {
    key: "purchases",
    label: "Закупівлі",
    routeSegment: "purchases",
    fixedTenderType: "purchase",
    icon: "i-heroicons-shopping-cart",
  },
];

const ANALYTICS_SECTIONS: AnalyticsSectionDefinition[] = [
  {
    mode: "personal-organizer",
    label: "Персональна аналітика організатора",
    icon: "i-heroicons-user-circle",
    basePath: "/cabinet/analytics/personal/organizer",
  },
  {
    mode: "personal-participant",
    label: "Персональна аналітика учасника",
    icon: "i-heroicons-user-group",
    basePath: "/cabinet/analytics/personal/participant",
  },
  {
    mode: "summary-tenders",
    label: "Зведена аналітика по проведенню",
    icon: "i-heroicons-chart-bar-square",
    basePath: "/cabinet/analytics/summary/tenders",
  },
  {
    mode: "summary-participation",
    label: "Зведена аналітика по участі",
    icon: "i-heroicons-presentation-chart-line",
    basePath: "/cabinet/analytics/summary/participation",
  },
];

function getSection(mode: AnalyticsMode): AnalyticsSectionDefinition {
  const section = ANALYTICS_SECTIONS.find((item) => item.mode === mode);
  if (!section) {
    throw new Error(`Unknown analytics section: ${mode}`);
  }
  return section;
}

function getPage(page: AnalyticsPageKey): AnalyticsPageDefinition {
  const analyticsPage = ANALYTICS_PAGES.find((item) => item.key === page);
  if (!analyticsPage) {
    throw new Error(`Unknown analytics page: ${page}`);
  }
  return analyticsPage;
}

export function getAnalyticsTabs(mode: AnalyticsMode) {
  const section = getSection(mode);
  return ANALYTICS_PAGES.map((page) => ({
    label: page.label,
    to: `${section.basePath}/${page.routeSegment}`,
  }));
}

export function getAnalyticsPageConfig(
  mode: AnalyticsMode,
  page: AnalyticsPageKey,
): AnalyticsPageConfig {
  const section = getSection(mode);
  const analyticsPage = getPage(page);
  return {
    mode,
    label: analyticsPage.label,
    pageTitle: `${section.label}: ${analyticsPage.label}`,
    metaTitle: `${section.label} - ${analyticsPage.label}`,
    to: `${section.basePath}/${analyticsPage.routeSegment}`,
    fixedTenderType: analyticsPage.fixedTenderType,
    tabs: getAnalyticsTabs(mode),
  };
}

export function getAnalyticsDefaultRoute(mode: AnalyticsMode) {
  return getAnalyticsPageConfig(mode, "sales").to;
}

export function getAnalyticsMenuItems(): AnalyticsMenuItem[] {
  return ANALYTICS_SECTIONS.map((section) => ({
    label: section.label,
    icon: section.icon,
    children: ANALYTICS_PAGES.map((page) => ({
      label: page.label,
      icon: page.icon,
      to: `${section.basePath}/${page.routeSegment}`,
    })),
  }));
}
