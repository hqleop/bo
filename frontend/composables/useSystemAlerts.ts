export type SystemAlertColor = "error" | "warning" | "success" | "info" | "neutral";

export type SystemAlertItem = {
  id: number;
  title: string;
  color: SystemAlertColor;
  timeoutMs?: number;
};

const inferColorByMessage = (message: string): SystemAlertColor => {
  const text = message.toLowerCase();
  if (text.includes("помил") || text.includes("error") || text.includes("failed")) {
    return "error";
  }
  if (
    text.includes("успіш") ||
    text.includes("завершено") ||
    text.includes("saved") ||
    text.includes("success")
  ) {
    return "success";
  }
  if (text.includes("уваг") || text.includes("warning")) {
    return "warning";
  }
  return "info";
};

export const useSystemAlerts = () => {
  const alerts = useState<SystemAlertItem[]>("system-alerts", () => []);
  const nextId = useState<number>("system-alert-next-id", () => 1);

  const remove = (id: number) => {
    alerts.value = alerts.value.filter((item) => item.id !== id);
  };

  const push = (
    title: string,
    options?: { color?: SystemAlertColor; timeoutMs?: number },
  ) => {
    const id = nextId.value++;
    const color = options?.color ?? inferColorByMessage(title);
    const timeoutMs = options?.timeoutMs ?? 5000;
    alerts.value = [...alerts.value, { id, title, color, timeoutMs }];

    if (timeoutMs > 0 && import.meta.client) {
      window.setTimeout(() => remove(id), timeoutMs);
    }

    return id;
  };

  const pushFromLegacyAlert = (message: unknown) => {
    const title =
      typeof message === "string" ? message : String(message ?? "Повідомлення");
    push(title);
  };

  return {
    alerts,
    push,
    remove,
    pushFromLegacyAlert,
  };
};
