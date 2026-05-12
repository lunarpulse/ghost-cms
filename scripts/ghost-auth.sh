#!/usr/bin/env bash
# Ghost Admin API JWT Token Generator
# Usage: source ghost-auth.sh or TOKEN=$(ghost-auth.sh)
#
# Reads GHOST_ADMIN_KEY from ~/.hermes/.env
# Outputs a fresh JWT token for Ghost Admin API authentication

set -e

ENV_FILE="${HOME}/.hermes/.env"

# Load API key from env file
if [[ -f "$ENV_FILE" ]]; then
    GHOST_ADMIN_KEY=$(grep "^GHOST_ADMIN_KEY=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'")
fi

if [[ -z "$GHOST_ADMIN_KEY" ]]; then
    echo "Error: GHOST_ADMIN_KEY not found in $ENV_FILE" >&2
    echo "Add it: echo 'GHOST_ADMIN_KEY=your_key' >> ~/.hermes/.env" >&2
    exit 1
fi

# Split key into id:secret
IFS=':' read -r KEY_ID KEY_SECRET <<< "$GHOST_ADMIN_KEY"

if [[ -z "$KEY_ID" || -z "$KEY_SECRET" ]]; then
    echo "Error: GHOST_ADMIN_KEY must be in format 'id:secret'" >&2
    exit 1
fi

# Base64URL encode helper (no padding, URL-safe)
base64url_encode() {
    printf '%s' "$1" | base64 | tr -d '\n' | tr -d '=' | tr '+' '-' | tr '/' '_'
}

# Current timestamps in seconds
NOW=$(date +%s)
EXP=$((NOW + 300))  # 5 minutes expiry

# Build JWT header and payload
HEADER="{\"alg\":\"HS256\",\"typ\":\"JWT\",\"kid\":\"$KEY_ID\"}"
PAYLOAD="{\"iat\":$NOW,\"exp\":$EXP,\"aud\":\"/admin/\"}"

# Encode header and payload
HEADER_B64=$(base64url_encode "$HEADER")
PAYLOAD_B64=$(base64url_encode "$PAYLOAD")
HEADER_PAYLOAD="${HEADER_B64}.${PAYLOAD_B64}"

# Sign with HMAC-SHA256 using hex-decoded secret
SIGNATURE=$(printf '%s' "$HEADER_PAYLOAD" | openssl dgst -binary -sha256 -mac HMAC -macopt hexkey:"$KEY_SECRET" | base64 | tr -d '=' | tr '+' '-' | tr '/' '_')

# Output complete JWT token
TOKEN="${HEADER_PAYLOAD}.${SIGNATURE}"
echo "$TOKEN"
