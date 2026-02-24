# Commonality MVP — Phased Build Plan

## Phase 1: Project Scaffold ✅

1. ✅ Create `.gitignore`, `CLAUDE.md`, `.env.example`
2. ✅ Create `docker-compose.yml` with all 5 services
3. ✅ Create backend `Dockerfile` + `pyproject.toml` with dependencies
4. ✅ Create frontend `Dockerfile` + `package.json` with dependencies
5. ✅ Create FastAPI app skeleton (`main.py`, `config.py`, `dependencies.py`)
6. ✅ Create Next.js app skeleton (layout, landing page)
7. ✅ Create DynamoDB table initialization script (`db/dynamo.py`)
8. ✅ Create Redis client wrapper (`db/redis.py`)
9. ✅ Verify `docker compose up` starts all services and they can communicate

## Phase 2: Auth ✅

10. ✅ Implement signup endpoint (argon2 password hashing, DynamoDB write)
11. ✅ Implement login endpoint (JWT generation)
12. ✅ Implement auth middleware (JWT validation)
13. ✅ Implement `/me` endpoint
14. ✅ Frontend: signup + login pages with form validation

## Phase 3: Chat (text)

15. Implement create chat endpoint (validate target user, create chat + user_chats entries)
16. Implement list chats endpoint (inbox)
17. Implement WebSocket handler for real-time messaging
18. Implement translation service (OpenAI) + dual-write to messages table
19. Implement message history endpoint (paginated)
20. Frontend: chat list page, chat conversation page with WebSocket

## Phase 4: Voice

21. Implement LiveKit token generation endpoint
22. Implement STT → translate → TTS pipeline service
23. Frontend: voice room page with LiveKit React SDK
24. Wire up real-time voice translation in call
