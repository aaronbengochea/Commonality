#!/usr/bin/env bash
# Reads the running ngrok tunnel URL and updates .env accordingly.
# Usage: ./scripts/ngrok-update-env.sh
#
# Prerequisites: ngrok tunnel must already be running (ngrok start --all)

set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env file not found at $ENV_FILE"
  exit 1
fi

# Fetch tunnel info from ngrok's local API
TUNNELS=$(curl -s http://127.0.0.1:4040/api/tunnels)

if [ -z "$TUNNELS" ] || echo "$TUNNELS" | grep -q '"error"'; then
  echo "ERROR: Could not reach ngrok API at http://127.0.0.1:4040"
  echo "Make sure ngrok is running: ngrok start --all"
  exit 1
fi

# Extract the HTTPS tunnel URL
TUNNEL_URL=$(echo "$TUNNELS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tunnels', []):
    if t['public_url'].startswith('https'):
        print(t['public_url'])
        break
")

if [ -z "$TUNNEL_URL" ]; then
  echo "ERROR: Could not find an HTTPS tunnel."
  echo "Raw tunnels response:"
  echo "$TUNNELS" | python3 -m json.tool
  exit 1
fi

# Derive WebSocket URL from HTTPS URL
WS_URL=$(echo "$TUNNEL_URL" | sed 's|^https://|wss://|')

echo "Detected ngrok tunnel: $TUNNEL_URL"
echo ""

# Update .env values (macOS-compatible sed)
# All traffic goes through nginx on the same URL
sed -i '' "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=$TUNNEL_URL|" "$ENV_FILE"
sed -i '' "s|^NEXT_PUBLIC_WS_URL=.*|NEXT_PUBLIC_WS_URL=$WS_URL|" "$ENV_FILE"
sed -i '' "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$TUNNEL_URL|" "$ENV_FILE"

echo "Updated .env:"
echo "  NEXT_PUBLIC_API_URL=$TUNNEL_URL"
echo "  NEXT_PUBLIC_WS_URL=$WS_URL"
echo "  CORS_ORIGINS=$TUNNEL_URL"
echo ""
echo "Now restart services:"
echo "  docker compose up -d --build frontend && docker compose restart backend"
