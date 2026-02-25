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
