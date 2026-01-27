"use client";

import { useCallback, useEffect, useState } from "react";
import type { RealtimeChannel } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

type ConnectionStatus = "connected" | "connecting" | "disconnected" | "error";

export function useRealtimeStatus() {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [lastConnected, setLastConnected] = useState<Date | null>(null);
  const [reconnectToken, setReconnectToken] = useState(0);

  useEffect(() => {
    let channel: RealtimeChannel | null = null;

    const handleStatus = (state: string) => {
      switch (state) {
        case "SUBSCRIBED":
          setStatus("connected");
          setLastConnected(new Date());
          break;
        case "TIMED_OUT":
          setStatus("error");
          break;
        case "CHANNEL_ERROR":
          setStatus("error");
          break;
        case "CLOSED":
          setStatus("disconnected");
          break;
        default:
          setStatus("connecting");
      }
    };

    setStatus("connecting");
    channel = supabase.channel("realtime-status");
    channel.subscribe((state) => {
      handleStatus(state);
    });

    return () => {
      if (channel) {
        channel.unsubscribe();
        supabase.removeChannel(channel);
      }
    };
  }, [reconnectToken]);

  const reconnect = useCallback(() => {
    setStatus("connecting");
    supabase.realtime.connect();
    setReconnectToken((value) => value + 1);
  }, []);

  return {
    status,
    lastConnected,
    isConnected: status === "connected",
    reconnect,
  };
}
