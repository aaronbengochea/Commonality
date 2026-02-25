"use client";

import { useCallback } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Mic, MicOff, LogOut } from "lucide-react";
import { useWalkieTalkie } from "@/hooks/useWalkieTalkie";
import type { TranscriptEntry } from "@/hooks/useWalkieTalkie";
import WaveformVisualizer from "./WaveformVisualizer";

interface VoiceRoomProps {
  token: string;
  serverUrl: string;
  userId: string;
  onDisconnected: () => void;
}

function WalkieTalkieControls({
  userId,
  onLeave,
}: {
  userId: string;
  onLeave: () => void;
}) {
  const room = useRoomContext();
  const {
    state,
    transcripts,
    error,
    isMyTurn,
    canSpeak,
    toggleRecording,
    clearError,
  } = useWalkieTalkie(room, userId);

  const handleToggle = useCallback(async () => {
    await toggleRecording();
  }, [toggleRecording]);

  const buttonLabel = (() => {
    if (state === "idle") return "Tap to Speak";
    if (state === "recording" && isMyTurn) return "Tap to Stop";
    if (state === "recording") return "Listening...";
    if (state === "processing") return "Translating...";
    if (state === "playing") return "Playing...";
    return "Tap to Speak";
  })();

  const buttonDisabled = (() => {
    if (state === "idle") return false;
    if (state === "recording" && isMyTurn) return false;
    return true;
  })();

  return (
    <div className="flex flex-col items-center gap-6 w-full">
      {/* Waveform */}
      <div className="w-full rounded-xl bg-white/5 p-4">
        <WaveformVisualizer state={state} />
        <p className="text-center text-sm text-slate-400 mt-2">
          {state === "idle" && "Ready"}
          {state === "recording" && isMyTurn && "Recording..."}
          {state === "recording" && !isMyTurn && "Other user is speaking..."}
          {state === "processing" && "Translating..."}
          {state === "playing" && "Playing translation..."}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div
          className="w-full bg-red-500/20 border border-red-500/40 rounded-lg p-3 text-red-300 text-sm cursor-pointer"
          onClick={clearError}
        >
          {error} (tap to dismiss)
        </div>
      )}

      {/* Transcripts */}
      {transcripts.length > 0 && (
        <div className="w-full max-h-48 overflow-y-auto space-y-3">
          {transcripts.map((t: TranscriptEntry, i: number) => (
            <div key={i} className="bg-white/5 rounded-lg p-3 space-y-1">
              <p className="text-sm text-slate-300">
                <span className="text-slate-500">Original:</span> {t.originalText}
              </p>
              <p className="text-sm text-white">
                <span className="text-slate-500">Translated:</span> {t.translatedText}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Push-to-talk button */}
      <button
        onClick={handleToggle}
        disabled={buttonDisabled}
        className={`
          w-24 h-24 rounded-full flex items-center justify-center
          transition-all duration-200 text-white
          ${state === "recording" && isMyTurn
            ? "bg-red-500 hover:bg-red-600 scale-110 shadow-lg shadow-red-500/30"
            : canSpeak
              ? "bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
              : "bg-slate-700 cursor-not-allowed opacity-50"
          }
        `}
      >
        {state === "recording" && isMyTurn ? (
          <MicOff className="w-8 h-8" />
        ) : (
          <Mic className="w-8 h-8" />
        )}
      </button>
      <p className="text-sm text-slate-400">{buttonLabel}</p>

      {/* Leave button */}
      <button
        onClick={onLeave}
        className="flex items-center gap-2 text-slate-400 hover:text-red-400 transition-colors text-sm"
      >
        <LogOut className="w-4 h-4" />
        Leave Room
      </button>

      {/* Audio renderer for TTS playback */}
      <RoomAudioRenderer />
    </div>
  );
}

export default function VoiceRoom({
  token,
  serverUrl,
  userId,
  onDisconnected,
}: VoiceRoomProps) {
  return (
    <LiveKitRoom
      serverUrl={serverUrl}
      token={token}
      connect={true}
      audio={false}
      video={false}
      onDisconnected={onDisconnected}
    >
      <WalkieTalkieControls userId={userId} onLeave={onDisconnected} />
    </LiveKitRoom>
  );
}
