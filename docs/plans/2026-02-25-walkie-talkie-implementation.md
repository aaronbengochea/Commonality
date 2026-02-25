# Walkie-Talkie Voice Translation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the full-duplex voice room with a push-to-talk walkie-talkie interface where one user speaks at a time and the translation pipeline (STT → translate → TTS) runs between turns.

**Architecture:** Keep LiveKit as the audio transport. Add a turn-taking state machine synchronized via LiveKit Data Channels. The backend translation-agent listens for data channel signals to start/stop recording and orchestrates the pipeline. The frontend replaces the LiveKit ControlBar with a custom tap-to-toggle button, animated waveform, and transcript display.

**Tech Stack:** Python/FastAPI backend, LiveKit Python SDK (`livekit.rtc`), ElevenLabs Scribe v2 (STT) + TTS WebSocket, OpenAI translation, Next.js 14 frontend, `livekit-client` JS SDK, React

**Design doc:** `docs/plans/2026-02-25-walkie-talkie-voice-translation-design.md`

---

## Task 1: Define Data Channel Signal Protocol

**Files:**
- Create: `backend/app/voice/signals.py`
- Test: `backend/tests/test_voice_signals.py`

This module defines the signal types and serialization used by both the backend agent and frontend for turn-taking coordination via LiveKit Data Channels.

**Step 1: Write the test**

```python
# backend/tests/test_voice_signals.py
import json
from app.voice.signals import Signal, encode_signal, decode_signal


def test_encode_recording_start():
    payload = encode_signal(Signal.RECORDING_START, user_id="user-123")
    data = json.loads(payload)
    assert data["signal"] == "RECORDING_START"
    assert data["userId"] == "user-123"


def test_encode_tts_playing_with_texts():
    payload = encode_signal(
        Signal.TTS_PLAYING,
        original_text="Hello",
        translated_text="Hola",
    )
    data = json.loads(payload)
    assert data["signal"] == "TTS_PLAYING"
    assert data["originalText"] == "Hello"
    assert data["translatedText"] == "Hola"


def test_decode_signal():
    raw = json.dumps({"signal": "RECORDING_STOP", "userId": "user-456"})
    sig, data = decode_signal(raw)
    assert sig == Signal.RECORDING_STOP
    assert data["userId"] == "user-456"


def test_decode_unknown_signal():
    raw = json.dumps({"signal": "UNKNOWN"})
    sig, data = decode_signal(raw)
    assert sig is None


def test_encode_simple_signals():
    for sig_type in [Signal.PROCESSING, Signal.TTS_COMPLETE]:
        payload = encode_signal(sig_type)
        data = json.loads(payload)
        assert data["signal"] == sig_type.value


def test_encode_error_signal():
    payload = encode_signal(Signal.ERROR, message="STT failed")
    data = json.loads(payload)
    assert data["signal"] == "ERROR"
    assert data["message"] == "STT failed"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_voice_signals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.voice.signals'`

**Step 3: Write the implementation**

```python
# backend/app/voice/signals.py
"""Data channel signal protocol for walkie-talkie turn-taking.

Signals are JSON-encoded strings sent via LiveKit Data Channels
with topic="walkie-talkie". Both the backend agent and frontend
use the same signal format.

Signal flow for one turn:
  RECORDING_START (frontend) → RECORDING_STOP (frontend) →
  PROCESSING (backend) → TTS_PLAYING (backend) → TTS_COMPLETE (backend)
"""
import json
from enum import Enum
from typing import Any


class Signal(Enum):
    RECORDING_START = "RECORDING_START"
    RECORDING_STOP = "RECORDING_STOP"
    PROCESSING = "PROCESSING"
    TTS_PLAYING = "TTS_PLAYING"
    TTS_COMPLETE = "TTS_COMPLETE"
    ERROR = "ERROR"


TOPIC = "walkie-talkie"

_SIGNAL_LOOKUP = {s.value: s for s in Signal}


def encode_signal(signal: Signal, **kwargs: Any) -> str:
    """Encode a signal with optional payload fields into a JSON string."""
    data: dict[str, Any] = {"signal": signal.value}
    # Map snake_case kwargs to camelCase for frontend compatibility
    key_map = {
        "user_id": "userId",
        "original_text": "originalText",
        "translated_text": "translatedText",
        "message": "message",
    }
    for key, value in kwargs.items():
        camel_key = key_map.get(key, key)
        data[camel_key] = value
    return json.dumps(data)


def decode_signal(raw: str) -> tuple[Signal | None, dict[str, Any]]:
    """Decode a JSON signal string. Returns (Signal, payload_dict) or (None, {}) if unknown."""
    data = json.loads(raw)
    signal_str = data.get("signal")
    signal = _SIGNAL_LOOKUP.get(signal_str)
    return signal, data
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_voice_signals.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add backend/app/voice/signals.py backend/tests/test_voice_signals.py
git commit -m "Add walkie-talkie data channel signal protocol"
```

