type UseTenderProposalsRealtimeOptions = {
  tenderId: Readonly<Ref<number>>;
  isSales: boolean;
  tenderStage: Readonly<Ref<string | null | undefined>>;
  isOnlineAuction: Readonly<Ref<boolean>>;
  isParticipant: Readonly<Ref<boolean>>;
  reload: (changedProposalIds: number[]) => Promise<void>;
  eventNames?: readonly string[];
  onEvent?: (message: RealtimeMessage) => boolean | void;
  participantMinSyncMs?: number | Readonly<Ref<number>>;
  organizerMinSyncMs?: number | Readonly<Ref<number>>;
  organizerBurstMinSyncMs?: number | Readonly<Ref<number>>;
  burstPendingProposalIdsThreshold?: number | Readonly<Ref<number>>;
  hiddenTabMinSyncMs?: number | Readonly<Ref<number>>;
  fallbackWhenWsOfflineMs?: number;
  maxProposalIdsPerSync?: number | Readonly<Ref<number>>;
  pauseSyncWhenHidden?: boolean | Readonly<Ref<boolean>>;
  syncJitterRatio?: number | Readonly<Ref<number>>;
};

type RealtimeMessage = {
  event?: string;
  payload?: Record<string, unknown>;
};

const RELOAD_DEBOUNCE_MS = 250;
const DEFAULT_PARTICIPANT_MIN_SYNC_MS = 1500;
const DEFAULT_ORGANIZER_MIN_SYNC_MS = 4000;
const DEFAULT_ORGANIZER_BURST_MIN_SYNC_MS = 12000;
const DEFAULT_BURST_PENDING_PROPOSAL_IDS_THRESHOLD = 200;
const DEFAULT_HIDDEN_TAB_MIN_SYNC_MS = 10000;
const DEFAULT_FALLBACK_WHEN_WS_OFFLINE_MS = 45000;

