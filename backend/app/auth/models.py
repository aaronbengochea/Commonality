from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    native_language: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    username: str
    first_name: str
    last_name: str
    native_language: str
