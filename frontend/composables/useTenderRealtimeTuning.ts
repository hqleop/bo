type UseTenderRealtimeTuningOptions = {
  proposalCount: Readonly<Ref<number>>;
  idleStreak: Readonly<Ref<number>>;
};

function toInt(value: unknown, fallback: number, min = 0) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, parsed);
}

function toNumber(value: unknown, fallback: number, min = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, parsed);
}

function toBoolean(value: unknown, fallback: boolean) {
  if (typeof value === "boolean") return value;
  const raw = String(value ?? "").trim().toLowerCase();
  if (!raw) return fallback;
  return ["1", "true", "yes", "on"].includes(raw);
}

export function useTenderRealtimeTuning(options: UseTenderRealtimeTuningOptions) {
  const config = useRuntimeConfig();
  const runtimePublic = config.public as Record<string, unknown>;

  const chunkSize = toInt(
    runtimePublic.tenderRealtimeChunkSize,
    120,
    1,
  );
  const maxIncrementalIds = toInt(
    runtimePublic.tenderRealtimeMaxIncrementalIds,
    480,
    1,
  );
  const deltaSyncIdsThreshold = toInt(
    runtimePublic.tenderRealtimeDeltaIdsThreshold,
    120,
    1,
  );

  const proposalThresholdMedium = toInt(
    runtimePublic.tenderRealtimeProposalThresholdMedium,
    300,
    1,
  );
  const proposalThresholdLarge = Math.max(
    proposalThresholdMedium + 1,
    toInt(runtimePublic.tenderRealtimeProposalThresholdLarge, 1000, 1),
  );
  const proposalThresholdXLarge = Math.max(
    proposalThresholdLarge + 1,
    toInt(runtimePublic.tenderRealtimeProposalThresholdXLarge, 3000, 1),
  );

  const syncMsSmall = toInt(runtimePublic.tenderRealtimeSyncMsSmall, 30000, 1000);
  const syncMsMedium = Math.max(
    syncMsSmall,
    toInt(runtimePublic.tenderRealtimeSyncMsMedium, 60000, 1000),
  );
  const syncMsLarge = Math.max(
    syncMsMedium,
    toInt(runtimePublic.tenderRealtimeSyncMsLarge, 120000, 1000),
  );
  const syncMsXLarge = Math.max(
    syncMsLarge,
    toInt(runtimePublic.tenderRealtimeSyncMsXLarge, 180000, 1000),
  );

  const idleLevel1Threshold = toInt(
    runtimePublic.tenderRealtimeIdleLevel1Threshold,
    4,
    1,
  );
  const idleLevel2Threshold = Math.max(
    idleLevel1Threshold + 1,
    toInt(runtimePublic.tenderRealtimeIdleLevel2Threshold, 8, 1),
  );
  const idleLevel3Threshold = Math.max(
    idleLevel2Threshold + 1,
    toInt(runtimePublic.tenderRealtimeIdleLevel3Threshold, 12, 1),
  );

  const idleLevel1MinSyncMs = toInt(
    runtimePublic.tenderRealtimeIdleLevel1MinSyncMs,
    90000,
    1000,
  );
  const idleLevel2MinSyncMs = Math.max(
    idleLevel1MinSyncMs,
    toInt(runtimePublic.tenderRealtimeIdleLevel2MinSyncMs, 120000, 1000),
  );
  const idleLevel3MinSyncMs = Math.max(
    idleLevel2MinSyncMs,
    toInt(runtimePublic.tenderRealtimeIdleLevel3MinSyncMs, 180000, 1000),
  );

  const burstPendingSmall = toInt(
    runtimePublic.tenderRealtimeBurstPendingSmall,
    200,
    1,
  );
  const burstPendingMedium = toInt(
    runtimePublic.tenderRealtimeBurstPendingMedium,
    160,
    1,
  );
  const burstPendingLarge = toInt(
    runtimePublic.tenderRealtimeBurstPendingLarge,
    120,
    1,
  );
  const burstPendingXLarge = toInt(
    runtimePublic.tenderRealtimeBurstPendingXLarge,
    80,
    1,
  );

  const burstSyncMultiplier = toNumber(
    runtimePublic.tenderRealtimeBurstSyncMultiplier,
    2,
    1,
  );
  const hiddenMinSyncMs = toInt(
    runtimePublic.tenderRealtimeHiddenMinSyncMs,
    60000,
    1000,
  );
  const hiddenSyncMultiplier = toNumber(
    runtimePublic.tenderRealtimeHiddenSyncMultiplier,
    2,
    1,
  );
  const fallbackWhenWsOfflineMs = toInt(
    runtimePublic.tenderRealtimeOfflineFallbackMs,
    180000,
    1000,
  );
  const pauseSyncWhenHidden = toBoolean(
    runtimePublic.tenderRealtimePauseWhenHidden,
    true,
  );
  const syncJitterRatio = Math.min(
    0.5,
    toNumber(runtimePublic.tenderRealtimeSyncJitterRatio, 0.15, 0),
  );

  const organizerSyncMs = computed(() => {
    const proposalCount = Number(options.proposalCount.value || 0);
    let base = syncMsSmall;
    if (proposalCount >= proposalThresholdXLarge) base = syncMsXLarge;
    else if (proposalCount >= proposalThresholdLarge) base = syncMsLarge;
    else if (proposalCount >= proposalThresholdMedium) base = syncMsMedium;

    const idleStreak = Number(options.idleStreak.value || 0);
    if (idleStreak >= idleLevel3Threshold) return Math.max(base, idleLevel3MinSyncMs);
    if (idleStreak >= idleLevel2Threshold) return Math.max(base, idleLevel2MinSyncMs);
    if (idleStreak >= idleLevel1Threshold) return Math.max(base, idleLevel1MinSyncMs);
    return base;
  });

  const organizerBurstSyncMs = computed(() =>
    Math.max(
      hiddenMinSyncMs,
      Math.round(organizerSyncMs.value * burstSyncMultiplier),
    ),
  );

  const organizerBurstPendingThreshold = computed(() => {
    const proposalCount = Number(options.proposalCount.value || 0);
    if (proposalCount >= proposalThresholdXLarge) return burstPendingXLarge;
    if (proposalCount >= proposalThresholdLarge) return burstPendingLarge;
    if (proposalCount >= proposalThresholdMedium) return burstPendingMedium;
    return burstPendingSmall;
  });

  const hiddenSyncMs = computed(() =>
    Math.max(
      hiddenMinSyncMs,
      Math.round(organizerSyncMs.value * hiddenSyncMultiplier),
    ),
  );

  return {
    chunkSize,
    maxIncrementalIds,
    deltaSyncIdsThreshold,
    organizerSyncMs,
    organizerBurstSyncMs,
    organizerBurstPendingThreshold,
    hiddenSyncMs,
    fallbackWhenWsOfflineMs,
    pauseSyncWhenHidden,
    syncJitterRatio,
  };
}
