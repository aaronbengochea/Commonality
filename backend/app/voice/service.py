import asyncio
import base64
import json
import logging
from datetime import timedelta

import websockets
from livekit import api

from app.chat.service import translate_text
from app.config import settings

logger = logging.getLogger(__name__)


def generate_livekit_token(user_id: str, username: str, room_name: str) -> str:
    """Generate a LiveKit access token for joining a room."""
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(user_id)
        .with_name(username)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_ttl(timedelta(hours=1))
    )
    return token.to_jwt()


async def run_stt_translate_tts(
    audio_chunks: asyncio.Queue,
    output_audio: asyncio.Queue,
    source_lang: str,
    target_lang: str,
    stop_event: asyncio.Event,
):
    """Run the full STT -> translate -> TTS pipeline.

    Reads raw PCM audio chunks from audio_chunks queue,
    sends them to ElevenLabs STT (Scribe v2),
    translates committed transcripts via OpenAI,
    synthesizes translated text via ElevenLabs TTS,
    and puts resulting audio chunks into output_audio queue.
    """
    stt_task = asyncio.create_task(
        _stt_pipeline(audio_chunks, output_audio, source_lang, target_lang, stop_event)
    )
    try:
        await stt_task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Voice pipeline error")


async def _stt_pipeline(
    audio_chunks: asyncio.Queue,
    output_audio: asyncio.Queue,
    source_lang: str,
    target_lang: str,
    stop_event: asyncio.Event,
):
    """Connect to ElevenLabs STT WebSocket and process audio."""
    stt_url = (
        f"wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        f"?model_id=scribe_v2_realtime"
    )
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    async with websockets.connect(stt_url, additional_headers=headers) as stt_ws:
        # Task to send audio chunks to STT
        async def send_audio():
            while not stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_chunks.get(), timeout=0.1)
                    audio_b64 = base64.b64encode(chunk).decode("utf-8")
                    await stt_ws.send(json.dumps({
                        "message_type": "input_audio_chunk",
                        "audio_base_64": audio_b64,
                        "commit": False,
                        "sample_rate": 16000,
                    }))
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break

            # Send final commit
            await stt_ws.send(json.dumps({
                "message_type": "input_audio_chunk",
                "audio_base_64": "",
                "commit": True,
                "sample_rate": 16000,
            }))

        # Task to receive STT results and run TTS
        async def receive_transcripts():
            async for message in stt_ws:
                data = json.loads(message)
                msg_type = data.get("message_type")

                if msg_type == "committed_transcript":
                    text = data.get("text", "").strip()
                    if not text:
                        continue

                    # Translate the committed transcript
                    if source_lang == target_lang:
                        translated = text
                    else:
                        translated = translate_text(text, source_lang, target_lang)

                    # Synthesize via TTS
                    await _tts_synthesize(translated, output_audio)

                elif msg_type == "input_error":
                    logger.warning("STT error: %s", data.get("message", ""))

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_transcripts())

        try:
            await asyncio.gather(sender, receiver)
        finally:
            sender.cancel()
            receiver.cancel()


async def _tts_synthesize(text: str, output_audio: asyncio.Queue):
    """Send text to ElevenLabs TTS WebSocket and collect audio chunks."""
    voice_id = settings.elevenlabs_tts_voice_id
    model_id = settings.elevenlabs_tts_model
    tts_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
        f"?model_id={model_id}"
    )

    async with websockets.connect(tts_url) as tts_ws:
        # Initialize connection with API key and voice settings
        await tts_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "xi_api_key": settings.elevenlabs_api_key,
        }))

        # Send the translated text
        await tts_ws.send(json.dumps({"text": text, "flush": True}))

        # Close the text stream
        await tts_ws.send(json.dumps({"text": ""}))

        # Receive audio chunks
        async for message in tts_ws:
            data = json.loads(message)
            audio_b64 = data.get("audio")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                await output_audio.put(audio_bytes)

            if data.get("isFinal"):
                break
