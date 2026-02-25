# Commonality

Real-time translation chat and voice app. Communicate in your native language — messages and speech are automatically translated so every participant sees and hears everything in their own language.

## Features

- **Text chat** with automatic translation between any supported language pair
- **Voice calls** with real-time speech-to-text, translation, and text-to-speech
- **1:1 conversations** — each user's message history is stored natively in their language

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript, Tailwind CSS) |
| Backend | Python 3.12 + FastAPI |
| Database | DynamoDB (Local for dev, AWS for production) |
| Cache / Pub-sub | Redis 7 |
| Chat transport | WebSockets |
| Text translation | OpenAI API |
| Voice rooms | LiveKit |
| Voice STT | ElevenLabs Scribe v2 |
| Voice TTS | ElevenLabs TTS |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- API keys for OpenAI, ElevenLabs (optional for text-only dev)

### Setup

```bash
cp .env.example .env
# Fill in your API keys in .env

docker compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8080
- **DynamoDB Admin:** http://localhost:8001

### Makefile Commands

```bash
make up        # Start all services
make down      # Stop all services
make build     # Rebuild images (no cache)
make logs      # Tail all service logs
make test      # Run backend tests
make lint      # Run linters
```

## Project Structure

```
commonality/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── dependencies.py   # DynamoDB + Redis clients
│   │   ├── auth/             # Signup, login, JWT
│   │   ├── chat/             # REST + WebSocket chat
│   │   ├── voice/            # LiveKit tokens + STT/TTS pipeline
│   │   └── db/               # DynamoDB table setup
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks (auth, WebSocket)
│   │   ├── lib/              # API client, WebSocket manager
│   │   └── types/            # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml        # 5 services: backend, frontend, dynamodb, redis, livekit
├── Makefile
└── .env.example
```

## How It Works

### Text Chat

1. User A sends a message via WebSocket
2. Backend stores the original message for User A
3. Backend translates the text (via OpenAI) into User B's language
4. Backend stores the translated message for User B
5. User B receives the translated message in real time

### Voice Calls

1. Users join a LiveKit room
2. Audio is streamed to ElevenLabs STT for transcription
3. Committed transcript segments are translated via OpenAI
4. Translated text is sent to ElevenLabs TTS
5. Synthesized audio is played to the other participant

## Deployment

See [docs/deploymentPlan.md](docs/deploymentPlan.md) for the full production deployment guide using Vercel (frontend), Railway (backend), AWS DynamoDB, Upstash Redis, and LiveKit Cloud.

## License

Private — all rights reserved.
