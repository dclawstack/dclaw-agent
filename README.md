# DClaw Agent

Build, share, and sell AI agents.

## Stack

- **Frontend:** Next.js 14+, React Flow, Tailwind CSS
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0, asyncpg
- **Database:** PostgreSQL
- **LLM:** Ollama (local) with echo fallback

## Quick Start

### Local (without Docker)

1. Start PostgreSQL locally and create database `dclaw_agent`.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   uvicorn app.main:app --reload --port 8091
   ```
3. Frontend:
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   npm run dev
   ```

### Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8091
- API docs: http://localhost:8091/docs

## Features

- **Agent Builder:** Visual drag-and-drop canvas with React Flow
- **Node Types:** Input, LLM, Tool, Memory, Condition, Output
- **Execution:** In-process async engine with step logging
- **Marketplace:** Publish and discover public agents
- **Real-Time:** SSE stream for run status updates

## Seed Data

The seed script creates a sample "Echo Agent" with Input → LLM → Output.

```bash
cd backend
python seed.py
```

## Code Manager

- **Tharuni Dayara** — tharunidayara@gmail.com

## License

MIT
