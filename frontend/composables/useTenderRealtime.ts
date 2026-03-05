type TenderRealtimeKind = "procurement" | "sales";

type TenderRealtimeEvent = {
  event?: string;
  payload?: Record<string, unknown>;
  sent_at?: string;
};

type ConnectOptions = {
  kind: TenderRealtimeKind;
  tenderId: number;
  onEvent?: (message: TenderRealtimeEvent) => void;
};

export const useTenderRealtime = () => {
  const { accessToken } = useAuth();
  const config = useRuntimeConfig();

  const socket = ref<WebSocket | null>(null);
  const isConnected = ref(false);
  const reconnectAttempt = ref(0);

  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let shouldReconnect = false;
  let currentConnect: ConnectOptions | null = null;

  const getWsBase = () => {
    const apiBase = String(config.public.apiBase || "");
    const apiRoot = apiBase.replace(/\/api\/?$/, "");
    return apiRoot.replace(/^http/i, "ws");
  };

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const buildUrl = (opts: ConnectOptions) => {
    return `${getWsBase()}/ws/tenders/${opts.kind}/${opts.tenderId}/`;
  };

  const closeSocket = () => {
    if (socket.value) {
      socket.value.onopen = null;
      socket.value.onclose = null;
      socket.value.onerror = null;
      socket.value.onmessage = null;
      socket.value.close();
      socket.value = null;
    }
    isConnected.value = false;
  };

  const connect = (opts: ConnectOptions) => {
    if (!import.meta.client) return;
    currentConnect = opts;
    shouldReconnect = true;
    clearReconnectTimer();
    closeSocket();
    if (!accessToken.value) return;

    const ws = new WebSocket(buildUrl(opts));
    socket.value = ws;

    ws.onopen = () => {
      reconnectAttempt.value = 0;
      isConnected.value = true;
    };

    ws.onmessage = (event) => {
      if (!opts.onEvent) return;
      try {
        const parsed = JSON.parse(String(event.data)) as TenderRealtimeEvent;
        opts.onEvent(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      isConnected.value = false;
    };

    ws.onclose = () => {
      isConnected.value = false;
      socket.value = null;
      if (!shouldReconnect || !currentConnect) return;
      const delay = Math.min(10000, 500 * 2 ** reconnectAttempt.value);
      reconnectAttempt.value += 1;
      reconnectTimer = setTimeout(() => connect(currentConnect), delay);
    };
  };

  const disconnect = () => {
    shouldReconnect = false;
    clearReconnectTimer();
    closeSocket();
  };

  return {
    connect,
    disconnect,
    isConnected: readonly(isConnected),
  };
};
