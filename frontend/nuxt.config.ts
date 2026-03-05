// https://nuxt.com/docs/api/configuration/nuxt-config
function intEnv(name: string, fallback: number) {
  const raw = process.env[name];
  const parsed = Number.parseInt(String(raw ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return parsed;
}

function numEnv(name: string, fallback: number) {
  const raw = process.env[name];
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return parsed;
}

function boolEnv(name: string, fallback: boolean) {
  const raw = String(process.env[name] ?? "").trim().toLowerCase();
  if (!raw) return fallback;
  return ["1", "true", "yes", "on"].includes(raw);
}

export default defineNuxtConfig({
  compatibilityDate: "2024-04-03",
  devtools: { enabled: true },
  modules: ["@nuxt/ui"],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000/api",
      tenderRealtimeChunkSize: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_CHUNK_SIZE",
        120,
      ),
      tenderRealtimeMaxIncrementalIds: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_MAX_INCREMENTAL_IDS",
        480,
      ),
      tenderRealtimeDeltaIdsThreshold: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_DELTA_IDS_THRESHOLD",
        120,
      ),
      tenderRealtimeProposalThresholdMedium: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_PROPOSAL_THRESHOLD_MEDIUM",
        300,
      ),
      tenderRealtimeProposalThresholdLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_PROPOSAL_THRESHOLD_LARGE",
        1000,
      ),
      tenderRealtimeProposalThresholdXLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_PROPOSAL_THRESHOLD_XLARGE",
        3000,
      ),
      tenderRealtimeSyncMsSmall: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_SYNC_MS_SMALL",
        30000,
      ),
      tenderRealtimeSyncMsMedium: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_SYNC_MS_MEDIUM",
        60000,
      ),
      tenderRealtimeSyncMsLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_SYNC_MS_LARGE",
        120000,
      ),
      tenderRealtimeSyncMsXLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_SYNC_MS_XLARGE",
        180000,
      ),
      tenderRealtimeIdleLevel1Threshold: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L1_THRESHOLD",
        4,
      ),
      tenderRealtimeIdleLevel2Threshold: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L2_THRESHOLD",
        8,
      ),
      tenderRealtimeIdleLevel3Threshold: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L3_THRESHOLD",
        12,
      ),
      tenderRealtimeIdleLevel1MinSyncMs: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L1_MIN_SYNC_MS",
        90000,
      ),
      tenderRealtimeIdleLevel2MinSyncMs: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L2_MIN_SYNC_MS",
        120000,
      ),
      tenderRealtimeIdleLevel3MinSyncMs: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_IDLE_L3_MIN_SYNC_MS",
        180000,
      ),
      tenderRealtimeBurstPendingSmall: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_BURST_PENDING_SMALL",
        200,
      ),
      tenderRealtimeBurstPendingMedium: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_BURST_PENDING_MEDIUM",
        160,
      ),
      tenderRealtimeBurstPendingLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_BURST_PENDING_LARGE",
        120,
      ),
      tenderRealtimeBurstPendingXLarge: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_BURST_PENDING_XLARGE",
        80,
      ),
      tenderRealtimeBurstSyncMultiplier: numEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_BURST_SYNC_MULTIPLIER",
        2,
      ),
      tenderRealtimeHiddenMinSyncMs: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_HIDDEN_MIN_SYNC_MS",
        60000,
      ),
      tenderRealtimeHiddenSyncMultiplier: numEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_HIDDEN_SYNC_MULTIPLIER",
        2,
      ),
      tenderRealtimeOfflineFallbackMs: intEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_OFFLINE_FALLBACK_MS",
        180000,
      ),
      tenderRealtimePauseWhenHidden: boolEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_PAUSE_WHEN_HIDDEN",
        true,
      ),
      tenderRealtimeSyncJitterRatio: numEnv(
        "NUXT_PUBLIC_TENDER_REALTIME_SYNC_JITTER_RATIO",
        0.15,
      ),
    },
  },
  css: ["~/assets/css/main.css"],
  // Вимикаємо SSR для кабінету — уникаємо hydration mismatch (різний стан auth/даних на сервері та клієнті)
  routeRules: {
    "/cabinet/**": { ssr: false },
  },
  app: {
    head: {
      htmlAttrs: {
        lang: "uk",
      },
      meta: [{ charset: "utf-8" }],
    },
  },
});
