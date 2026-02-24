"use client";

import { useEffect, useRef, useCallback } from "react";

export function useWebSocket(url: string, onMessage: (data: string) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // TODO: Implement WebSocket connection in Phase 3
    return () => {
      wsRef.current?.close();
    };
  }, [url]);

  const send = useCallback((data: string) => {
    wsRef.current?.send(data);
  }, []);

  return { send };
}