---

## Task 2: Rewrite Backend Room Agent for Push-to-Talk

**Files:**
- Modify: `backend/app/voice/service.py` (full rewrite of `_room_agent` and `_participant_pipeline`)
- Reference: `backend/app/voice/signals.py` (from Task 1)

The current `_room_agent` starts pipelines automatically when audio tracks appear. The new version waits for `RECORDING_START`/`RECORDING_STOP` data channel signals before processing audio.

**Step 1: Write the test**

```python
# backend/tests/test_voice_walkie_talkie.py
"""Tests for the walkie-talkie pipeline orchestration logic.

These test the signal-driven flow without real LiveKit/ElevenLabs connections.
We mock the external dependencies and verify the correct signals are sent
at each stage of the pipeline.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.voice.signals import Signal, TOPIC, decode_signal


@pytest.fixture
def mock_room():
    """Create a mock LiveKit room with data publishing capability."""
    room = MagicMock()
    room.local_participant = MagicMock()
    room.local_participant.publish_data = AsyncMock()
    room.remote_participants = {"user-1": MagicMock(), "user-2": MagicMock()}
    room.connection_state = 3  # CONN_CONNECTED
    room.disconnect = AsyncMock()
    # Store event handlers
    room._handlers = {}

    def on(event_name):
        def decorator(fn):
            room._handlers[event_name] = fn
            return fn
        return decorator

    room.on = on
    room.connect = AsyncMock()
    return room


def test_signal_topic_constant():
    """Verify the topic used for walkie-talkie signals."""
    assert TOPIC == "walkie-talkie"


def test_recording_start_signal_decoded():
    raw = json.dumps({"signal": "RECORDING_START", "userId": "user-1"})
    sig, data = decode_signal(raw)
    assert sig == Signal.RECORDING_START
    assert data["userId"] == "user-1"


def test_recording_stop_signal_decoded():
    raw = json.dumps({"signal": "RECORDING_STOP", "userId": "user-1"})
    sig, data = decode_signal(raw)
    assert sig == Signal.RECORDING_STOP
```

**Step 2: Run test to verify it passes** (these are unit tests on signals, not the pipeline itself)

Run: `cd backend && python -m pytest tests/test_voice_walkie_talkie.py -v`
Expected: PASS

**Step 3: Rewrite `_room_agent` in `backend/app/voice/service.py`**

Replace the entire `_room_agent` function (lines 61-144) and `_participant_pipeline` function (lines 147-227) with the new signal-driven versions. Keep `generate_livekit_token`, `_generate_agent_token`, `ensure_pipeline_for_room`, and `_tts_and_publish` mostly unchanged.

The new `_room_agent` should:

