import logging
import os

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_translation_model: str = "gpt-4o-mini"

    # LiveKit
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret"
    livekit_url: str = "ws://livekit:7880"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_tts_voice_id: str = "Xb7hH8MSUJpSbSDYk0k2"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"

    # DynamoDB
    dynamodb_endpoint: str = "http://dynamodb-local:8000"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "local"
    aws_secret_access_key: str = "local"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440
    password_min_length: int = 8

    # Server
    backend_port: int = 8080
    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

if settings.jwt_secret == "change-me-in-production" and os.getenv("ENVIRONMENT", "development") != "development":
    raise RuntimeError("JWT_SECRET must be set to a secure value in non-development environments")
