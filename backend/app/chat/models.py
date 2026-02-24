from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    username: str = Field(min_length=1)


class ChatResponse(BaseModel):
    chat_id: str
    other_username: str
    other_user_id: str
    last_message_preview: str | None = None
    updated_at: str | None = None


class MessageResponse(BaseModel):
    message_id: str
    text: str
    from_user_id: str
    language: str
    timestamp: str


class MessagesPageResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: str | None = None
