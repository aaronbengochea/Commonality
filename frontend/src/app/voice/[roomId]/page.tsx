"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import VoiceRoom from "@/components/VoiceRoom";
import { Card } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { ArrowLeft, Phone } from "lucide-react";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://localhost:7880";

export default function VoiceRoomPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const { user, loading } = useAuth("/login");
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user || !roomId) return;
    let cancelled = false;

    api
      .post("/api/voice/token", { chat_id: roomId })
      .then((data) => {
        if (!cancelled) setToken(data.token);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to join voice room");
      });

    return () => {
      cancelled = true;
    };
  }, [user, roomId]);

  function handleDisconnected() {
    router.push(`/chat/${roomId}`);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }
  if (!user) return null;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="absolute left-6 top-6">
        <Link
          href={`/chat/${roomId}`}
          className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to chat
        </Link>
      </div>

      <Card className="flex w-full max-w-md flex-col items-center py-10">
        <Phone className="mb-4 h-10 w-10 text-muted-foreground" />
        <h1 className="mb-1 bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-2xl font-bold text-transparent">
          Voice Call
        </h1>
        <p className="mb-6 text-sm text-muted-foreground">
          {token ? "In call" : "Connecting..."}
        </p>

        {error && (
          <Alert variant="destructive" className="mb-4 w-full">{error}</Alert>
        )}

        {token ? (
          <VoiceRoom
            token={token}
            serverUrl={LIVEKIT_URL}
            userId={user.userId}
            onDisconnected={handleDisconnected}
          />
        ) : (
          !error && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <div className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
              <span className="text-sm">Connecting to voice room...</span>
            </div>
          )
        )}
      </Card>
    </main>
  );
}
