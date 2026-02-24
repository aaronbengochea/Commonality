"use client";

import { useParams } from "next/navigation";

export default function VoiceRoomPage() {
  const { roomId } = useParams<{ roomId: string }>();

  return (
    <main className="flex h-screen flex-col items-center justify-center">
      <h1 className="text-2xl font-bold">Voice Room</h1>
      <p className="mt-2 text-gray-500">Room: {roomId}</p>
      {/* TODO: LiveKit room component in Phase 4 */}
    </main>
  );
}
