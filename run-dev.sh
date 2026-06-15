#!/usr/bin/env bash
# Convenience script: start the FastAPI backend and Next.js front together.
set -e
( cd backend && uvicorn main:app --reload --port 8000 ) &
BACK_PID=$!
( cd web && npm run dev ) &
FRONT_PID=$!
trap "kill $BACK_PID $FRONT_PID 2>/dev/null" EXIT
wait
