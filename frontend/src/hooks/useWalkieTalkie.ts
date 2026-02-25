// frontend/src/hooks/useWalkieTalkie.ts
"use client";

import { useReducer, useCallback, useEffect, useRef } from "react";
import type { Room } from "livekit-client";
import { RoomEvent, DataPacket_Kind } from "livekit-client";

const TOPIC = "walkie-talkie";

export type WalkieState = "idle" | "recording" | "processing" | "playing";

export interface TranscriptEntry {
  originalText: string;
  translatedText: string;
  speakerId: string;
  timestamp: number;
}

interface WalkieStore {
  state: WalkieState;
  activeSpeakerId: string | null;
  transcripts: TranscriptEntry[];
  error: string | null;
}

type WalkieAction =
  | { type: "RECORDING_START"; userId: string }
  | { type: "RECORDING_STOP" }
  | { type: "PROCESSING" }
  | { type: "TTS_PLAYING"; originalText: string; translatedText: string; speakerId: string }
  | { type: "TTS_COMPLETE" }
  | { type: "ERROR"; message: string }
  | { type: "CLEAR_ERROR" };

function walkieReducer(store: WalkieStore, action: WalkieAction): WalkieStore {
  switch (action.type) {
    case "RECORDING_START":
      return { ...store, state: "recording", activeSpeakerId: action.userId, error: null };
    case "RECORDING_STOP":
      return { ...store, state: "processing" };
    case "PROCESSING":
      return { ...store, state: "processing" };
    case "TTS_PLAYING":
      return {
        ...store,
        state: "playing",
        transcripts: [
          ...store.transcripts,
          { originalText: action.originalText, translatedText: action.translatedText, speakerId: action.speakerId, timestamp: Date.now() },
        ],
      };
    case "TTS_COMPLETE":
      return { ...store, state: "idle", activeSpeakerId: null };
    case "ERROR":
      return { ...store, state: "idle", activeSpeakerId: null, error: action.message };
    case "CLEAR_ERROR":
      return { ...store, error: null };
    default:
      return store;
  }
}

const initialStore: WalkieStore = {
  state: "idle",
  activeSpeakerId: null,
  transcripts: [],
  error: null,
};

export function useWalkieTalkie(room: Room | undefined, userId: string) {
  const [store, dispatch] = useReducer(walkieReducer, initialStore);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant?: any,
      kind?: DataPacket_Kind,
      topic?: string,
    ) => {
      if (topic !== TOPIC) return;
      const decoder = new TextDecoder();
      const data = JSON.parse(decoder.decode(payload));
      const signal = data.signal as string;

      switch (signal) {
        case "RECORDING_START":
          if (data.userId !== userId) {
            dispatch({ type: "RECORDING_START", userId: data.userId });
          }
          break;
        case "PROCESSING":
          dispatch({ type: "PROCESSING" });
          break;
        case "TTS_PLAYING":
          dispatch({
            type: "TTS_PLAYING",
            originalText: data.originalText || "",
            translatedText: data.translatedText || "",
            speakerId: store.activeSpeakerId || "",
          });
          break;
        case "TTS_COMPLETE":
          dispatch({ type: "TTS_COMPLETE" });
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
          break;
        case "ERROR":
          dispatch({ type: "ERROR", message: data.message || "An error occurred" });
          break;
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room, userId, store.activeSpeakerId]);

  const sendSignal = useCallback(
    async (signal: string, payload: Record<string, string> = {}) => {
      if (!room) return;
      const encoder = new TextEncoder();
      const data = encoder.encode(JSON.stringify({ signal, ...payload }));
      await room.localParticipant.publishData(data, { reliable: true, topic: TOPIC });
    },
    [room],
  );

  const startRecording = useCallback(async () => {
    if (store.state !== "idle" || !room) return;
    await room.localParticipant.setMicrophoneEnabled(true);
    await sendSignal("RECORDING_START", { userId });
    dispatch({ type: "RECORDING_START", userId });
    timeoutRef.current = setTimeout(() => { stopRecording(); }, 30000);
  }, [store.state, room, userId, sendSignal]);

  const stopRecording = useCallback(async () => {
    if (store.state !== "recording" || !room) return;
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
    await room.localParticipant.setMicrophoneEnabled(false);
    await sendSignal("RECORDING_STOP", { userId });
    dispatch({ type: "RECORDING_STOP" });
    timeoutRef.current = setTimeout(() => {
      dispatch({ type: "ERROR", message: "Translation timed out" });
    }, 30000);
  }, [store.state, room, userId, sendSignal]);

  const toggleRecording = useCallback(async () => {
    if (store.state === "idle") { await startRecording(); }
    else if (store.state === "recording" && store.activeSpeakerId === userId) { await stopRecording(); }
  }, [store.state, store.activeSpeakerId, userId, startRecording, stopRecording]);

  const clearError = useCallback(() => { dispatch({ type: "CLEAR_ERROR" }); }, []);

  return {
    state: store.state,
    activeSpeakerId: store.activeSpeakerId,
    transcripts: store.transcripts,
    error: store.error,
    isMyTurn: store.activeSpeakerId === userId,
    canSpeak: store.state === "idle",
    toggleRecording,
    clearError,
  };
}
