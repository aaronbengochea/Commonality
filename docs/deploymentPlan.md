# Demo Deployment Plan: ngrok Tunneling + LiveKit Cloud

---

## Overview

Expose the local docker-compose stack to the internet using a single ngrok tunnel through an nginx reverse proxy. Everything runs on your machine — no cloud hosting, no AWS, no Redis migration. The only external service is **LiveKit Cloud** for reliable WebRTC voice calls (free tier).

### Architecture

| Service | Runs on | Exposed via |
|---|---|---|
| **nginx** | Docker (localhost:8888) | ngrok tunnel (single HTTPS URL) |
| **Frontend** | Docker (localhost:3000) | nginx proxy (path: `/*`) |
| **Backend** | Docker (localhost:8080) | nginx proxy (path: `/api/*`) |
| **Database** | DynamoDB Local (Docker) | Not exposed (local only) |
| **Cache/Pub-sub** | Redis (Docker) | Not exposed (local only) |
| **Voice** | **LiveKit Cloud** | Direct (WSS URL) |

nginx routes `/api/*` (including WebSocket upgrades for `/api/ws/*`) to the backend, and everything else to the frontend. This lets us use a **single ngrok tunnel** on the free tier.

### Why This Approach

- **Single ngrok tunnel** — works on the free tier (no paid plan needed)
- **Zero code changes** to the backend or frontend
- **No cloud accounts** needed (except ngrok free tier + LiveKit Cloud free tier)
- Public URL ready in under a minute
- Automated scripts to update `.env` and restart services
- Good enough for MVP demos with multiple users
- Can upgrade to full Vercel + Railway deployment later if needed

---

## Prerequisites

1. **ngrok** installed (`brew install ngrok` on macOS)
2. **ngrok account** (free tier at [ngrok.com](https://ngrok.com)) — authenticate with `ngrok config add-authtoken <token>`
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
- nginx: http://localhost:8888 → login page loads (proxied from frontend)

> **Note:** The local LiveKit container still runs but won't be used — the backend now points to LiveKit Cloud via the `.env` change above.

---

## Step 3: Start the ngrok Tunnel

In a separate terminal:

```bash
make tunnel
```

This runs `ngrok start --all`, which starts a single tunnel to port 8888 (nginx).

Note the HTTPS URL ngrok gives you, e.g.:
- `https://abc123.ngrok-free.app`

---

## Step 4: Update Environment & Restart

In your main terminal, run:

```bash
make tunnel-restart
```

This automatically:
1. Reads the tunnel URL from ngrok's local API
2. Updates `.env` with the correct `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, and `CORS_ORIGINS`
3. Rebuilds the frontend (to bake in the `NEXT_PUBLIC_*` vars)
4. Restarts the backend (to pick up new `CORS_ORIGINS`)
5. Ensures nginx is running

All three env vars point to the **same ngrok URL** since nginx handles the routing.

---

## Step 5: Verify

1. Open the **ngrok URL** (e.g., `https://abc123.ngrok-free.app`) in a browser
2. Register a user, log in → chat list loads
3. Open a **second browser** (or incognito window) → register a second user
4. Start a chat between them → send messages, verify real-time delivery
5. Click Call → verify LiveKit Cloud connects and mic permission is requested
6. Speak → verify voice translation pipeline works

---

## Quick Reference

```bash
# Full startup sequence:
make up                # Start docker stack
make tunnel            # Start ngrok (in separate terminal)
make tunnel-restart    # Auto-configure .env and restart services

# Individual commands:
make tunnel-env        # Just update .env from ngrok (no restart)
```

---

## Sharing with Others

Send the **ngrok URL** to anyone you want to demo with. They can:
- Open it on any device (phone, laptop, different network)
- Register their own account
- Chat and call with you in real time

---

## Limitations

| Limitation | Details |
|---|---|
| **ngrok URLs change** | Free tier gives random URLs on each restart. Run `make tunnel-restart` to auto-update. A paid ngrok plan gives stable subdomains. |
| **Your machine must be on** | Everything runs locally — if your laptop sleeps or loses internet, the demo goes down |
| **ngrok free tier bandwidth** | Sufficient for demos, not for sustained multi-user load |
| **WebSocket through ngrok** | Works well for text chat; occasional latency spikes possible |

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
