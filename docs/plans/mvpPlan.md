# Commonality MVP — Implementation Plan

## Context

Commonality is a real-time translation chat and voice app. Users chat and call in their native language; messages and speech are automatically translated so each participant sees/hears everything in their own language. This plan covers the **initial MVP scaffold**: project structure, Docker Compose, backend + frontend skeleton, DynamoDB tables, auth, and the foundation for chat and voice features.

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js (App Router, TypeScript) |
| Database | DynamoDB Local (Docker) |
| Cache / Pub-sub | Redis 7 |
| Chat transport | WebSockets (FastAPI native) |
| Text translation | OpenAI API |
| Voice rooms | LiveKit |
| Voice STT | ElevenLabs Scribe v2 (realtime WS) |
| Voice TTS | ElevenLabs TTS (streaming WS) |
| Containerization | Docker + Docker Compose |
| Architecture | Monolith backend (single FastAPI service) |

## Project Structure

```
commonality/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings from env vars (pydantic-settings)
│   │   ├── dependencies.py      # Shared deps (DynamoDB client, Redis, etc.)
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # POST /signup, /login, GET /me
│   │   │   ├── service.py       # JWT creation, password hashing (argon2)
│   │   │   └── models.py        # Pydantic request/response schemas
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # REST: create chat, list chats, get messages
│   │   │   ├── websocket.py     # WS: real-time message send/receive
│   │   │   ├── service.py       # Translation + dual-write logic
│   │   │   └── models.py
│   │   ├── voice/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # REST: create room token
│   │   │   ├── service.py       # STT → translate → TTS pipeline
│   │   │   └── models.py
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── dynamo.py        # DynamoDB table creation + CRUD helpers
│   │       └── redis.py         # Redis client wrapper
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_chat.py
│       └── test_voice.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Landing / login
│   │   │   ├── signup/
│   │   │   │   └── page.tsx
│   │   │   ├── chat/
│   │   │   │   ├── page.tsx     # Chat list (inbox)
│   │   │   │   └── [chatId]/
│   │   │   │       └── page.tsx # Chat conversation
│   │   │   └── voice/
│   │   │       └── [roomId]/
│   │   │           └── page.tsx # Voice call room
│   │   ├── components/
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatList.tsx
│   │   │   └── VoiceRoom.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAuth.ts
│   │   ├── lib/
│   │   │   ├── api.ts           # HTTP client to backend
│   │   │   └── ws.ts            # WebSocket connection manager
│   │   └── types/
│   │       └── index.ts
│   └── public/
```

## Docker Compose Services

```yaml
services:
  backend:       # FastAPI on port 8080, hot-reload via volume mount
  frontend:      # Next.js on port 3000, hot-reload via volume mount
  dynamodb-local: # amazon/dynamodb-local on port 8000
  redis:         # redis:7-alpine on port 6379
  livekit:       # livekit/livekit-server on port 7880
```

All services on a shared Docker network. Backend connects to DynamoDB, Redis, and LiveKit by container hostname.

## DynamoDB Schema (4 separate tables)

### Table: `users`

| PK | SK | Attributes |
|---|---|---|
| `USER#{userId}` | `PROFILE` | username, firstName, lastName, nativeLanguage, passwordHash, createdAt |

**GSI1:** PK=`USERNAME#{username}`, SK=`PROFILE` — for login by username and uniqueness checks

### Table: `chats`

| PK | SK | Attributes |
|---|---|---|
| `CHAT#{chatId}` | `META` | memberUserIds (list), createdAt |

### Table: `user_chats`

| PK | SK | Attributes |
|---|---|---|
| `USER#{userId}` | `CHAT#{chatId}` | otherUsername, otherUserId, lastMessagePreview, updatedAt |

### Table: `messages`

| PK | SK | Attributes |
|---|---|---|
| `USER#{userId}#CHAT#{chatId}` | `MSG#{timestamp}#{msgId}` | text, fromUserId, originalMessageId, language |

## API Endpoints

### Auth
- `POST /api/auth/signup` — body: {username, password, firstName, lastName, nativeLanguage}
- `POST /api/auth/login` — body: {username, password} → returns JWT
- `GET /api/auth/me` — returns current user profile (requires JWT)