```python
async def _room_agent(room_name: str, chat_id: str):
    """Join a LiveKit room and orchestrate walkie-talkie translation turns.

    Listens for data channel signals from frontends:
    - RECORDING_START: a user started recording
    - RECORDING_STOP: a user stopped recording, begin STT → translate → TTS

    Sends signals back to frontends:
    - PROCESSING: pipeline is transcribing/translating
    - TTS_PLAYING: TTS audio is about to play, includes transcripts
    - TTS_COMPLETE: turn is done, buttons unlock
    - ERROR: something failed, buttons unlock
    """
    agent_token = _generate_agent_token(room_name)
    livekit_url = settings.livekit_url
    room = rtc.Room()

    # Resolve chat members and their languages
    chat_meta = get_chat_meta(chat_id)
    if not chat_meta:
        return
    member_ids = chat_meta.get("memberUserIds", [])
    members = {}
    for uid in member_ids:
        user = get_user_by_id(uid)
        if user:
            user.pop("passwordHash", None)
            members[uid] = user

    if len(members) < 2:
        return

    stop_event = asyncio.Event()
    # Track the current recording session
    recording_speaker_id: str | None = None
    audio_stream: rtc.AudioStream | None = None
    audio_frames: list[rtc.AudioFrameEvent] = []
    recording_active = asyncio.Event()

    async def _publish_signal(signal: Signal, **kwargs):
        """Send a signal to all participants via data channel."""
        payload = encode_signal(signal, **kwargs)
        await room.local_participant.publish_data(
            payload, reliable=True, topic=TOPIC
        )

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        nonlocal audio_stream
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        # We'll create audio streams on demand when recording starts
        # For now, just log that we can hear this participant
        logger.debug("Audio track available for %s", participant.identity)

    @room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        nonlocal recording_speaker_id, audio_stream, recording_active
        if data_packet.topic != TOPIC:
            return

        sig, payload = decode_signal(data_packet.data.decode("utf-8"))

        if sig == Signal.RECORDING_START:
            speaker_id = payload.get("userId")
            if speaker_id and speaker_id in members:
                recording_speaker_id = speaker_id
                # Find the speaker's audio track and create a stream
                for participant in room.remote_participants.values():
                    if participant.identity == speaker_id:
                        for pub in participant.track_publications.values():
                            if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                                audio_stream = rtc.AudioStream(pub.track)
                                break
                        break
                recording_active.set()
                logger.info("Recording started for %s", speaker_id)

        elif sig == Signal.RECORDING_STOP:
            recording_active.clear()
            logger.info("Recording stopped for %s", payload.get("userId"))

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        nonlocal recording_speaker_id
        if participant.identity == recording_speaker_id:
            recording_active.clear()
            recording_speaker_id = None

    try:
        await room.connect(livekit_url, agent_token)
        logger.info("Translation agent joined room %s", room_name)

        while not stop_event.is_set():
            # Wait for a recording session to start
            try:
                await asyncio.wait_for(recording_active.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                # Check if room is empty
                if len(room.remote_participants) == 0:
                    await asyncio.sleep(5)
                    if len(room.remote_participants) == 0:
                        break
                continue

            # A recording session has started
            speaker_id = recording_speaker_id
            if not speaker_id or not audio_stream:
                recording_active.clear()
                continue

            # Collect audio while recording is active
            try:
                await _run_walkie_talkie_turn(
                    room, audio_stream, speaker_id, members,
                    recording_active, _publish_signal, stop_event,
                )
            except Exception:
                logger.exception("Walkie-talkie turn failed for %s", speaker_id)
                try:
                    await _publish_signal(Signal.ERROR, message="Translation failed")
                except Exception:
                    pass

            # Reset for next turn
            recording_speaker_id = None
            audio_stream = None

    finally:
        stop_event.set()
        await room.disconnect()
        logger.info("Translation agent left room %s", room_name)
```

**Step 4: Write `_run_walkie_talkie_turn`** (new function replacing `_participant_pipeline`)

