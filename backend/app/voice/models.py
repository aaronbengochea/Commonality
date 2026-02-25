from pydantic import BaseModel


class VoiceTokenRequest(BaseModel):
    chat_id: str


class VoiceTokenResponse(BaseModel):
    token: str
    room_name: str
