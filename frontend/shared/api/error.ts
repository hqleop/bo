const DEFAULT_API_ERROR_MESSAGE = "Request failed";

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;
  return value as Record<string, unknown>;
}

function extractFirstMessage(payload: unknown): string | null {
  if (typeof payload === "string") {
    const normalized = payload.trim();
    return normalized || null;
  }

  if (Array.isArray(payload)) {
    for (const item of payload) {
      const nested = extractFirstMessage(item);
      if (nested) return nested;
    }
    return null;
  }

  const record = asRecord(payload);
  if (!record) return null;

  const priorityKeys = ["detail", "message", "error", "non_field_errors"];
  for (const key of priorityKeys) {
    const nested = extractFirstMessage(record[key]);
    if (nested) return nested;
  }

  for (const value of Object.values(record)) {
    const nested = extractFirstMessage(value);
    if (nested) return nested;
  }

  return null;
}

export function getApiErrorMessage(
  error: unknown,
  fallback = DEFAULT_API_ERROR_MESSAGE,
): string {
  const direct = extractFirstMessage(error);
  if (direct) return direct;

  const record = asRecord(error);
  if (!record) return fallback;

  const fromData = extractFirstMessage(record.data);
  if (fromData) return fromData;

  return fallback;
}
