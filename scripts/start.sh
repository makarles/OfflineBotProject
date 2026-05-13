#!/usr/bin/env sh
set -e

mkdir -p /app/data /app/data/sync /app/data/snapshots

if [ "${BUILD_RAG_INDEX:-0}" = "1" ]; then
  echo "Rebuilding RAG index..."
  python -m backend.rag.indexer
fi

echo "Starting airline company server on :8500..."
uvicorn backend.company_main:app --host 0.0.0.0 --port 8500 &
COMPANY_PID=$!

echo "Starting onboard passenger server on :8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BOARD_PID=$!

trap 'kill "$COMPANY_PID" "$BOARD_PID" 2>/dev/null || true' INT TERM

wait "$COMPANY_PID" "$BOARD_PID"