const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080";

export function createWebSocket(path: string, token: string): WebSocket {
  const url = `${WS_URL}${path}?token=${token}`;
  return new WebSocket(url);
}
