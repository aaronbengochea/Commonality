import asyncio
import base64
import json
import logging
from datetime import timedelta

import websockets
from livekit import api, rtc

from app.auth.service import get_user_by_id
from app.chat.service import get_chat_meta, translate_text
from app.config import settings
from app.voice.signals import Signal, TOPIC, encode_signal, decode_signal

logger = logging.getLogger(__name__)

# Track active pipeline tasks per room to prevent duplicates
_active_rooms: dict[str, asyncio.Task] = {}


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


def _generate_agent_token(room_name: str) -> str:
    """Generate a LiveKit token for the server-side translation agent."""
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity("translation-agent")
        .with_name("Translation Agent")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_ttl(timedelta(hours=2))
    )
    return token.to_jwt()


async def ensure_pipeline_for_room(room_name: str, chat_id: str):
    """Start a translation pipeline agent for a room if one isn't already running."""
    if room_name in _active_rooms and not _active_rooms[room_name].done():
        return

    task = asyncio.create_task(_room_agent(room_name, chat_id))
    _active_rooms[room_name] = task

    # Cleanup when done
    def on_done(t: asyncio.Task):
        _active_rooms.pop(room_name, None)
        if t.exception():
            logger.error("Pipeline for room %s failed: %s", room_name, t.exception())

    task.add_done_callback(on_done)


async def _room_agent(room_name: str, chat_id: str):
    """Join a LiveKit room and orchestrate walkie-talkie translation turns."""
    agent_token = _generate_agent_token(room_name)
    livekit_url = settings.livekit_url
    room = rtc.Room()

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
    recording_speaker_id: str | None = None
    audio_stream: rtc.AudioStream | None = None
    recording_active = asyncio.Event()

    async def _publish_signal(signal: Signal, **kwargs):
        payload = encode_signal(signal, **kwargs)
        await room.local_participant.publish_data(
            payload, reliable=True, topic=TOPIC
        )

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        logger.debug("Audio track available for %s", participant.identity)

    @room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        nonlocal recording_speaker_id, audio_stream
        if data_packet.topic != TOPIC:
            return
        sig, payload = decode_signal(data_packet.data.decode("utf-8"))

        if sig == Signal.RECORDING_START:
            speaker_id = payload.get("userId")
            if speaker_id and speaker_id in members:
                recording_speaker_id = speaker_id
                for participant in room.remote_participants.values():
                    if participant.identity == speaker_id:
                        for pub in participant.track_publications.values():
                            if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                                audio_stream = rtc.AudioStream(pub.track)
                                break
                        break
                if audio_stream:
                    recording_active.set()
                    logger.info("Recording started for %s", speaker_id)
                else:
                    recording_speaker_id = None
                    logger.warning("No audio track found for %s, ignoring RECORDING_START", speaker_id)

        elif sig == Signal.RECORDING_STOP:
            recording_active.clear()
            logger.info("Recording stopped for %s", payload.get("userId"))

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        nonlocal recording_speaker_id
        if participant.identity == recording_speaker_id:
            recording_active.clear()
            recording_speaker_id = None

    try:
        await room.connect(livekit_url, agent_token)
        logger.info("Translation agent joined room %s", room_name)

        while not stop_event.is_set():
            try:
                await asyncio.wait_for(recording_active.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                if len(room.remote_participants) == 0:
                    await asyncio.sleep(5)
                    if len(room.remote_participants) == 0:
                        break
                continue

            speaker_id = recording_speaker_id
            if not speaker_id or not audio_stream:
                recording_active.clear()
                continue

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

            recording_speaker_id = None
            audio_stream = None

    finally:
        stop_event.set()
        await room.disconnect()
        logger.info("Translation agent left room %s", room_name)


async def _run_walkie_talkie_turn(
    room: rtc.Room,
    audio_stream: rtc.AudioStream,
    speaker_id: str,
    members: dict[str, dict],
    recording_active: asyncio.Event,
    publish_signal,
    stop_event: asyncio.Event,
):
    """Execute one walkie-talkie turn: collect audio -> STT -> translate -> TTS."""
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

        await sender
        try:
            await asyncio.wait_for(receiver, timeout=5.0)
        except asyncio.TimeoutError:
            receiver.cancel()

    full_transcript = " ".join(transcript_parts)
    if not full_transcript:
        await publish_signal(Signal.TTS_COMPLETE)
        return

    await publish_signal(Signal.PROCESSING)

    loop = asyncio.get_running_loop()
    translated = await loop.run_in_executor(
        None, translate_text, full_transcript, source_lang, target_lang
    )

    await publish_signal(
        Signal.TTS_PLAYING,
        original_text=full_transcript,
        translated_text=translated,
    )
    await _tts_and_publish(translated, room, speaker_id)

    await publish_signal(Signal.TTS_COMPLETE)


async def _tts_and_publish(text: str, room: rtc.Room, speaker_id: str):
    """Synthesize text via ElevenLabs TTS and publish audio to the LiveKit room."""
    voice_id = settings.elevenlabs_tts_voice_id
    model_id = settings.elevenlabs_tts_model
    tts_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
        f"?model_id={model_id}"
    )
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with websockets.connect(tts_url, additional_headers=headers) as tts_ws:
            # Initialize with voice settings
            await tts_ws.send(json.dumps({
                "text": " ",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            }))

            # Send translated text
            await tts_ws.send(json.dumps({"text": text, "flush": True}))

            # Close text stream
            await tts_ws.send(json.dumps({"text": ""}))

            # Collect and publish audio chunks
            audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
            track = rtc.LocalAudioTrack.create_audio_track(
                f"translated-{speaker_id}", audio_source
            )
            publication = await room.local_participant.publish_track(track)

            async for message in tts_ws:
                data = json.loads(message)
                audio_b64 = data.get("audio")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    frame = rtc.AudioFrame(
                        data=audio_bytes,
                        sample_rate=24000,
                        num_channels=1,
                        samples_per_channel=len(audio_bytes) // 2,
                    )
                    await audio_source.capture_frame(frame)

                if data.get("isFinal"):
                    break

            await room.local_participant.unpublish_track(publication.sid)

    except Exception:
        logger.exception("TTS synthesis/publish error for speaker %s", speaker_id)
