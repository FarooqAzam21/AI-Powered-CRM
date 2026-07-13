#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT_DIR"
RUNTIME_DIR="$ROOT_DIR/backend/data"

if [ -f backend/.env ]; then
  set -a
  . backend/.env
  set +a
fi

start_bg() {
  name="$1"
  shift
  log_file="$RUNTIME_DIR/${name}.log"
  mkdir -p "$RUNTIME_DIR"
  echo "Starting ${name}..."
  "$@" >"$log_file" 2>&1 &
  echo "$!" >"$RUNTIME_DIR/${name}.pid"
}

if command -v redis-server >/dev/null 2>&1; then
  start_bg redis redis-server --save "" --appendonly no
  if command -v redis-cli >/dev/null 2>&1; then
    tries=0
    until redis-cli ping >/dev/null 2>&1 || [ "$tries" -ge 20 ]; do
      tries=$((tries + 1))
      sleep 0.25
    done
  fi
else
  echo "redis-server not found; expecting Redis at ${REDIS_URL:-redis://localhost:6379/0}"
fi

if command -v ollama >/dev/null 2>&1; then
  start_bg ollama ollama serve
else
  echo "ollama not found; expecting Ollama at ${OLLAMA_BASE_URL:-http://localhost:11434}"
fi

cd backend
if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
  start_bg celery celery -A tasks.celery_app.celery_app worker --loglevel="${LOG_LEVEL:-INFO}" --pool=solo -Q email,ai,leads,campaigns,maintenance,crm,analytics,dashboard
else
  echo "Redis is not reachable; skipping Celery worker and using local task fallback."
fi

echo "Starting FastAPI on http://127.0.0.1:8000"
uvicorn main:app --host 127.0.0.1 --port 8000
