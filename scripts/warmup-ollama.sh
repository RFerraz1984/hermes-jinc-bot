#!/usr/bin/env bash
# Warmup Ollama llama3.1:8b model to keep it in VRAM/RAM
# Run via cron every 5-10 minutes to prevent cold starts

curl -s -X POST http://host.docker.internal:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.1:8b", "prompt": "warmup", "keep_alive": -1, "stream": false}' \
  > /dev/null 2>&1
