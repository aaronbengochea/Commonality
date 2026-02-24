from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # LiveKit
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "devsecret"
    livekit_url: str = "ws://livekit:7880"

    # ElevenLabs
    elevenlabs_api_key: str = ""

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

    # Server
    backend_port: int = 8080

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
