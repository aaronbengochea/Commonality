# Demo Deployment Plan: ngrok Tunneling + LiveKit Cloud

> **Internal plan transcript:** `.claude/projects/-Users-aaronbengo-Documents-github-commonality/03b1bb67-c43f-43f5-aaeb-944ed712500c.jsonl`

---

## Overview

Expose the local docker-compose stack to the internet using ngrok tunnels. Everything runs on your machine — no cloud hosting, no AWS, no Redis migration. The only external service is **LiveKit Cloud** for reliable WebRTC voice calls (free tier).

### Architecture

| Service | Runs on | Exposed via |
|---|---|---|
| **Frontend** | Docker (localhost:3000) | ngrok tunnel |
| **Backend** | Docker (localhost:8080) | ngrok tunnel |
| **Database** | DynamoDB Local (Docker) | Not exposed (local only) |
| **Cache/Pub-sub** | Redis (Docker) | Not exposed (local only) |
| **Voice** | **LiveKit Cloud** | Direct (WSS URL) |

### Why This Approach

- **Zero code changes** to the backend or frontend
- **No cloud accounts** needed (except ngrok free tier + LiveKit Cloud free tier)
- Public URLs ready in under a minute
- Good enough for MVP demos with multiple users
- Can upgrade to full Vercel + Railway deployment later if needed

---

## Prerequisites

1. **ngrok** installed (`brew install ngrok` on macOS)
2. **ngrok account** (free tier at [ngrok.com](https://ngrok.com)) — needed for multiple simultaneous tunnels
3. **LiveKit Cloud account** (free tier at [livekit.io/cloud](https://livekit.io/cloud)) — needed for voice calls to work across networks

---

## Step 1: Set Up LiveKit Cloud (One-Time)

Local LiveKit only works on your machine. For voice calls between different users/devices, we need LiveKit Cloud.

1. Create account at [livekit.io/cloud](https://livekit.io/cloud)
2. Create a project
3. Copy three values:
   - **API Key** (e.g., `APIxxxxxxx`)
   - **API Secret** (e.g., `xxxxxxxxxxxxxxxx`)
   - **WSS URL** (e.g., `wss://your-project.livekit.cloud`)

Update your `.env` file:

```bash
LIVEKIT_API_KEY=your-livekit-cloud-api-key
LIVEKIT_API_SECRET=your-livekit-cloud-api-secret
LIVEKIT_URL=wss://your-project.livekit.cloud
```

---

## Step 2: Start the Local Stack

```bash
make up
```

Verify everything is running:
- Backend: http://localhost:8080/api/health → `{"status":"ok"}`
- Frontend: http://localhost:3000 → login page loads

> **Note:** The local LiveKit container still runs but won't be used — the backend now points to LiveKit Cloud via the `.env` change above.

---

## Step 3: Start ngrok Tunnels

Open two terminal tabs and start tunnels for frontend and backend:

**Terminal 1 — Backend tunnel:**
```bash
ngrok http 8080
```

**Terminal 2 — Frontend tunnel:**
```bash
ngrok http 3000
```

Note the HTTPS URLs ngrok gives you, e.g.:
- Backend: `https://abc123.ngrok-free.app`
- Frontend: `https://def456.ngrok-free.app`

> **Tip:** With a free ngrok account you can run multiple tunnels. If you hit limits, use a single `ngrok.yml` config file to start both at once (see appendix).

---

## Step 4: Update Environment Variables

Update your `.env` with the ngrok URLs:

```bash
# Frontend env vars (used at build time by Next.js)
NEXT_PUBLIC_API_URL=https://abc123.ngrok-free.app
NEXT_PUBLIC_WS_URL=wss://abc123.ngrok-free.app
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud

# Backend CORS (allow the frontend tunnel)
CORS_ORIGINS=https://def456.ngrok-free.app
```

Then rebuild and restart the frontend (it needs to rebake the `NEXT_PUBLIC_*` vars):

```bash
docker compose up -d --build frontend
```

The backend picks up `CORS_ORIGINS` on restart:

```bash
docker compose restart backend
```

---

## Step 5: Verify

1. Open the **frontend ngrok URL** (e.g., `https://def456.ngrok-free.app`) in a browser
2. Register a user, log in → chat list loads
3. Open a **second browser** (or incognito window) → register a second user
4. Start a chat between them → send messages, verify real-time delivery
5. Click Call → verify LiveKit Cloud connects and mic permission is requested
6. Speak → verify voice translation pipeline works

---

## Sharing with Others

Send the **frontend ngrok URL** to anyone you want to demo with. They can:
- Open it on any device (phone, laptop, different network)
- Register their own account
- Chat and call with you in real time

---

## Limitations

| Limitation | Details |
|---|---|
| **ngrok URLs change** | Free tier gives random URLs on each restart. You'll need to update `.env` and rebuild frontend each time. A paid ngrok plan gives stable subdomains. |
| **Your machine must be on** | Everything runs locally — if your laptop sleeps or loses internet, the demo goes down |
| **ngrok free tier bandwidth** | Sufficient for demos, not for sustained multi-user load |
| **WebSocket through ngrok** | Works well for text chat; occasional latency spikes possible |

---

## Appendix: ngrok Config for Both Tunnels at Once

Create `~/.ngrok2/ngrok.yml` (or add to existing):

```yaml
tunnels:
  backend:
    addr: 8080
    proto: http
  frontend:
    addr: 3000
    proto: http
```

Then start both with:

```bash
ngrok start --all
```

---

## Future: Full Production Deployment

When ready to move beyond demo tunneling, the production path is:

| Service | Platform |
|---|---|
| Frontend | Vercel |
| Backend | Railway |
| Database | AWS DynamoDB (PAY_PER_REQUEST) |
| Cache/Pub-sub | Upstash Redis |
| Voice | LiveKit Cloud |

This requires code changes (optional DynamoDB endpoint, production Dockerfile, on-demand billing). A full production deployment plan can be written when needed.
