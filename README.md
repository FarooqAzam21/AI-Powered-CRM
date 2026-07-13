# AI-Powered CRM + Email Automation Platform

A state-of-the-art Customer Relationship Management (CRM) and Email Automation platform built with a highly modular, decoupled AI Engine. This system is designed to provide real-time sales analytics, background email synchronization, and context-aware AI capabilities without locking you into a single LLM provider.

## 🚀 Key Features

### Core CRM Functionality
- **Contacts & Leads:** Manage customer profiles, track interactions, and score leads.
- **Pipelines & Deals:** Track sales cycles, territories, and deal progression.
- **Analytics & Dashboards:** Real-time metrics streaming via WebSockets.
- **Email Integration:** Background Gmail metadata synchronization and thread tracking.

### Advanced AI Engine
- **Provider Agnostic:** Easily swap between Ollama (Local), OpenAI, or Anthropic.
- **RAG Knowledge Base:** Powered by ChromaDB. Ingests PDFs, CSVs, and DOCX files to ground AI responses in company facts.
- **Dynamic Context Builder:** Automatically aggregates a contact's CRM history, past emails, deal status, and persistent AI memory before generation.
- **Jinja2 Prompt Management:** Prompt templates are completely decoupled from Python logic, allowing prompt engineers to tweak behaviors safely.
- **Auto-Retrying Response Parser:** Forces the LLM to output strict JSON for data extraction (like Lead Scoring or Classification). If the LLM hallucinates formatting, it auto-corrects.
- **Semantic Caching:** Identical prompts are hashed and cached in Redis for 24 hours to save compute.
- **PII Security:** A sanitizer strips Credit Card numbers, SSNs, and Phone Numbers before sending context to the LLM.
- **Real-Time Streaming:** AI responses (like drafting emails) stream token-by-token directly to the frontend via WebSockets.

---

## 🏗 System Architecture

The application follows a modern asynchronous microservices-inspired monolithic architecture.

### Tech Stack
- **Backend Framework:** FastAPI (Python 3.11+)
- **Database ORM:** SQLAlchemy (Async/Sync)
- **Task Queue:** Celery + Redis Broker
- **Vector Database:** ChromaDB (Local embedded)
- **AI Models:** Ollama (default: `qwen2.5:1.5b` or `llama3`)
- **WebSockets:** FastAPI WebSockets + custom connection manager
- **Templating:** Jinja2

### Directory Structure
```
backend/
├── ai/                     # Modular AI Engine
│   ├── cache/              # Redis Semantic Caching
│   ├── context/            # ContextBuilder (Aggregates CRM data)
│   ├── memory/             # MemoryManager (Extracts persistent customer preferences)
│   ├── parser/             # ResponseParser (Enforces strict JSON with auto-retries)
│   ├── prompts/            # PromptManager & Jinja2 Templates
│   ├── providers/          # BaseProvider interface & OllamaProvider
│   ├── rag/                # ChromaDB KnowledgeBase & Document Parsers
│   ├── services/           # The AIEngine Facade (Main entry point)
│   └── utils/              # PIISanitizer
├── auth/                   # JWT Authentication & User Models
├── config/                 # Pydantic Settings & Environment Variables
├── crm_email/              # Gmail API integration and sync logic
├── models/                 # SQLAlchemy Database Models (CRM, AI Memory, Campaigns)
├── routers/                # FastAPI REST & WebSocket endpoints
├── services/               # Core CRM business logic (Dashboards, Sales Cycle, etc.)
├── tasks/                  # Celery Application initialization
├── workers/                # Celery Background Workers (e.g., email_tasks)
└── ws_manager/             # WebSocket connection management
```

---

## 🧠 How the AI Engine Works (The Pipeline)

When a user clicks "Generate Reply" on a contact's email, the following pipeline executes:

1. **Context Aggregation (`ContextBuilder`)**
   The CRM gathers the contact's profile, past deals, recent activities, and persistent AI memory.
2. **RAG Retrieval (`KnowledgeBase`)**
   The user's query is embedded, and relevant company documents are retrieved from ChromaDB.
3. **PII Sanitization (`PIISanitizer`)**
   All aggregated context is scrubbed of sensitive information (SSNs, Credit Cards).
4. **Prompt Assembly (`PromptManager`)**
   The clean context and user query are injected into a Jinja2 template (`reply_generation.jinja2`).
5. **Semantic Caching (`SemanticCache`)**
   The system hashes the final prompt and checks Redis. If found, it returns the cached reply instantly.
6. **LLM Generation (`OllamaProvider`)**
   If not cached, the request is sent to the local Ollama instance. Tokens can either be generated synchronously or streamed via WebSockets.
7. **Response Parsing (`ResponseParser`)**
   *(For structured data tasks only)* The LLM's output is validated against a JSON schema. If it fails, the error is fed back to the LLM for an automatic retry.
8. **Memory Extraction (`MemoryManager`)**
   Post-generation, the interaction is analyzed in the background via a Celery task to update the customer's persistent memory (e.g., updating their preferred tone or noted pain points).

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.11+
- Redis Server (Running on localhost:6379)
- Ollama (Running locally with your preferred model pulled, e.g., `ollama run qwen2.5:1.5b`)
- PostgreSQL (or SQLite for dev)

### Installation
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up your `.env` file (Database URLs, Redis URL, Ollama endpoint).
4. Run the FastAPI Server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
5. Run the Celery Worker (in a separate terminal):
   ```bash
   celery -A tasks.celery_app worker --loglevel=info
   ```

## 🔒 Security
- **Authentication:** JWT Bearer tokens for all API endpoints.
- **Data Privacy:** PII masking ensures no sensitive customer data touches the AI generation layer.
- **Role-Based Access Control:** Admin vs User separation for endpoints and WebSocket broadcasts.

---

## 🚀 Startup Commands

> Full details in [STARTUP.md](./STARTUP.md). Run each in its own terminal, in this order:

### 1. Ollama (AI Model — run first)
```powershell
ollama pull qwen2.5:1.5b   # First time only
ollama serve
```

### 2. Backend (FastAPI)
```powershell
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Celery Worker (Background Tasks)
```powershell
cd backend
.\venv\Scripts\activate
celery -A tasks.celery_app.celery_app worker --loglevel=INFO --pool=solo -Q email,ai,leads,campaigns,maintenance,crm,analytics,dashboard
```

### 4. Frontend (React + Vite)
```powershell
cd frontend
npm install     # First time only
npm run dev
```

### 5. Docker Compose (Spins up PostgreSQL + Redis + API + Workers)
```powershell
docker compose up --build       # Foreground
docker compose up --build -d    # Background (detached)
docker compose down             # Stop all
docker compose down -v          # Stop + wipe database
```

### Service URLs
| Service     | URL                        |
|-------------|----------------------------|
| Frontend    | http://localhost:5173       |
| Backend API | http://localhost:8000       |
| API Docs    | http://localhost:8000/docs  |
| Ollama      | http://localhost:11434      |
| Redis       | localhost:6379              |
| PostgreSQL  | localhost:5432              |
