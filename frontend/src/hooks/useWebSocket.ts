"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import type { ClusterEvent, ClusterTopology } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/monitor";

export function useClusterWebSocket() {
  const [events, setEvents]     = useState<ClusterEvent[]>([]);
  const [topology, setTopology] = useState<ClusterTopology | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef   = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (e) => {
      try {
        const msg: ClusterEvent = JSON.parse(e.data as string);
        if (msg.event === "connected" || msg.event === "heartbeat") {
          setTopology(msg.data as unknown as ClusterTopology);
        }
        setEvents((prev) => [msg, ...prev].slice(0, 100));
      } catch {/* ignore parse errors */}
    };

    ws.onerror  = () => setConnected(false);

    ws.onclose  = () => {
      setConnected(false);
      retryRef.current = setTimeout(connect, 3000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [connect]);

  const clearEvents = () => setEvents([]);

  return { events, topology, connected, clearEvents };
}
