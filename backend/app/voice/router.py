from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.chat.service import get_chat_meta
from app.config import settings
from app.voice.models import VoiceTokenRequest, VoiceTokenResponse
from app.voice.service import generate_livekit_token

router = APIRouter()


@router.post("/token", response_model=VoiceTokenResponse)
async def create_voice_token(
    body: VoiceTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    # Verify chat exists and user is a member
    chat_meta = get_chat_meta(body.chat_id)
    if not chat_meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    if current_user["userId"] not in chat_meta.get("memberUserIds", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this chat")

    room_name = f"chat-{body.chat_id}"
    token = generate_livekit_token(
        user_id=current_user["userId"],
        username=current_user["username"],
        room_name=room_name,
    )

    return VoiceTokenResponse(
        token=token,
        room_name=room_name,
        livekit_url=settings.livekit_url,
    )
