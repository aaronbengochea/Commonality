"""Tests for the walkie-talkie pipeline orchestration logic."""
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
    room.connection_state = 3
    room.disconnect = AsyncMock()
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