export function useTenderProposalsRealtime(
  options: UseTenderProposalsRealtimeOptions,
) {
  const tenderRealtime = useTenderRealtime();

  let syncTimer: ReturnType<typeof setTimeout> | null = null;
  let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
  let activeSessionKey: string | null = null;
  let hasVisibilityListener = false;
  let syncInFlight = false;
  let hasPendingSync = false;
  let needsRerun = false;
  let lastSyncAt = 0;
  const pendingProposalIds = new Set<number>();

  const clearSyncTimer = () => {
    if (!syncTimer) return;
    clearTimeout(syncTimer);
    syncTimer = null;
  };

  const clearFallbackTimer = () => {
    if (!fallbackTimer) return;
    clearTimeout(fallbackTimer);
    fallbackTimer = null;
  };

  const resolveBool = (
    value: boolean | Readonly<Ref<boolean>> | undefined,
    fallback: boolean,
  ) => {
    if (typeof value === "boolean") return value;
    const fromRef = (value as Readonly<Ref<boolean>> | undefined)?.value;
    if (typeof fromRef === "boolean") return fromRef;
    return fallback;
  };

  const resolveSyncMs = (
    value: number | Readonly<Ref<number>> | undefined,
    fallback: number,
  ) => {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.max(0, value);
    }
    const fromRef = Number((value as Readonly<Ref<number>> | undefined)?.value);
    if (Number.isFinite(fromRef)) return Math.max(0, fromRef);
    return fallback;
  };

  const resolveMaxProposalIdsPerSync = () => {
    const raw = options.maxProposalIdsPerSync;
    if (typeof raw === "number" && Number.isFinite(raw)) {
      return Math.max(0, Math.floor(raw));
    }
    const fromRef = Number((raw as Readonly<Ref<number>> | undefined)?.value);
    if (Number.isFinite(fromRef)) return Math.max(0, Math.floor(fromRef));
    return 0;
  };

  const resolveInt = (
    value: number | Readonly<Ref<number>> | undefined,
    fallback: number,
  ) => {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Math.max(0, Math.floor(value));
    }
    const fromRef = Number((value as Readonly<Ref<number>> | undefined)?.value);
    if (Number.isFinite(fromRef)) return Math.max(0, Math.floor(fromRef));
    return fallback;
  };

  const resolveJitterRatio = () => {
    const raw = options.syncJitterRatio;
    if (typeof raw === "number" && Number.isFinite(raw)) {
      return Math.max(0, Math.min(0.5, raw));
    }
    const fromRef = Number((raw as Readonly<Ref<number>> | undefined)?.value);
    if (Number.isFinite(fromRef)) {
      return Math.max(0, Math.min(0.5, fromRef));
    }
    return 0;
  };

  const withJitter = (delayMs: number) => {
    const baseDelay = Math.max(0, Math.round(delayMs));
    const ratio = resolveJitterRatio();
    if (!baseDelay || ratio <= 0) return baseDelay;
    const spread = Math.round(baseDelay * ratio);
    if (spread <= 0) return baseDelay;
    return baseDelay + Math.floor(Math.random() * (spread + 1));
  };

  const isHiddenSyncPaused = () =>
    import.meta.client &&
    document.visibilityState === "hidden" &&
    resolveBool(options.pauseSyncWhenHidden, false);

  const getMinSyncGapMs = () => {
    const participantMinSyncMs = resolveSyncMs(
      options.participantMinSyncMs,
      DEFAULT_PARTICIPANT_MIN_SYNC_MS,
    );
    const organizerMinSyncMs = resolveSyncMs(
      options.organizerMinSyncMs,
      DEFAULT_ORGANIZER_MIN_SYNC_MS,
    );
    const organizerBurstMinSyncMs = resolveSyncMs(
      options.organizerBurstMinSyncMs,
      DEFAULT_ORGANIZER_BURST_MIN_SYNC_MS,
    );
    const burstPendingProposalIdsThreshold = resolveInt(
      options.burstPendingProposalIdsThreshold,
      DEFAULT_BURST_PENDING_PROPOSAL_IDS_THRESHOLD,
    );
    const hiddenTabMinSyncMs = resolveSyncMs(
      options.hiddenTabMinSyncMs,
      DEFAULT_HIDDEN_TAB_MIN_SYNC_MS,
    );

    if (import.meta.client && document.visibilityState === "hidden") {
      return hiddenTabMinSyncMs;
    }
    if (options.isParticipant.value) return participantMinSyncMs;
    if (
      burstPendingProposalIdsThreshold > 0 &&
      pendingProposalIds.size >= burstPendingProposalIdsThreshold
    ) {
      return Math.max(organizerMinSyncMs, organizerBurstMinSyncMs);
    }
    return organizerMinSyncMs;
  };

  const syncNow = async () => {
    clearSyncTimer();
    if (!hasPendingSync) return;
    if (isHiddenSyncPaused()) return;
    if (syncInFlight) {
      needsRerun = true;
      return;
    }

    const now = Date.now();
    const minGap = getMinSyncGapMs();
    const nextAllowedAt = lastSyncAt + minGap;
    if (nextAllowedAt > now) {
      syncTimer = setTimeout(() => {
        void syncNow();
      }, withJitter(nextAllowedAt - now));
      return;
    }

    const maxProposalIdsPerSync = resolveMaxProposalIdsPerSync();
    let changedProposalIds = Array.from(pendingProposalIds);
    if (
      maxProposalIdsPerSync > 0 &&
      changedProposalIds.length > maxProposalIdsPerSync
    ) {
      changedProposalIds = changedProposalIds.slice(0, maxProposalIdsPerSync);
      for (const proposalId of changedProposalIds) {
        pendingProposalIds.delete(proposalId);
      }
      hasPendingSync = pendingProposalIds.size > 0;
    } else {
      pendingProposalIds.clear();
      hasPendingSync = false;
    }
    syncInFlight = true;
    try {
      await options.reload(changedProposalIds);
      lastSyncAt = Date.now();
    } finally {
      syncInFlight = false;
      if (needsRerun || hasPendingSync) {
        needsRerun = false;
        syncTimer = setTimeout(() => {
          void syncNow();
        }, withJitter(RELOAD_DEBOUNCE_MS));
      }
    }
  };

  const queueSync = (proposalId?: number | null) => {
    const normalizedProposalId = Number(proposalId);
    if (Number.isInteger(normalizedProposalId) && normalizedProposalId > 0) {
      pendingProposalIds.add(normalizedProposalId);
    }
    hasPendingSync = true;
    if (syncTimer) return;
    if (isHiddenSyncPaused()) return;
    syncTimer = setTimeout(() => {
      void syncNow();
    }, withJitter(RELOAD_DEBOUNCE_MS));
  };

  const queueSyncMany = (proposalIds: readonly number[]) => {
    for (const proposalId of proposalIds) {
      const normalizedProposalId = Number(proposalId);
      if (Number.isInteger(normalizedProposalId) && normalizedProposalId > 0) {
        pendingProposalIds.add(normalizedProposalId);
      }
    }
    hasPendingSync = true;
    if (syncTimer || isHiddenSyncPaused()) return;
    syncTimer = setTimeout(() => {
      void syncNow();
    }, withJitter(RELOAD_DEBOUNCE_MS));
  };

  const shouldBeActive = () =>
    options.tenderStage.value === "acceptance" && options.isOnlineAuction.value;

  const handleVisibilityChange = () => {
    if (!import.meta.client) return;
    if (document.visibilityState === "hidden") {
      if (isHiddenSyncPaused()) clearSyncTimer();
      return;
    }
    if (!hasPendingSync || syncTimer) return;
    syncTimer = setTimeout(() => {
      void syncNow();
    }, withJitter(RELOAD_DEBOUNCE_MS));
  };

  const attachVisibilityListener = () => {
    if (!import.meta.client || hasVisibilityListener) return;
    document.addEventListener("visibilitychange", handleVisibilityChange);
    hasVisibilityListener = true;
  };

  const detachVisibilityListener = () => {
    if (!import.meta.client || !hasVisibilityListener) return;
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    hasVisibilityListener = false;
  };

  const scheduleFallbackSync = () => {
    clearFallbackTimer();
    const fallbackWhenWsOfflineMs =
      options.fallbackWhenWsOfflineMs ?? DEFAULT_FALLBACK_WHEN_WS_OFFLINE_MS;
    fallbackTimer = setTimeout(() => {
      if (!tenderRealtime.isConnected.value && !isHiddenSyncPaused()) {
        queueSync();
      }
      scheduleFallbackSync();
    }, withJitter(fallbackWhenWsOfflineMs));
  };

  const stop = () => {
    activeSessionKey = null;
    hasPendingSync = false;
    needsRerun = false;
    pendingProposalIds.clear();
    clearSyncTimer();
    clearFallbackTimer();
    detachVisibilityListener();
    tenderRealtime.disconnect();
  };

  const start = () => {
    if (!import.meta.client) return;
    attachVisibilityListener();
    if (!shouldBeActive()) {
      stop();
      return;
    }

    const tenderId = Number(options.tenderId.value);
    if (!Number.isInteger(tenderId) || tenderId <= 0) return;

    const kind = options.isSales ? "sales" : "procurement";
    const sessionKey = `${kind}:${tenderId}`;
    if (activeSessionKey !== sessionKey) {
      activeSessionKey = sessionKey;
      tenderRealtime.connect({
        kind,
        tenderId,
        onEvent: (message: RealtimeMessage) => {
          const eventName = String(message?.event || "");
          if (!eventName.startsWith("proposal.")) return;
          const allowedEvents = options.eventNames;
          if (
            Array.isArray(allowedEvents) &&
            allowedEvents.length > 0 &&
            !allowedEvents.includes(eventName)
          ) {
            return;
          }
          const handledLocally = options.onEvent?.(message);
          if (handledLocally === true) return;
          const proposalIds = Array.isArray(message?.payload?.proposal_ids)
            ? message.payload.proposal_ids
                .map((proposalId) => Number(proposalId))
                .filter(
                  (proposalId): proposalId is number =>
                    Number.isInteger(proposalId) && proposalId > 0,
                )
            : [];
          if (proposalIds.length > 0) {
            queueSyncMany(proposalIds);
            return;
          }
          const proposalId = Number(message?.payload?.proposal_id);
          queueSync(proposalId);
        },
      });
    }

    scheduleFallbackSync();
  };

  return {
    start,
    stop,
    queueSync,
  };
}