### Chat
- `POST /api/chats` — body: {username} → creates 1:1 chat, validates target user exists
- `GET /api/chats` — returns user's chat list (inbox)
- `GET /api/chats/{chatId}/messages?cursor=X&limit=N` — paginated message history (already localized)
- `WS /api/ws/chat` — WebSocket for real-time send/receive

### Voice
- `POST /api/voice/token` — body: {chatId} → returns LiveKit room token
- Voice translation pipeline runs server-side, coordinated through LiveKit room events

## Chat Message Flow (dual-write)

1. User A sends message via WebSocket
2. Backend stores original message for User A (in A's language)
3. Backend calls OpenAI to translate text from A's language → B's language
4. Backend stores translated message for User B (in B's language)
5. Backend pushes translated message to User B via WebSocket
6. Both users' message history is natively in their language

## Voice Translation Flow

1. User A speaks → LiveKit captures audio
2. Backend streams audio to ElevenLabs STT (realtime WebSocket)
3. On committed transcript segment: translate via OpenAI (A's lang → B's lang)
4. Send translated text to ElevenLabs TTS (streaming WebSocket)
5. Play synthesized audio to User B
6. Reverse pipeline for B → A

**Critical:** Only translate on committed/final STT segments, not partials.

## MVP Build Order

### Phase 1: Project Scaffold (this plan)
1. Create `.gitignore`, `CLAUDE.md`, `.env.example`
2. Create `docker-compose.yml` with all 5 services
3. Create backend `Dockerfile` + `pyproject.toml` with dependencies
4. Create frontend `Dockerfile` + `package.json` with dependencies
5. Create FastAPI app skeleton (`main.py`, `config.py`, `dependencies.py`)
6. Create Next.js app skeleton (layout, landing page)
7. Create DynamoDB table initialization script (`db/dynamo.py`)
8. Create Redis client wrapper (`db/redis.py`)
9. Verify `docker compose up` starts all services and they can communicate

### Phase 2: Auth
10. Implement signup endpoint (argon2 password hashing, DynamoDB write)
11. Implement login endpoint (JWT generation)
12. Implement auth middleware (JWT validation)
13. Implement `/me` endpoint
14. Frontend: signup + login pages with form validation

### Phase 3: Chat (text)
15. Implement create chat endpoint (validate target user, create chat + user_chats entries)
16. Implement list chats endpoint (inbox)
17. Implement WebSocket handler for real-time messaging
18. Implement translation service (OpenAI) + dual-write to messages table
19. Implement message history endpoint (paginated)
20. Frontend: chat list page, chat conversation page with WebSocket

### Phase 4: Voice
21. Implement LiveKit token generation endpoint
22. Implement STT → translate → TTS pipeline service
23. Frontend: voice room page with LiveKit React SDK
24. Wire up real-time voice translation in call

## Key Dependencies (Python)

- `fastapi`, `uvicorn[standard]` — web framework + ASGI server
- `boto3` — DynamoDB client
- `redis[hiredis]` — Redis client
- `pyjwt` — JWT encoding/decoding
- `argon2-cffi` — password hashing
- `openai` — translation via GPT
- `livekit-api` — LiveKit server SDK (token generation)
- `websockets` — for ElevenLabs STT/TTS WebSocket connections
- `pydantic-settings` — configuration management
- `httpx` — async HTTP client
- `pytest`, `pytest-asyncio` — testing

## Key Dependencies (Frontend)

- `next`, `react`, `react-dom` — framework
- `typescript` — type safety
- `tailwindcss` — styling
- `@livekit/components-react`, `livekit-client` — LiveKit React SDK
- `jose` — JWT decoding on client

## Environment Variables (.env.example)

```
# OpenAI
OPENAI_API_KEY=

# LiveKit
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
LIVEKIT_URL=ws://livekit:7880

# ElevenLabs
ELEVENLABS_API_KEY=

# DynamoDB
DYNAMODB_ENDPOINT=http://dynamodb-local:8000
BACKEND_PORT=8080
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=local
AWS_SECRET_ACCESS_KEY=local

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
```

## Verification

After scaffold is complete:
1. `docker compose up --build` — all 5 services start without errors
2. Backend health check: `curl http://localhost:8080/api/health` returns 200
3. Frontend loads: `http://localhost:3000` shows landing page
4. DynamoDB tables created: backend logs confirm 4 tables initialized
5. Redis connected: backend logs confirm Redis connection
