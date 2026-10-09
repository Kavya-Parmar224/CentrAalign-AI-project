# Autonomous AI Task Worker

An autonomous AI agent that accepts natural-language tasks and executes them end-to-end — navigating websites, reading files, calling APIs, remembering context, retrying failures, and verifying outcomes.

---

## Demo

Given the task:
> "Check the onboarding ticket, navigate to the provisioning page, grant them GitHub access, and mark the ticket as resolved."

The agent will:
1. Navigate to the IT ticketing dashboard
2. Locate the onboarding ticket and extract the user's email
3. Navigate to the provisioning portal
4. Select the user and grant GitHub access
5. Return to the ticket and mark it as resolved
5. Verify the entry was saved
6. Return a verified summary with screenshot evidence

---

## Architecture

```
User (natural language task)
        │
        ▼
  ┌─────────────┐
  │  FastAPI    │  ← REST + WebSocket
  │  Backend    │
  └──────┬──────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │                   AutonomousAgent                        │
  │                                                         │
  │  1. Planner   → LLM decomposes task into ordered steps  │
  │  2. ReAct Loop→ Reason → Act → Observe (up to 25 iters) │
  │  3. Verifier  → Separate LLM pass checks goal achieved  │
  │  4. Summarise → Human-readable result + evidence        │
  └──────────────────────────────┬──────────────────────────┘
                                 │ dispatches to
         ┌───────────────────────┼──────────────────────┐
         ▼                       ▼                      ▼
   ┌───────────┐         ┌──────────────┐       ┌──────────────┐
   │  Browser  │         │  File / HTTP │       │  ask_human   │
   │ (Playwright│        │   Tools      │       │  (HIL gate)  │
   │  headful) │         └──────────────┘       └──────────────┘
   └───────────┘
         │
         ▼
   ┌──────────────────┐
   │ Acme Corp Portal │  ← simulated company app (Flask)
   │ localhost:5001   │
   └──────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Agent core | `agent/core.py` | ReAct loop, retry logic, conversation management |
| Planner | `agent/planner.py` | LLM task decomposition into typed `TaskPlan` |
| Verifier | `agent/verifier.py` | Independent LLM verification of task completion |
| Memory | `agent/memory.py` | Working memory + SQLite episodic storage |
| Browser tool | `agent/tools/browser_tool.py` | Playwright — navigate, click, fill, extract, screenshot |
| File tool | `agent/tools/file_tool.py` | Read/write local files (text, CSV, JSON) |
| HTTP tool | `agent/tools/http_tool.py` | Generic HTTP requests |
| Human-in-loop | `agent/tools/ask_human_tool.py` | Pause and ask user via WebSocket |
| API server | `api/server.py` | FastAPI + WebSocket event streaming |
| Demo app | `demo_app/app.py` | Simulated internal IT Helpdesk portal |
| Frontend | `frontend/` | React + Vite live execution trace UI |

---

## Setup & Run

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/)

### 1. Clone and install Python dependencies

```bash
git clone <repo-url>
cd autonomous-ai-worker

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 4. Run

**Option A — all-in-one (backend + demo app):**
```bash
python run.py
```

**Option B — separate terminals (recommended for development):**
```bash
# Terminal 1: Demo company app
python demo_app/app.py

# Terminal 2: FastAPI backend
uvicorn api.server:app --port 8000 --reload

# Terminal 3: React frontend
cd frontend && npm run dev
```

### 5. Open the UI

- **Agent UI:** http://localhost:3000
- **Demo Company Portal:** http://localhost:5001
- **API Docs:** http://localhost:8000/docs

---

## Example Tasks to Try

1. **Ticket resolution:**
   > "Check the onboarding ticket, navigate to the provisioning page, grant them GitHub access, and mark the ticket as resolved."

2. **Information lookup:**
   > "Find the open high-priority ticket, look up the user's manager via the API, and write a summary file."

3. **Data summarization:**
   > "Get all open tickets via the API and summarize the current workload."

---

## How It Works — Technical Detail

### ReAct Loop

Each iteration:
1. **Reason** — LLM receives full conversation history + task context, picks the next tool to call
2. **Act** — The tool executes (browser action, file read, HTTP call, etc.)
3. **Observe** — Tool result is appended to conversation history; key facts extracted to memory
4. Loop until `TASK_COMPLETE` signal or max iterations

The conversation history is maintained as a proper multi-turn dialogue, so the model always has full context of what it has done and observed.

### Retry Logic

