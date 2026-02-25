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
    """Join a LiveKit room as a server-side agent and run translation pipelines
    for each participant's audio track."""
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

    pipeline_tasks: dict[str, asyncio.Task] = {}
    stop_event = asyncio.Event()

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return

        speaker_id = participant.identity
        if speaker_id not in members or speaker_id in pipeline_tasks:
            return

        speaker = members[speaker_id]
        # Find the other participant
        listener_id = next((uid for uid in members if uid != speaker_id), None)
        if not listener_id:
            return
        listener = members[listener_id]

        source_lang = speaker.get("nativeLanguage", "en")
        target_lang = listener.get("nativeLanguage", "en")

        if source_lang == target_lang:
            return  # No translation needed

        # Start pipeline for this speaker's audio
        audio_stream = rtc.AudioStream(track)
        task = asyncio.create_task(
            _participant_pipeline(
                audio_stream, room, speaker_id, source_lang, target_lang, stop_event
            )
        )
        pipeline_tasks[speaker_id] = task

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        task = pipeline_tasks.pop(participant.identity, None)
        if task:
            task.cancel()

    try:
        await room.connect(livekit_url, agent_token)
        logger.info("Translation agent joined room %s", room_name)

        # Stay alive until all participants leave or stop event
        while not stop_event.is_set():
            if len(room.remote_participants) == 0 and room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                # Wait a bit for participants to join
                await asyncio.sleep(5)
                if len(room.remote_participants) == 0:
                    break
            await asyncio.sleep(1)
    finally:
        stop_event.set()
        for task in pipeline_tasks.values():
            task.cancel()
        await room.disconnect()
        logger.info("Translation agent left room %s", room_name)


async def _participant_pipeline(
    audio_stream: rtc.AudioStream,
    room: rtc.Room,
    speaker_id: str,
    source_lang: str,
    target_lang: str,
    stop_event: asyncio.Event,
):
    """Run STT -> translate -> TTS for one participant's audio."""
    stt_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime"
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with websockets.connect(stt_url, additional_headers=headers) as stt_ws:
            async def send_audio():
                async for event in audio_stream:
                    if stop_event.is_set():
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

                # Send final commit
                try:
                    await stt_ws.send(json.dumps({
                        "message_type": "input_audio_chunk",
                        "audio_base_64": "",
                        "commit": True,
                        "sample_rate": 16000,
                    }))
                except Exception:
                    logger.debug("Could not send final STT commit")

            async def receive_and_synthesize():
                async for message in stt_ws:
                    if stop_event.is_set():
                        break
                    data = json.loads(message)
                    msg_type = data.get("message_type")

                    if msg_type == "committed_transcript":
                        text = data.get("text", "").strip()
                        if not text:
                            continue

                        # Translate in a thread to avoid blocking the event loop
                        loop = asyncio.get_event_loop()
                        translated = await loop.run_in_executor(
                            None, translate_text, text, source_lang, target_lang
                        )

                        # Synthesize and publish to room
                        await _tts_and_publish(translated, room, speaker_id)

                    elif msg_type == "input_error":
                        logger.warning("STT error for %s: %s", speaker_id, data.get("message"))

            sender = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(receive_and_synthesize())

            done, pending = await asyncio.wait(
                [sender, receiver], return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done:
                if task.exception():
                    logger.error("Pipeline task error for %s: %s", speaker_id, task.exception())

    except websockets.exceptions.ConnectionClosed:
        logger.warning("STT WebSocket closed for speaker %s", speaker_id)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Pipeline error for speaker %s", speaker_id)


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
