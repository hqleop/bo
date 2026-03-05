export type CriterionInputKind = "text" | "number" | "date" | "file" | "boolean";
export type CriterionValue = string | number | boolean | string[] | null;

type CriterionLike = {
  type?: unknown;
} | null | undefined;

export function criterionInputKind(criterion: CriterionLike): CriterionInputKind {
  const typeValue = String(criterion?.type || "").toLowerCase();
  if (typeValue === "numeric" || typeValue === "number") return "number";
  if (typeValue === "date") return "date";
  if (typeValue === "boolean") return "boolean";
  if (typeValue === "file") return "file";
  return "text";
}

export function normalizeCriterionBoolean(value: unknown): boolean | null {
  if (value === true || value === false) return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "1", "yes", "y", "\u0442\u0430\u043a", "t"].includes(normalized)) {
      return true;
    }
    if (["false", "0", "no", "n", "\u043d\u0456", "ni", "f"].includes(normalized)) {
      return false;
    }
  }
  if (typeof value === "number") {
    if (value === 1) return true;
    if (value === 0) return false;
  }
  return null;
}

export function normalizeCriterionValueForUi(
  criterion: CriterionLike,
  rawValue: unknown,
): CriterionValue | "" {
  const kind = criterionInputKind(criterion);
  if (kind === "number") {
    if (rawValue == null || rawValue === "") return "";
    const numberValue = Number(rawValue);
    return Number.isNaN(numberValue) ? "" : numberValue;
  }
  if (kind === "boolean") return normalizeCriterionBoolean(rawValue) ?? "";
  if (kind === "date") return String(rawValue ?? "").trim();
  if (kind === "file") {
    if (Array.isArray(rawValue)) {
      return rawValue.map((item) => String(item || "").trim()).filter(Boolean);
    }
    if (typeof rawValue === "string") {
      const cleaned = rawValue.trim();
      return cleaned ? [cleaned] : [];
    }
    return [];
  }
  return String(rawValue ?? "");
}

export function normalizeCriterionValueForSave(
  criterion: CriterionLike,
  rawValue: unknown,
): string | number | boolean | string[] | null {
  const kind = criterionInputKind(criterion);
  if (kind === "number") {
    if (rawValue == null || rawValue === "") return null;
    const numberValue = Number(rawValue);
    return Number.isNaN(numberValue) ? null : numberValue;
  }
  if (kind === "boolean") return normalizeCriterionBoolean(rawValue);
  if (kind === "date") {
    const text = String(rawValue ?? "").trim();
    return text !== "" ? text : null;
  }
  if (kind === "file") {
    if (Array.isArray(rawValue)) {
      const names = rawValue.map((item) => String(item || "").trim()).filter(Boolean);
      return names.length ? names : null;
    }
    if (typeof rawValue === "string") {
      const cleaned = rawValue.trim();
      return cleaned ? [cleaned] : null;
    }
    return null;
  }
  const text = String(rawValue ?? "");
  return text.trim() !== "" ? text : null;
}

export function formatCriterionValue(criterion: CriterionLike, value: unknown): string {
  if (value == null || value === "") return "";
  const kind = criterionInputKind(criterion);
  if (kind === "boolean") {
    const boolValue = normalizeCriterionBoolean(value);
    if (boolValue === null) return "";
    return boolValue ? "\u0422\u0430\u043a" : "\u041d\u0456";
  }
  if (kind === "file" && Array.isArray(value)) {
    return value
      .map((item) => String(item || "").trim())
      .filter(Boolean)
      .join(", ");
  }
  return String(value);
}

export function fileModelKey(positionId: number | "g", criterionId: number): string {
  return `${positionId}:${criterionId}`;
}

export function extractFilesArray(value: unknown): File[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter((item): item is File => item instanceof File);
  if (value instanceof File) return [value];
  return [];
}

export function toValidNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

export function formatPriceValue(value: number): string {
  return value.toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
