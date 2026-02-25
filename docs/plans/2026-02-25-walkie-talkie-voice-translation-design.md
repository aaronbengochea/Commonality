# Walkie-Talkie Voice Translation Design

## Overview

Replace the current full-duplex LiveKit voice room with a push-to-talk walkie-talkie interface. One user speaks at a time; their speech is transcribed, translated, and spoken back to the other user in their native language via ElevenLabs TTS.

## Goals

- Eliminate audio overlap issues from simultaneous speaking
- Provide clear turn-taking UX so users know when to speak
- Show both original and translated transcripts for transparency
- Use ElevenLabs pre-made voice for TTS (no voice cloning for MVP)
- Ephemeral voice messages (not persisted to chat history)

## Architecture: LiveKit Push-to-Talk

Keep LiveKit as the audio transport layer. Add push-to-talk signaling via LiveKit Data Channels. The backend translation-agent joins the room and orchestrates the STT → translate → TTS pipeline, triggered by data channel signals.

### Why LiveKit

- Existing infrastructure already works (token generation, room management, audio tracks)
- LiveKit Data Channels provide low-latency signaling (no extra WebSocket needed)
- Built-in audio handling (mic permissions, echo cancellation, noise suppression)
- Minimal changes to existing backend pipeline

## Turn-Taking State Machine

Both users share a synchronized state driven by data channel messages.

### States

| State | Speaker's UI | Receiver's UI |
|---|---|---|
| **IDLE** | Button enabled: "Tap to Speak" | Button enabled: "Tap to Speak" |
| **RECORDING** | Button active: "Tap to Stop" | Button locked: "Listening..." |
| **PROCESSING** | Button locked, waveform pulses | Button locked, waveform pulses |
| **PLAYING** | Button locked, shows transcripts | Button locked, hears TTS, shows transcripts |

### Transitions

```
IDLE → RECORDING          User taps "Speak" button
RECORDING → PROCESSING    User taps "Stop" button
PROCESSING → PLAYING      TTS audio begins
PLAYING → IDLE            TTS audio finishes
Any → IDLE (error)        Pipeline failure or timeout
```

### Data Channel Signals

| Signal | Sender | Payload | Purpose |
|---|---|---|---|
| `RECORDING_START` | Frontend (speaker) | `{userId}` | Lock other user's button |
| `RECORDING_STOP` | Frontend (speaker) | `{userId}` | Backend begins STT pipeline |
| `PROCESSING` | Backend agent | `{}` | Both UIs show processing state |
| `TTS_PLAYING` | Backend agent | `{originalText, translatedText}` | Show transcripts, play audio |
| `TTS_COMPLETE` | Backend agent | `{}` | Unlock both buttons → IDLE |
| `ERROR` | Backend agent | `{message}` | Unlock both buttons, show error |

## Backend Pipeline

### Signal-Driven Flow

1. Agent joins room, listens for data channel signals
2. On `RECORDING_START`: subscribe to speaker's audio track, begin piping to ElevenLabs Scribe v2 realtime WebSocket
3. On `RECORDING_STOP`: flush STT, collect final committed transcript
4. Send `PROCESSING` signal to room
5. Translate via OpenAI (`gpt-4o-mini`): speaker's language → receiver's native language
6. Send `TTS_PLAYING` signal with `{originalText, translatedText}`
7. Run ElevenLabs TTS (`eleven_flash_v2_5`) → publish audio as LocalAudioTrack to room
8. On TTS audio complete: send `TTS_COMPLETE` signal

### Changes to `voice/service.py`

- Replace continuous audio subscription with signal-driven recording
- Add `room.on("data_received")` handler for turn-taking signals
- Buffer complete STT transcript before translating
- Send data channel signals at each pipeline stage
- Mute handling: speaker's mic track unmuted only during RECORDING state

### What Stays the Same

- LiveKit room + token generation
- ElevenLabs Scribe v2 realtime WebSocket for STT
- OpenAI translation via `translate_text()`
- ElevenLabs TTS streaming WebSocket
- Agent joining room as "translation-agent"
- Config via environment variables

## Frontend Voice Room UI

### Layout

