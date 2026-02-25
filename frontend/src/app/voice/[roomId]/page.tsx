"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import VoiceRoom from "@/components/VoiceRoom";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://localhost:7880";

export default function VoiceRoomPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const { user, loading } = useAuth("/");
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user || !roomId) return;

    api
      .post("/api/voice/token", { chat_id: roomId })
      .then((data) => {
        setToken(data.token);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to join voice room");
      });
  }, [user, roomId]);

  function handleDisconnected() {
    router.push(`/chat/${roomId}`);
  }

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!user) return null;

  return (
    <main className="flex h-screen flex-col items-center justify-center">
      <header className="absolute left-4 top-4">
        <a href={`/chat/${roomId}`} className="text-blue-600 hover:underline">
          &larr; Back to chat
        </a>
      </header>

      <h1 className="mb-2 text-2xl font-bold">Voice Call</h1>
      <p className="mb-6 text-gray-500">Room: {roomId}</p>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {token ? (
        <VoiceRoom
          token={token}
          serverUrl={LIVEKIT_URL}
          onDisconnected={handleDisconnected}
        />
      ) : (
        !error && <p className="text-gray-500">Connecting to voice room...</p>
      )}
    </main>
  );
}
