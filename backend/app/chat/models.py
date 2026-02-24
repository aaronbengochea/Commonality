from pydantic import BaseModel


class CreateChatRequest(BaseModel):
    username: str


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
