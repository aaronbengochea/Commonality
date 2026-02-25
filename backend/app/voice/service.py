import array
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
    # When RECORDING_START arrives before the audio track, store the pending speaker ID
    pending_speaker_id: str | None = None

    async def _publish_signal(signal: Signal, **kwargs):
        payload = encode_signal(signal, **kwargs)
        await room.local_participant.publish_data(
            payload, reliable=True, topic=TOPIC
        )

    def _try_attach_audio(speaker_id: str) -> bool:
        """Try to find and attach an audio stream for the given speaker. Returns True if successful."""
        nonlocal recording_speaker_id, audio_stream, pending_speaker_id
        for participant in room.remote_participants.values():
            if participant.identity == speaker_id:
                for pub in participant.track_publications.values():
                    if pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                        audio_stream = rtc.AudioStream(pub.track)
                        recording_speaker_id = speaker_id
                        pending_speaker_id = None
                        recording_active.set()
                        logger.info("Recording started for %s", speaker_id)
                        return True
                break
        return False

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        nonlocal pending_speaker_id
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return
        logger.debug("Audio track available for %s", participant.identity)
        # If we were waiting for this speaker's track, attach it now
        if pending_speaker_id and participant.identity == pending_speaker_id:
            _try_attach_audio(pending_speaker_id)

    @room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        nonlocal recording_speaker_id, audio_stream, pending_speaker_id
        if data_packet.topic != TOPIC:
            return
        sig, payload = decode_signal(data_packet.data.decode("utf-8"))

        if sig == Signal.RECORDING_START:
            speaker_id = payload.get("userId")
            if speaker_id and speaker_id in members:
                if not _try_attach_audio(speaker_id):
                    # Track not available yet — wait for track_subscribed to fire
                    pending_speaker_id = speaker_id
                    logger.info("Audio track not yet available for %s, waiting for subscription...", speaker_id)

        elif sig == Signal.RECORDING_STOP:
            pending_speaker_id = None
            recording_active.clear()
            logger.info("Recording stopped for %s", payload.get("userId"))

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        nonlocal recording_speaker_id, pending_speaker_id
        if participant.identity == recording_speaker_id:
            recording_active.clear()
            recording_speaker_id = None
        if participant.identity == pending_speaker_id:
            pending_speaker_id = None

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
            pending_speaker_id = None

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
    logger.info("=== WALKIE-TALKIE TURN START for speaker=%s ===", speaker_id)

    speaker = members[speaker_id]
    listener_id = next((uid for uid in members if uid != speaker_id), None)
    if not listener_id:
        logger.warning("No listener found for speaker=%s, aborting turn", speaker_id)
        return
    listener = members[listener_id]

    source_lang = speaker.get("nativeLanguage", "en")
    target_lang = listener.get("nativeLanguage", "en")
    logger.info("Languages: source=%s (%s) -> target=%s (%s)",
                source_lang, speaker.get("username"), target_lang, listener.get("username"))

    if source_lang == target_lang:
        logger.info("Same language (%s), skipping translation", source_lang)
        await publish_signal(Signal.TTS_COMPLETE)
        return

    stt_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime"
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    transcript_parts: list[str] = []
    audio_frame_count = 0
    # Event to signal that we got a committed transcript after our final commit
    stt_done = asyncio.Event()

    async with websockets.connect(stt_url, additional_headers=headers) as stt_ws:
        logger.info("[1/4] STT WebSocket connected to ElevenLabs")

        async def send_audio():
            nonlocal audio_frame_count
            first_frame_logged = False
            async for event in audio_stream:
                if not recording_active.is_set() or stop_event.is_set():
                    break
                if isinstance(event, rtc.AudioFrameEvent):
                    audio_frame_count += 1
                    pcm_data = event.frame.data.tobytes()
                    src_rate = event.frame.sample_rate

                    # Downsample to 16kHz for ElevenLabs STT
                    if src_rate != 16000 and src_rate % 16000 == 0:
                        factor = src_rate // 16000
                        samples = array.array("h", pcm_data)
                        downsampled = samples[::factor]
                        pcm_data = downsampled.tobytes()

                    if not first_frame_logged:
                        logger.info(
                            "[1/4] First audio frame: src_rate=%d, num_channels=%d, "
                            "samples_per_channel=%d, pcm_bytes_after_resample=%d",
                            src_rate,
                            event.frame.num_channels,
                            event.frame.samples_per_channel,
                            len(pcm_data),
                        )
                        first_frame_logged = True

                    audio_b64 = base64.b64encode(pcm_data).decode("utf-8")
                    await stt_ws.send(json.dumps({
                        "message_type": "input_audio_chunk",
                        "audio_base_64": audio_b64,
                        "commit": False,
                        "sample_rate": 16000,
                    }))

            logger.info("[1/4] Audio send complete: %d frames sent to STT", audio_frame_count)
            try:
                await stt_ws.send(json.dumps({
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "commit": True,
                    "sample_rate": 16000,
                }))
                logger.info("[1/4] Final STT commit sent")
            except Exception:
                logger.debug("Could not send final STT commit")

        async def receive_transcripts():
            commit_received = False
            async for message in stt_ws:
                data = json.loads(message)
                msg_type = data.get("message_type")
                logger.info("[2/4] STT << %s: %s", msg_type, json.dumps(data)[:300])
                if msg_type == "committed_transcript":
                    text = data.get("text", "").strip()
                    if text:
                        transcript_parts.append(text)
                        logger.info("[2/4] STT transcript chunk: '%s'", text)
                    commit_received = True
                    stt_done.set()
                elif msg_type == "input_error":
                    logger.warning("[2/4] STT error for %s: %s", speaker_id, data.get("message"))
                    stt_done.set()

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_transcripts())

        await sender
        # Wait for committed transcript (fast path) or timeout (fallback)
        try:
            await asyncio.wait_for(stt_done.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("[2/4] STT receive timed out after 5s")
        receiver.cancel()

    has_audio = audio_frame_count > 0
    full_transcript = " ".join(transcript_parts)
    logger.info("[2/4] STT RESULT: has_audio=%s, frame_count=%d, transcript='%s'",
                has_audio, audio_frame_count, full_transcript if full_transcript else "(empty)")

    if not full_transcript:
        logger.warning("[2/4] Empty transcript — no speech detected. Ending turn.")
        await publish_signal(Signal.TTS_COMPLETE)
        return

    await publish_signal(Signal.PROCESSING)

    logger.info("[3/4] Sending to OpenAI for translation: '%s' (%s -> %s)",
                full_transcript, source_lang, target_lang)
    loop = asyncio.get_running_loop()
    translated = await loop.run_in_executor(
        None, translate_text, full_transcript, source_lang, target_lang
    )
    logger.info("[3/4] TRANSLATION RESULT: '%s'", translated)

    await publish_signal(
        Signal.TTS_PLAYING,
        original_text=full_transcript,
        translated_text=translated,
    )

    logger.info("[4/4] Starting TTS synthesis for: '%s'", translated)
    await _tts_and_publish(translated, room, speaker_id)
    logger.info("[4/4] TTS complete")

    await publish_signal(Signal.TTS_COMPLETE)
    logger.info("=== WALKIE-TALKIE TURN COMPLETE for speaker=%s ===", speaker_id)


async def _tts_and_publish(text: str, room: rtc.Room, speaker_id: str):
    """Synthesize text via ElevenLabs TTS and publish audio to the LiveKit room."""
    voice_id = settings.elevenlabs_tts_voice_id
    model_id = settings.elevenlabs_tts_model
    tts_url = (
        f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
        f"?model_id={model_id}&output_format=pcm_24000"
    )
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with websockets.connect(tts_url, additional_headers=headers) as tts_ws:
            logger.info("[4/4] TTS WebSocket connected to ElevenLabs (voice=%s, model=%s)", voice_id, model_id)

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
            logger.info("[4/4] TTS audio track published to LiveKit room (sid=%s)", publication.sid)

            tts_chunk_count = 0
            async for message in tts_ws:
                data = json.loads(message)
                audio_b64 = data.get("audio")
                if audio_b64:
                    tts_chunk_count += 1
                    audio_bytes = base64.b64decode(audio_b64)
                    # Ensure byte length is a multiple of 2 (int16 samples)
                    if len(audio_bytes) % 2 != 0:
                        audio_bytes = audio_bytes + b"\x00"
                    frame = rtc.AudioFrame(
                        data=audio_bytes,
                        sample_rate=24000,
                        num_channels=1,
                        samples_per_channel=len(audio_bytes) // 2,
                    )
                    await audio_source.capture_frame(frame)

                if data.get("isFinal"):
                    break

            logger.info("[4/4] TTS playback done: %d audio chunks published", tts_chunk_count)
            # Wait for LiveKit to drain the audio buffer before unpublishing
            await asyncio.sleep(2.0)
            await room.local_participant.unpublish_track(publication.sid)

    except Exception:
        logger.exception("[4/4] TTS synthesis/publish error for speaker %s", speaker_id)
