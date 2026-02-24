# Commonality

Real-time translation chat and voice app. Users communicate in their native language; messages and speech are automatically translated.

## Tech Stack

- **Backend:** Python 3.12 + FastAPI (single monolith service)
- **Frontend:** Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Database:** DynamoDB Local (Docker)
- **Cache/Pub-sub:** Redis 7
- **Chat transport:** WebSockets (FastAPI native)
- **Text translation:** OpenAI API
- **Voice rooms:** LiveKit
- **Voice STT:** ElevenLabs Scribe v2 (realtime WS)
- **Voice TTS:** ElevenLabs TTS (streaming WS)

## Project Structure

- `backend/` — FastAPI app in `backend/app/`, tests in `backend/tests/`
- `frontend/` — Next.js app in `frontend/src/`
- `docker-compose.yml` — 5 services: backend, frontend, dynamodb-local, redis, livekit

## Running

```bash
cp .env.example .env  # fill in API keys
docker compose up --build
```

- Backend: http://localhost:8080
- Frontend: http://localhost:3000

## Backend Conventions

- Config via pydantic-settings (`app/config.py`)
- DynamoDB tables: users, chats, user_chats, messages (see docs/plans/mvpPlan.md for schema)
- Auth: JWT tokens, argon2 password hashing
- API prefix: `/api/`
- Tests: `pytest` with `pytest-asyncio`

## Frontend Conventions

- App Router (`src/app/`)
- Components in `src/components/`
- Hooks in `src/hooks/`
- API client in `src/lib/api.ts`
- WebSocket manager in `src/lib/ws.ts`
- Types in `src/types/index.ts`

## Key Patterns

- **Chat dual-write:** Each message stored per-user in their language (sender gets original, recipient gets translation)
- **Voice pipeline:** STT → translate → TTS, only on committed/final STT segments
