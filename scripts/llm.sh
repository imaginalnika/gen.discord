#!/bin/bash

set -e
[ -f "$HOME/.env" ] && source "$HOME/.env"

if [ -z "$1" ]; then
  echo "Usage: ./llm.sh <prompt>"
  echo "Example: ./llm.sh 'What is the capital of France?'"
  exit 1
fi

PROMPT="$1"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY environment variable not set"
  exit 1
fi

# Escape the prompt for JSON
ESCAPED_PROMPT=$(echo "$PROMPT" | jq -Rs .)

RESPONSE=$(curl -s https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 8192,
    "messages": [
      {
        "role": "user",
        "content": '"$ESCAPED_PROMPT"'
      }
    ]
  }')

# Extract the response text
TEXT=$(echo "$RESPONSE" | jq -r '.content[0].text // empty' 2>/dev/null)

if [ -n "$TEXT" ]; then
  echo "$TEXT"
else
  echo "✗ Failed to get response"
  echo "Response: $RESPONSE"
  exit 1
fi
