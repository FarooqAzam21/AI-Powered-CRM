# 🚀 Startup Commands — AI-Powered CRM

All commands assume you are running from the project root:
`c:\Users\Farooq\Desktop\AI App\AI-Powered CRM\`

---

## ⚡ Quick Start (Recommended Order)

Run each service in its own terminal window.

---

## 1️⃣ Ollama (Local AI Model)

Ollama must be running **before** the backend starts.

```powershell
# Pull the model (first time only)
ollama pull qwen2.5:1.5b

# Start Ollama server (runs on http://localhost:11434)
ollama serve
```

Verify it's running:
```powershell
ollama list
```

---

## 2️⃣ Backend (FastAPI + Uvicorn)

```powershell
# Navigate to backend
cd "c:\Users\Farooq\Desktop\AI App\AI-Powered CRM\backend"

# (First time) Create a virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# (First time) Install dependencies
pip install -r requirements.txt

# (First time) Apply database migrations
alembic upgrade head

# Start the API server (http://localhost:8000)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API Docs available at: `http://localhost:8000/docs`

---

## 3️⃣ Celery Worker (Background Tasks)

Open a **new terminal**, activate the same venv, then run:

```powershell
cd "c:\Users\Farooq\Desktop\AI App\AI-Powered CRM\backend"
.\venv\Scripts\activate

# Start the Celery worker (processes email, AI, analytics tasks)
celery -A tasks.celery_app.celery_app worker --loglevel=INFO --pool=solo -Q email,ai,leads,campaigns,maintenance,crm,analytics,dashboard
```

---

## 4️⃣ Celery Beat (Scheduled Tasks — Optional)

Open a **new terminal**, activate the same venv, then run:

```powershell
cd "c:\Users\Farooq\Desktop\AI App\AI-Powered CRM\backend"
.\venv\Scripts\activate

# Start Celery Beat scheduler
celery -A tasks.celery_app.celery_app beat --loglevel=INFO
```

---

## 5️⃣ Frontend (Vite + React)

```powershell
# Navigate to frontend
cd "c:\Users\Farooq\Desktop\AI App\AI-Powered CRM\frontend"

# (First time) Install Node dependencies
npm install

# Start the dev server (http://localhost:5173)
npm run dev
```

---

## 6️⃣ Redis (Required for Celery + Caching)

If Redis is **not already running** as a system service:

```powershell
# Option A: Via Docker (easiest)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Option B: If Redis is installed natively on Windows
redis-server
```

Verify Redis:
```powershell
redis-cli ping
# Expected output: PONG
```

---

## 🐳 Docker Compose (Run Everything at Once)

> Runs PostgreSQL, Redis, the FastAPI API, Celery Worker, and Celery Beat — all in containers.
> **Note:** Ollama and the Frontend still run on your host machine.

```powershell
# Navigate to project root
cd "c:\Users\Farooq\Desktop\AI App\AI-Powered CRM"

# Build and start all services
docker compose up --build

# Run in detached (background) mode
docker compose up --build -d

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f api
docker compose logs -f worker

# Stop all services
docker compose down

# Stop and remove volumes (resets the database)
docker compose down -v
```

---

## 📋 Service Summary Table

| Service        | Command                        | URL / Port           |
|----------------|-------------------------------|----------------------|
| Ollama         | `ollama serve`                 | `localhost:11434`    |
| Backend API    | `uvicorn main:app --reload`    | `localhost:8000`     |
| API Docs       | *(auto-generated)*             | `localhost:8000/docs`|
| Celery Worker  | `celery ... worker`            | *(background)*       |
| Celery Beat    | `celery ... beat`              | *(background)*       |
| Frontend       | `npm run dev`                  | `localhost:5173`     |
| Redis          | `redis-server`                 | `localhost:6379`     |
| PostgreSQL     | *(via Docker Compose)*         | `localhost:5432`     |

---

## 🔍 Health Checks

```powershell
# Backend health
curl http://localhost:8000/health

# AI Engine health (requires auth token)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/ai/health

# Ollama
curl http://localhost:11434/api/tags

# Redis
redis-cli ping
```
