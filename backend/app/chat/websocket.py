import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth.service import decode_access_token, get_user_by_id
from app.chat.service import get_chat_meta, send_message
from app.db.redis import publish, subscribe

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory map of user_id -> set of active WebSocket connections
_connections: dict[str, set[WebSocket]] = {}
# Single Redis listener task per user (shared across all their connections)
_listener_tasks: dict[str, asyncio.Task] = {}


def _register(user_id: str, ws: WebSocket):
    _connections.setdefault(user_id, set()).add(ws)


def _unregister(user_id: str, ws: WebSocket):
    if user_id in _connections:
        _connections[user_id].discard(ws)
        if not _connections[user_id]:
            del _connections[user_id]


async def _deliver_to_local(user_id: str, payload: str):
    """Send a message to all local WebSocket connections for a user."""
    for ws in list(_connections.get(user_id, [])):
        try:
            await ws.send_text(payload)
        except Exception:
            _unregister(user_id, ws)


async def _redis_listener(user_id: str):
    """Listen on a Redis pub/sub channel for messages targeting this user.
    Delivers to all local WebSocket connections for the user."""
    pubsub = await subscribe(f"user:{user_id}:messages")
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg["type"] == "message":
                logger.info("Redis listener received message for user %s", user_id)
                await _deliver_to_local(user_id, msg["data"])
            else:
                await asyncio.sleep(0.05)
    finally:
        await pubsub.unsubscribe(f"user:{user_id}:messages")
        await pubsub.close()


def _authenticate(websocket: WebSocket) -> dict | None:
    """Validate JWT from query param and return user dict, or None."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = get_user_by_id(user_id)
        if user:
            user.pop("passwordHash", None)
        return user
    except Exception:
        return None


@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket):
    # Accept first, then authenticate (WebSocket lifecycle requires accept before close)
    await websocket.accept()

    user = _authenticate(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user["userId"]
    _register(user_id, websocket)

    # Start a single Redis listener per user (shared across tabs)
    if user_id not in _listener_tasks or _listener_tasks[user_id].done():
        _listener_tasks[user_id] = asyncio.create_task(_redis_listener(user_id))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            chat_id = data.get("chat_id")
            text = data.get("text", "").strip()

            if not chat_id or not text:
                await websocket.send_text(json.dumps({"error": "chat_id and text are required"}))
                continue

            # Verify membership
            chat_meta = get_chat_meta(chat_id)
            if not chat_meta or user_id not in chat_meta.get("memberUserIds", []):
                await websocket.send_text(json.dumps({"error": "Not a member of this chat"}))
                continue

            # Identify the other user
            other_user_id = next(
                (uid for uid in chat_meta["memberUserIds"] if uid != user_id),
                None,
            )
            if not other_user_id:
                continue

            other_user = get_user_by_id(other_user_id)
            if not other_user:
                continue

            # Dual-write message (translate + store) with error handling
            # Run in executor to avoid blocking the event loop with synchronous DynamoDB/OpenAI calls
            try:
                loop = asyncio.get_event_loop()
                sender_msg, recipient_msg = await loop.run_in_executor(
                    None, send_message, chat_id, user, other_user, text
                )
            except Exception:
                logger.exception("Failed to send message in chat %s", chat_id)
                await websocket.send_text(json.dumps({"error": "Failed to send message"}))
                continue

            # Build payloads from the already-written records
            sender_payload = json.dumps({
                "type": "message",
                "chat_id": chat_id,
                "message": {
                    "message_id": sender_msg["messageId"],
                    "text": sender_msg["text"],
                    "from_user_id": user_id,
                    "language": sender_msg["language"],
                    "timestamp": sender_msg["timestamp"],
                },
            })

            recipient_payload = json.dumps({
                "type": "message",
                "chat_id": chat_id,
                "message": {
                    "message_id": recipient_msg["messageId"],
                    "text": recipient_msg["text"],
                    "from_user_id": user_id,
                    "language": recipient_msg["language"],
                    "timestamp": recipient_msg["timestamp"],
                },
            })

            # Deliver to sender via local connection
            logger.info("Delivering message to sender %s locally", user_id)
            await _deliver_to_local(user_id, sender_payload)

            # Deliver to recipient via Redis pub/sub (works across instances)
            logger.info("Publishing message to recipient %s via Redis", other_user_id)
            await publish(f"user:{other_user_id}:messages", recipient_payload)

    except WebSocketDisconnect:
        pass
    finally:
        _unregister(user_id, websocket)
        # Only cancel the Redis listener when the last connection for this user disconnects
        if user_id not in _connections and user_id in _listener_tasks:
            _listener_tasks.pop(user_id).cancel()