- Each tool call is retried up to 3 times with **exponential backoff** (2s, 4s, 8s)
- Consecutive failures increment a counter; at 4 consecutive failures the loop terminates
- On retries, the error message is included so the LLM can adapt its approach

### Memory System

- **Working memory** — in-process dict for fast key-value storage (e.g. `ticket_id: T-103`)
- **Fact extraction** — regex-based extraction of amounts ($), dates, IDs from tool outputs
- **Episodic storage** — SQLite log of every trace entry for auditability
- **Context injection** — memory snapshot injected into conversation every 5 steps

### Verification

After execution, a **separate** LLM call assesses:
- Did the agent achieve the user's stated goal?
- What evidence exists (extracted data, screenshots, API confirmations)?
- Result: `VERIFIED` / `PARTIAL` / `FAILED` with detailed explanation

Using a separate verification pass prevents the executing agent from self-confirming success.

### Human-in-the-Loop

The agent calls `ask_human` when:
- It detects an ambiguity it cannot resolve from context
- It is about to take a destructive/irreversible action
- It needs confirmation before proceeding

The agent loop **pauses** (asyncio Future) until the human responds via the UI.

### Browser Automation

Playwright runs in **headful mode** (visible browser window) so you can watch the agent work in real time. Each browser action:
- Takes a screenshot immediately after execution
- Screenshots are served via the API and shown inline in the trace UI

---

## Architecture Decisions

**Why a custom ReAct loop instead of LangChain?**
Full control over retry logic, conversation management, event emission, and verification. LangChain abstractions obscure the actual API calls and make debugging harder. A hand-rolled loop is ~200 lines and fully transparent.

**Why a separate Verifier LLM call?**
An agent that assesses its own success will almost always say it succeeded. A separate prompt with fresh context is far more reliable.

**Why headful Playwright (not headless)?**
Demo purposes — watching the browser navigate is compelling in a live demo. Can be toggled to headless for production.

**Why Flask for the demo app instead of mocking?**
A real web app tests real browser automation. Mocking would defeat the purpose of demonstrating that the agent can actually navigate UIs.

**Why Google Gemini 3.1 Flash-Lite?**
Gemini Flash-Lite is extremely fast and cost-effective, which is perfect for an agent that needs to run rapid multi-step reasoning loops. It reliably follows tool instructions while keeping execution costs very low.

**Why WebSockets for the UI?**
The agent runs asynchronously (can take 30-120 seconds). WebSocket streaming lets you watch the agent reason and act in real time, which is essential for understanding and debugging.

---

## Known Limitations

- **Single-browser session per task** — no parallelism within a task
- **No persistent agent identity** — memory is per-task only
- **Playwright setup required** — users must `playwright install chromium`
- **API key cost** — long tasks may use many Gemini API calls (typically 5-15 per task)
- **No auth support** — cannot log into password-protected sites
- **Context window** — very long tasks may exceed conversation limits; memory summarization is basic
- **Screenshot serving** — screenshots identified by filename, not scoped per-task (multi-task concurrent use could mix screenshots)

---

## What I'd Build Next

1. **Persistent memory across tasks** — vector DB (e.g. ChromaDB) for semantic retrieval of past execution patterns
2. **Parallel sub-task execution** — decompose tasks into independent branches and run concurrently
3. **Structured output validation** — Pydantic validation of LLM JSON outputs with automatic repair prompts
4. **Sandboxed browser profiles** — isolated Playwright contexts per task to prevent state leakage
5. **Evaluation harness** — scripted test tasks with expected outcomes to measure success rate
6. **Auth credential vault** — secure storage for site credentials (never in plaintext)
7. **Task queue** — Redis-backed queue for multi-task scheduling
8. **Streaming plan updates** — re-plan mid-execution when the environment differs from expectations

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| LLM | Google Gemini 3.1 Flash-Lite | gemini-3.1-flash-lite |
| Browser | Playwright (Chromium) | ≥1.43 |
| Backend | FastAPI + Uvicorn | ≥0.110 |
| WebSockets | FastAPI WebSocket | built-in |
| Demo App | Flask | ≥3.0 |
| Memory DB | SQLite (stdlib) | built-in |
| Frontend | React + Vite + Tailwind CSS | React 18 |
| HTTP Client | httpx (async) | ≥0.27 |
| Data models | Pydantic v2 | ≥2.7 |

---

## Assumptions

- The "company system" is the local Flask demo app at `localhost:5001`
- Tasks are single-user (no concurrent task isolation required for this prototype)
- The Gemini API is available and the key has sufficient quota
- Playwright's Chromium is installed locally
- Tasks complete in reasonable time (under 5 minutes); no background job persistence across server restarts
