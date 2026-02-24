"use client";

import { useEffect, useRef, useCallback } from "react";
import { createWebSocket } from "@/lib/ws";

export function useWebSocket(onMessage: (data: string) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    const ws = createWebSocket("/api/ws/chat", token);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      onMessageRef.current(event.data);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return { send };
}