```python
async def _run_walkie_talkie_turn(
    room: rtc.Room,
    audio_stream: rtc.AudioStream,
    speaker_id: str,
    members: dict[str, dict],
    recording_active: asyncio.Event,
    publish_signal,
    stop_event: asyncio.Event,
):
    """Execute one walkie-talkie turn: collect audio → STT → translate → TTS.

    This function blocks until the full turn is complete (TTS finished playing).
    """
    speaker = members[speaker_id]
    listener_id = next((uid for uid in members if uid != speaker_id), None)
    if not listener_id:
        return
    listener = members[listener_id]

    source_lang = speaker.get("nativeLanguage", "en")
    target_lang = listener.get("nativeLanguage", "en")

    if source_lang == target_lang:
        await publish_signal(Signal.TTS_COMPLETE)
        return

    # --- Phase 1: Collect audio via STT ---
    stt_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime"
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    transcript_parts: list[str] = []

    async with websockets.connect(stt_url, additional_headers=headers) as stt_ws:
        async def send_audio():
            async for event in audio_stream:
                if not recording_active.is_set() or stop_event.is_set():
                    break
                if isinstance(event, rtc.AudioFrameEvent):
                    pcm_data = event.frame.data.tobytes()
                    audio_b64 = base64.b64encode(pcm_data).decode("utf-8")
                    await stt_ws.send(json.dumps({
                        "message_type": "input_audio_chunk",
                        "audio_base_64": audio_b64,
                        "commit": False,
                        "sample_rate": event.frame.sample_rate,
                    }))

            # Send manual commit to flush any remaining audio
            try:
                await stt_ws.send(json.dumps({
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "commit": True,
                    "sample_rate": 16000,
                }))
            except Exception:
                logger.debug("Could not send final STT commit")

        async def receive_transcripts():
            async for message in stt_ws:
                data = json.loads(message)
                msg_type = data.get("message_type")
                if msg_type == "committed_transcript":
                    text = data.get("text", "").strip()
                    if text:
                        transcript_parts.append(text)
                elif msg_type == "input_error":
                    logger.warning("STT error for %s: %s", speaker_id, data.get("message"))

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_transcripts())

        # Wait for sender to finish (recording stopped), then give receiver
        # a short window to get the final committed transcript
        await sender
        try:
            await asyncio.wait_for(receiver, timeout=5.0)
        except asyncio.TimeoutError:
            receiver.cancel()

    full_transcript = " ".join(transcript_parts)
    if not full_transcript:
        await publish_signal(Signal.TTS_COMPLETE)
        return

    # --- Phase 2: Translate ---
    await publish_signal(Signal.PROCESSING)

    loop = asyncio.get_event_loop()
    translated = await loop.run_in_executor(
        None, translate_text, full_transcript, source_lang, target_lang
    )

    # --- Phase 3: TTS and publish ---
    await publish_signal(
        Signal.TTS_PLAYING,
        original_text=full_transcript,
        translated_text=translated,
    )
    await _tts_and_publish(translated, room, speaker_id)

    await publish_signal(Signal.TTS_COMPLETE)
```

**Step 5: Add imports to service.py**

At the top of `backend/app/voice/service.py`, add:

```python
from app.voice.signals import Signal, TOPIC, encode_signal, decode_signal
```

**Step 6: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add backend/app/voice/service.py
git commit -m "Rewrite voice service for push-to-talk walkie-talkie flow

- Replace continuous pipeline with signal-driven turn-taking
- Agent listens for RECORDING_START/STOP via LiveKit data channels
- Full turn: collect audio → STT → translate → TTS → unlock
- Send PROCESSING/TTS_PLAYING/TTS_COMPLETE signals to frontends"
```

---

## Task 3: Create Frontend Walkie-Talkie Hook

**Files:**
- Create: `frontend/src/hooks/useWalkieTalkie.ts`
- Reference: `frontend/src/types/index.ts`

This hook manages the walkie-talkie state machine on the frontend, driven by LiveKit data channel messages.

**Step 1: Write the hook**

```typescript
// frontend/src/hooks/useWalkieTalkie.ts
"use client";

import { useReducer, useCallback, useEffect, useRef } from "react";
import type { Room } from "livekit-client";
import { RoomEvent, DataPacket_Kind } from "livekit-client";

// Signal types matching backend/app/voice/signals.py
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
      return {
        ...store,
        state: "recording",
        activeSpeakerId: action.userId,
        error: null,
      };
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
          {
            originalText: action.originalText,
            translatedText: action.translatedText,
            speakerId: action.speakerId,
            timestamp: Date.now(),
          },
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

  // Listen for data channel signals from other participants and backend agent
  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: DataPacket_Kind,
      topic: string | undefined,
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
      await room.localParticipant.publishData(data, {
        reliable: true,
        topic: TOPIC,
      });
    },
    [room],
  );

  const startRecording = useCallback(async () => {
    if (store.state !== "idle" || !room) return;

    // Unmute mic
    await room.localParticipant.setMicrophoneEnabled(true);

    // Notify others
    await sendSignal("RECORDING_START", { userId });
    dispatch({ type: "RECORDING_START", userId });

    // Safety timeout: 30s max recording
    timeoutRef.current = setTimeout(() => {
      stopRecording();
    }, 30000);
  }, [store.state, room, userId, sendSignal]);

  const stopRecording = useCallback(async () => {
    if (store.state !== "recording" || !room) return;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    // Mute mic
    await room.localParticipant.setMicrophoneEnabled(false);

    // Notify others and backend
    await sendSignal("RECORDING_STOP", { userId });
    dispatch({ type: "RECORDING_STOP" });

    // Safety timeout: 30s for pipeline to complete
    timeoutRef.current = setTimeout(() => {
      dispatch({ type: "ERROR", message: "Translation timed out" });
    }, 30000);
  }, [store.state, room, userId, sendSignal]);

  const toggleRecording = useCallback(async () => {
    if (store.state === "idle") {
      await startRecording();
    } else if (store.state === "recording" && store.activeSpeakerId === userId) {
      await stopRecording();
    }
  }, [store.state, store.activeSpeakerId, userId, startRecording, stopRecording]);

  const clearError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
  }, []);

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
```

**Step 2: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (or only pre-existing ones)

**Step 3: Commit**

```bash
git add frontend/src/hooks/useWalkieTalkie.ts
git commit -m "Add useWalkieTalkie hook for push-to-talk state machine

