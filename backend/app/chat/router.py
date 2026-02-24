from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.auth.service import get_user_by_username
from app.chat.models import ChatResponse, CreateChatRequest, MessagesPageResponse, MessageResponse
from app.chat.service import (
    create_chat,
    find_existing_chat,
    get_chat_meta,
    get_messages,
    list_user_chats,
)

router = APIRouter()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_endpoint(
    body: CreateChatRequest,
    current_user: dict = Depends(get_current_user),
):
    other_user = get_user_by_username(body.username)
    if not other_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if other_user["userId"] == current_user["userId"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create a chat with yourself")

    # Return existing chat if one already exists
    existing = find_existing_chat(current_user["userId"], other_user["userId"])
    if existing:
        return ChatResponse(
            chat_id=existing["chatId"],
            other_username=existing["otherUsername"],
            other_user_id=existing["otherUserId"],
            last_message_preview=existing.get("lastMessagePreview"),
            updated_at=existing.get("updatedAt"),
        )

    chat_id = create_chat(current_user, other_user)
    return ChatResponse(
        chat_id=chat_id,
        other_username=other_user["username"],
        other_user_id=other_user["userId"],
    )


@router.get("", response_model=list[ChatResponse])
async def list_chats_endpoint(current_user: dict = Depends(get_current_user)):
    items = list_user_chats(current_user["userId"])
    return [
        ChatResponse(
            chat_id=item["chatId"],
            other_username=item["otherUsername"],
            other_user_id=item["otherUserId"],
            last_message_preview=item.get("lastMessagePreview"),
            updated_at=item.get("updatedAt"),
        )
        for item in items
    ]


@router.get("/{chat_id}/messages", response_model=MessagesPageResponse)
async def get_messages_endpoint(
    chat_id: str,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    # Verify user is a member of this chat
    chat_meta = get_chat_meta(chat_id)
    if not chat_meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    if current_user["userId"] not in chat_meta.get("memberUserIds", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this chat")

    items, next_cursor = get_messages(current_user["userId"], chat_id, cursor, limit)
    messages = [
        MessageResponse(
            message_id=item["messageId"],
            text=item["text"],
            from_user_id=item["fromUserId"],
            language=item["language"],
            timestamp=item["timestamp"],
        )
        for item in items
    ]
    return MessagesPageResponse(messages=messages, next_cursor=next_cursor)
