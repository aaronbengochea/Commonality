"use client";

import { useEffect, useRef, useCallback } from "react";
import { createWebSocket } from "@/lib/ws";

export function useWebSocket(onMessage: (data: string) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const pendingQueue = useRef<string[]>([]);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const ws = createWebSocket("/api/ws/chat", token);
    wsRef.current = ws;

    ws.onopen = () => {
      // Flush any messages queued while connecting
      for (const msg of pendingQueue.current) {
        ws.send(msg);
      }
      pendingQueue.current = [];
    };

    ws.onmessage = (event) => {
      onMessageRef.current(event.data);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
      wsRef.current = null;
      pendingQueue.current = [];
    };
  }, []);

  const send = useCallback((data: string) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data);
    } else if (ws?.readyState === WebSocket.CONNECTING) {
      pendingQueue.current.push(data);
    }
  }, []);

  return { send };
}