- Reducer-based state: idle → recording → processing → playing → idle
- Listens for LiveKit data channel signals
- Sends RECORDING_START/STOP signals
- 30s safety timeouts for recording and pipeline"
```

---

## Task 4: Create Waveform Visualizer Component

**Files:**
- Create: `frontend/src/components/WaveformVisualizer.tsx`

A simple animated waveform that responds to the walkie-talkie state.

**Step 1: Write the component**

```typescript
// frontend/src/components/WaveformVisualizer.tsx
"use client";

import { useEffect, useRef } from "react";
import type { WalkieState } from "@/hooks/useWalkieTalkie";

interface WaveformVisualizerProps {
  state: WalkieState;
  className?: string;
}

export default function WaveformVisualizer({ state, className = "" }: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const barCount = 32;
    const barWidth = width / barCount * 0.6;
    const gap = width / barCount * 0.4;
    let phase = 0;

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + gap) + gap / 2;
        let barHeight: number;

        if (state === "idle") {
          // Gentle idle animation
          barHeight = 4 + Math.sin(phase + i * 0.3) * 2;
        } else if (state === "recording") {
          // Active recording — taller, faster bars
          barHeight = 8 + Math.sin(phase * 2 + i * 0.4) * (height * 0.35);
        } else if (state === "processing") {
          // Pulsing — uniform gentle pulse
          barHeight = 6 + Math.sin(phase * 1.5) * 8;
        } else {
          // Playing — medium animation
          barHeight = 6 + Math.sin(phase * 1.8 + i * 0.5) * (height * 0.25);
        }

        const y = (height - barHeight) / 2;

        // Color based on state
        if (state === "recording") {
          ctx.fillStyle = "rgba(239, 68, 68, 0.8)"; // red
        } else if (state === "processing") {
          ctx.fillStyle = "rgba(250, 204, 21, 0.7)"; // yellow
        } else if (state === "playing") {
          ctx.fillStyle = "rgba(34, 197, 94, 0.8)"; // green
        } else {
          ctx.fillStyle = "rgba(148, 163, 184, 0.4)"; // gray
        }

        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }

      phase += 0.05;
      animationRef.current = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
    };
  }, [state]);

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-24 ${className}`}
      style={{ display: "block" }}
    />
  );
}
```

**Step 2: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/WaveformVisualizer.tsx
git commit -m "Add animated waveform visualizer for walkie-talkie states

- Canvas-based animation with state-driven bar heights and colors
- Red for recording, yellow for processing, green for playing, gray for idle
- DPR-aware rendering for crisp display on retina screens"
```

---

## Task 5: Create Walkie-Talkie Voice Room Component

**Files:**
- Modify: `frontend/src/components/VoiceRoom.tsx` (replace contents)
- Reference: `frontend/src/hooks/useWalkieTalkie.ts`, `frontend/src/components/WaveformVisualizer.tsx`

Replace the current ControlBar-based VoiceRoom with the walkie-talkie UI.

**Step 1: Read the current VoiceRoom.tsx** (already read above — 42 lines)

**Step 2: Rewrite VoiceRoom.tsx**

```typescript
// frontend/src/components/VoiceRoom.tsx
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
    activeSpeakerId,
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
            <div
              key={i}
              className="bg-white/5 rounded-lg p-3 space-y-1"
            >
              <p className="text-sm text-slate-300">
                <span className="text-slate-500">Original:</span>{" "}
                {t.originalText}
              </p>
              <p className="text-sm text-white">
                <span className="text-slate-500">Translated:</span>{" "}
                {t.translatedText}
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
      audio={true}
      video={false}
      onDisconnected={onDisconnected}
    >
      <WalkieTalkieControls userId={userId} onLeave={onDisconnected} />
    </LiveKitRoom>
  );
}
```

**Step 3: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/VoiceRoom.tsx
git commit -m "Replace VoiceRoom with walkie-talkie push-to-talk UI

- Custom tap-to-toggle button with state-driven styling
- Waveform visualizer shows recording/processing/playing states
- Scrollable transcript area showing original + translated text
- Leave room button to exit back to chat"
```

