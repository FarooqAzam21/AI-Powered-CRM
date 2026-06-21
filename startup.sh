#!/usr/bin/env sh
set -eu

cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
