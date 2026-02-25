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
