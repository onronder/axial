import type { QueryClient } from "@tanstack/react-query";

const SYNC_CHANNEL = "axial-query-sync";

type SyncMessage =
  | {
      type: "invalidate";
      queryKey: unknown[];
      sourceId: string;
      timestamp: number;
    }
  | {
      type: "update";
      queryKey: unknown[];
      data: unknown;
      sourceId: string;
      timestamp: number;
    };

const createTabId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const stableKey = (key: unknown[]): string | null => {
  try {
    return JSON.stringify(key);
  } catch {
    return null;
  }
};

export function setupCrossTabSync(queryClient: QueryClient) {
  if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") {
    return () => {};
  }

  const tabId = createTabId();
  const channel = new BroadcastChannel(SYNC_CHANNEL);
  const suppressed = new Set<string>();

  channel.onmessage = (event: MessageEvent<SyncMessage>) => {
    const message = event.data;
    if (!message || message.sourceId === tabId) return;

    const keyHash = stableKey(message.queryKey);
    if (keyHash) {
      suppressed.add(keyHash);
    }

    if (message.type === "invalidate") {
      queryClient.invalidateQueries({ queryKey: message.queryKey });
    } else if (message.type === "update") {
      queryClient.setQueryData(message.queryKey, message.data);
    }

    if (keyHash) {
      queueMicrotask(() => suppressed.delete(keyHash));
    }
  };

  const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
    if (event.type !== "updated") return;

    const query = event.query;
    const keyHash = stableKey(query.queryKey);
    if (!keyHash || suppressed.has(keyHash)) return;

    if (query.state.isInvalidated) {
      channel.postMessage({
        type: "invalidate",
        queryKey: query.queryKey,
        sourceId: tabId,
        timestamp: Date.now(),
      } satisfies SyncMessage);
      return;
    }

    if (query.state.status === "success" && query.state.data !== undefined) {
      channel.postMessage({
        type: "update",
        queryKey: query.queryKey,
        data: query.state.data,
        sourceId: tabId,
        timestamp: Date.now(),
      } satisfies SyncMessage);
    }
  });

  return () => {
    unsubscribe();
    channel.close();
  };
}
