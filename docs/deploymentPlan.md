# Production Deployment Plan: Vercel + Railway + Managed Services

> **Internal plan transcript:** `.claude/projects/-Users-aaronbengo-Documents-github-commonality/03b1bb67-c43f-43f5-aaeb-944ed712500c.jsonl`

---

## Overview

The app currently runs entirely via docker-compose locally (backend, frontend, DynamoDB Local, Redis, LiveKit). To test features like voice calling with multiple users and to make the app accessible, we need a production deployment.

### Target Stack

| Service | Local (docker-compose) | Production |
|---|---|---|
| **Frontend** | Docker / Next.js dev server | **Vercel** (native Next.js support) |
| **Backend** | Docker / Uvicorn with reload | **Railway** (container hosting with WebSocket support) |
| **Database** | DynamoDB Local (Docker) | **AWS DynamoDB** (managed) |
| **Cache/Pub-sub** | Redis 7 (Docker) | **Upstash Redis** (serverless, TLS) |
| **Voice** | LiveKit self-hosted (Docker) | **LiveKit Cloud** (managed) |

---

## Commit 1: Production-Ready Backend

### 1a. Make `dynamodb_endpoint` optional

**File:** `backend/app/config.py` (line 25)

Change `dynamodb_endpoint: str = "http://dynamodb-local:8000"` to `dynamodb_endpoint: str | None = None`.

- Local dev sets it via `.env`
- Production leaves it unset so boto3 uses the default AWS endpoint

### 1b. Conditionally pass `endpoint_url` to boto3

**File:** `backend/app/dependencies.py` (lines 12-20)

Build a `kwargs` dict and only include `endpoint_url` when `settings.dynamodb_endpoint` is not None:

```python
kwargs = {
    "region_name": settings.aws_region,
    "aws_access_key_id": settings.aws_access_key_id,
    "aws_secret_access_key": settings.aws_secret_access_key,
}
if settings.dynamodb_endpoint:
    kwargs["endpoint_url"] = settings.dynamodb_endpoint
_dynamo_client = boto3.resource("dynamodb", **kwargs)
```

### 1c. Use on-demand billing for DynamoDB in production

**File:** `backend/app/db/dynamo.py` (lines 89-103)

In `create_tables()`, when `ENVIRONMENT != "development"`, strip `ProvisionedThroughput` from table defs and GSIs, add `BillingMode: "PAY_PER_REQUEST"`.

The existing `ResourceInUseException` catch handles repeated startups gracefully.

### 1d. Production Dockerfile

**File:** `backend/Dockerfile`

Replace current dev Dockerfile:
- `pip install .` instead of `".[dev]"` (no test deps in production)
- Remove `--reload` flag
- Use `--workers 1` (WebSocket connections are stateful; Railway scales at container level)

### 1e. Create `.dockerignore`

**File (new):** `backend/.dockerignore`

Exclude: `__pycache__`, `*.pyc`, `.pytest_cache`, `.venv`, `.env`, `tests/`, `.git`

### 1f. Update `.env.example`

**File:** `.env.example`

Add `DYNAMODB_ENDPOINT=http://dynamodb-local:8000` with a comment that it should be **omitted** for production. Add `ENVIRONMENT` guidance.

---

## Commit 2: Update `docker-compose.yml` for Local Dev Parity

Ensure `docker-compose.yml` passes `DYNAMODB_ENDPOINT=http://dynamodb-local:8000` to the backend service explicitly, so local dev keeps working after the `config.py` default changed to `None`.

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `backend/app/config.py` | `dynamodb_endpoint` → `str \| None = None` |
| `backend/app/dependencies.py` | Conditionally pass `endpoint_url` |
| `backend/app/db/dynamo.py` | `PAY_PER_REQUEST` billing in production |
| `backend/Dockerfile` | Production-ready (no reload, no dev deps) |
| `backend/.dockerignore` | New file |
| `.env.example` | Add production guidance comments |
| `docker-compose.yml` | Pass `DYNAMODB_ENDPOINT` explicitly to backend |

---

## External Service Setup (Manual, Not Code)

### AWS DynamoDB

1. Create IAM user `commonality-backend` with DynamoDB permissions on tables: `users`, `chats`, `user_chats`, `messages`
2. Generate access key + secret key
3. Tables auto-create on first Railway startup via `create_tables()`

### Upstash Redis

1. Create account at [upstash.com](https://upstash.com)
2. Create Redis database (region near Railway)
3. Copy the `rediss://` URL — existing `redis.from_url()` handles TLS natively

### LiveKit Cloud

1. Create account at [livekit.io/cloud](https://livekit.io/cloud)
2. Create project → get API key, secret, and WSS URL (`wss://YOUR_PROJECT.livekit.cloud`)

---

## Railway Deployment (Backend)

1. Create Railway project, connect GitHub repo
2. Set **root directory** to `backend`
3. Railway auto-detects Dockerfile
4. Set health check path: `/api/health`
5. Configure environment variables:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `OPENAI_API_KEY` | *(your key)* |
| `OPENAI_TRANSLATION_MODEL` | `gpt-4o-mini` |
| `ELEVENLABS_API_KEY` | *(your key)* |
| `ELEVENLABS_TTS_VOICE_ID` | `Xb7hH8MSUJpSbSDYk0k2` |
| `ELEVENLABS_TTS_MODEL` | `eleven_flash_v2_5` |
| `LIVEKIT_API_KEY` | *(from LiveKit Cloud)* |
| `LIVEKIT_API_SECRET` | *(from LiveKit Cloud)* |
| `LIVEKIT_URL` | `wss://YOUR_PROJECT.livekit.cloud` |
| `AWS_REGION` | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | *(from IAM user)* |
| `AWS_SECRET_ACCESS_KEY` | *(from IAM user)* |
| `REDIS_URL` | `rediss://...` *(from Upstash)* |
| `JWT_SECRET` | *(generate via `openssl rand -base64 32`)* |
| `BACKEND_PORT` | `8080` |
| `PORT` | `8080` |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` |

> **Do NOT set `DYNAMODB_ENDPOINT`** — omitting it makes boto3 use standard AWS endpoints.

---

## Vercel Deployment (Frontend)

1. Import repo on Vercel, set **root directory** to `frontend`
2. Vercel auto-detects Next.js (already has `output: "standalone"`)
3. Configure environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-DOMAIN.up.railway.app` |
| `NEXT_PUBLIC_WS_URL` | `wss://YOUR-RAILWAY-DOMAIN.up.railway.app` |
| `NEXT_PUBLIC_LIVEKIT_URL` | `wss://YOUR_PROJECT.livekit.cloud` |
| `NEXT_PUBLIC_PASSWORD_MIN_LENGTH` | `8` |

> **Note:** `NEXT_PUBLIC_` vars are baked at build time. Changing the Railway domain requires a Vercel redeploy.

---

## Verification Checklist

1. `make up` locally — confirm local dev still works (DynamoDB Local, Redis, etc.)
2. Deploy backend to Railway → `curl https://RAILWAY_DOMAIN/api/health` returns `{"status":"ok"}`
3. Check AWS Console → 4 DynamoDB tables created
4. Deploy frontend to Vercel → login page loads
5. Register a user, log in → chat list loads
6. Open two browser tabs as different users → send messages, verify real-time delivery
7. Click Call → verify LiveKit Cloud connects and requests mic permission