```
┌─────────────────────────────────────┐
│  ← Back to Chat     Voice Room      │
│                                     │
│  ┌─────────────────────────────────┐│
│  │     [Animated Waveform Area]    ││
│  │                                 ││
│  │  Status: "Ready" / "Recording"  ││
│  │          "Translating..."       ││
│  │          "Playing translation"  ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  Original: "Hello, how are you?"││
│  │  Translated: "Hola, ¿cómo...?" ││
│  └─────────────────────────────────┘│
│                                     │
│         ┌───────────────┐           │
│         │  🎙 Tap to    │           │
│         │    Speak      │           │
│         └───────────────┘           │
│                                     │
│         [Leave Room]                │
└─────────────────────────────────────┘
```

### Components

- **Waveform visualizer**: animated during recording, processing, and playback; dormant when idle
- **Transcript area**: scrollable list of conversation turns, each showing original + translated text
- **Push-to-talk button**: large, centered, tap-to-toggle (tap to start recording, tap again to stop)
- **Leave room button**: exits back to chat

### Button States

| State | Label | Appearance |
|---|---|---|
| IDLE | "Tap to Speak" | Enabled, default style |
| RECORDING (self) | "Tap to Stop" | Active/highlighted, pulsing |
| RECORDING (other) | "Listening..." | Disabled/grayed |
| PROCESSING | "Translating..." | Disabled, spinner/pulse |
| PLAYING | "Playing..." | Disabled |

### State Management

- `useReducer` hook driven by LiveKit data channel messages
- `<LiveKitRoom>` component retained for connection management
- Custom inner components replace `<ControlBar>`
- `<RoomAudioRenderer>` retained for TTS audio playback

## Data Flow (One Turn)

```
User A (English)                    Backend Agent                    User B (Spanish)
     │                                    │                               │
     │ TAP "Speak"                        │                               │
     │──RECORDING_START──────────────────▶│──RECORDING_START─────────────▶│
     │  mic unmutes                       │                               │ button locks
     │                                    │                               │
     │ ~~~speaking~~~                     │                               │
     │ ──audio track streams────────────▶ │ (piping to STT WS)           │
     │                                    │                               │
     │ TAP "Stop"                         │                               │
     │──RECORDING_STOP──────────────────▶ │                               │
     │  mic mutes                         │                               │
     │                                    │ flush STT → transcript        │
     │◀──PROCESSING───────────────────────│──PROCESSING──────────────────▶│
     │                                    │ OpenAI translate              │
     │◀──TTS_PLAYING {texts}──────────────│──TTS_PLAYING {texts}─────────▶│
     │  shows transcripts                 │ ElevenLabs TTS → audio track │ hears TTS, shows transcripts
     │                                    │                               │
     │◀──TTS_COMPLETE─────────────────────│──TTS_COMPLETE────────────────▶│
     │  button unlocks                    │                               │ button unlocks
```

## Error Handling

- **STT failure**: send `ERROR` signal, unlock both buttons, show error toast
- **Translation failure**: same
- **TTS failure**: same
- **User disconnects mid-recording**: cancel pipeline, send `TTS_COMPLETE` to unlock remaining user
- **Safety timeout**: if no `TTS_COMPLETE` within 30s of `RECORDING_STOP`, auto-unlock both buttons

## Technical Details

### ElevenLabs STT (Scribe v2 Realtime)

- Endpoint: `wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime`
- Audio format: PCM 16kHz (from LiveKit audio stream)
- Commit strategy: manual (flush on `RECORDING_STOP`)
- Listen for `committed_transcript` messages

### ElevenLabs TTS

- Endpoint: `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_flash_v2_5`
- Voice: pre-made default (`Xb7hH8MSUJpSbSDYk0k2`, configurable via env)
- Output: PCM 24kHz
- Send translated text with `flush: true`, listen for audio chunks until `isFinal`

### Translation

- OpenAI `gpt-4o-mini` via existing `translate_text()` function
- Source language: speaker's `nativeLanguage` from user profile
- Target language: receiver's `nativeLanguage` from user profile

## Future Enhancements (Not in MVP)

- **Voice cloning (IVC)**: let users record a 1-minute voice sample; use their cloned voice for TTS
- **Persist voice messages**: save transcripts to chat history using dual-write pattern
- **Streaming translation**: begin TTS as translation streams in, reducing latency
- **Multi-participant rooms**: extend turn-taking for group calls