---

## Task 6: Update Voice Room Page to Pass userId

**Files:**
- Modify: `frontend/src/app/voice/[roomId]/page.tsx`

The new `VoiceRoom` component needs a `userId` prop. The page already has the user from `useAuth`.

**Step 1: Read the current page** (already read — 96 lines)

**Step 2: Update the VoiceRoom usage**

In `frontend/src/app/voice/[roomId]/page.tsx`, find the VoiceRoom component usage and add the `userId` prop:

Change:
```tsx
<VoiceRoom
  token={token}
  serverUrl={LIVEKIT_URL}
  onDisconnected={handleDisconnected}
/>
```

To:
```tsx
<VoiceRoom
  token={token}
  serverUrl={LIVEKIT_URL}
  userId={user.userId}
  onDisconnected={handleDisconnected}
/>
```

**Step 3: Also update the mic-muted connection**

The `VoiceRoom` component now starts with mic muted (the hook unmutes on record). Update the LiveKitRoom in VoiceRoom.tsx to start with mic disabled. In the `LiveKitRoom` component, change `audio={true}` to `audio={false}`:

```tsx
<LiveKitRoom
  serverUrl={serverUrl}
  token={token}
  connect={true}
  audio={false}  // Start muted; hook enables mic on recording
  video={false}
  onDisconnected={onDisconnected}
>
```

**Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/app/voice/[roomId]/page.tsx frontend/src/components/VoiceRoom.tsx
git commit -m "Wire userId to VoiceRoom and start with mic muted

- Pass user.userId from page to VoiceRoom component
- Start LiveKitRoom with audio=false (mic muted by default)
- Hook enables mic only during active recording"
```

---

## Task 7: Integration Testing with Docker

**Files:** None (manual testing)

This task verifies the full walkie-talkie flow works end-to-end through the ngrok tunnel.

**Step 1: Start the stack**

```bash
make up
```

Wait for all containers to be healthy.

**Step 2: Start ngrok tunnel**

In a separate terminal:
```bash
make tunnel
```

**Step 3: Configure environment**

```bash
make tunnel-restart
```

**Step 4: Test the flow**

1. Open the ngrok URL in Browser A, register User A (English)
2. Open the ngrok URL in Browser B (or incognito), register User B (Spanish)
3. Create a chat between them
4. Navigate to voice room from the chat
5. Verify both users see the "Tap to Speak" button in IDLE state
6. User A taps "Tap to Speak" → button changes to "Tap to Stop", waveform animates red
7. User B sees button locked with "Listening..." text
8. User A speaks in English, then taps "Tap to Stop"
9. Both users see "Translating..." with yellow pulsing waveform
10. User B hears Spanish TTS audio, both see original + translated transcripts
11. Both buttons unlock to IDLE
12. User B can now tap to speak and respond

**Step 5: Verify error handling**

- Test disconnect during recording
- Test the 30s safety timeout by starting recording and waiting

**Step 6: Commit any fixes discovered during testing**

---

## Task Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Signal protocol module | `signals.py` + test |
| 2 | Backend agent rewrite for push-to-talk | `service.py` |
| 3 | `useWalkieTalkie` React hook | `useWalkieTalkie.ts` |
| 4 | Waveform visualizer component | `WaveformVisualizer.tsx` |
| 5 | VoiceRoom UI rewrite | `VoiceRoom.tsx` |
| 6 | Wire userId prop + mic mute | `page.tsx` + `VoiceRoom.tsx` |
| 7 | Integration test via ngrok | Manual testing |
