from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.dynamo import create_tables
from app.dependencies import close_redis, get_redis_client
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.chat.websocket import router as chat_ws_router
from app.voice.router import router as voice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    await get_redis_client()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(title="Commonality", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api/chats", tags=["chat"])
app.include_router(chat_ws_router, prefix="/api/ws", tags=["chat-ws"])
app.include_router(voice_router, prefix="/api/voice", tags=["voice"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
