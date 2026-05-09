# DClaw Agent — v1.2 Feature Roadmap

> Based on: Y Combinator vertical SaaS principles, trending GitHub repos (crewai, autogen, langgraph), AI product research (Relevance AI, Superagent, AgentGPT, MultiOn)

## Pre-Flight Checklist

- [ ] `frontend/package-lock.json` committed after any `npm install` / dependency change
- [ ] `frontend/next-env.d.ts` exists and is committed
- [ ] `docker-compose.yml` healthchecks correct
- [ ] `frontend/Dockerfile` declares `ARG NEXT_PUBLIC_API_URL` before `RUN npm run build`

## v1.0 Feature Inventory (Current)

- [ ] Agent definition builder
- [ ] Tool/library system
- [ ] Conversation/memory management
- [ ] Basic execution engine
- [ ] Real backend CRUD (no mocks)
- [ ] Docker + Helm deployment
- [ ] Alembic migrations
- [ ] Backend tests

---

## v1.2 Roadmap

### P0 — Must Have (Ship in v1.0, demo-ready)

#### 1. AI Agent Builder (Visual Orchestrator)
**Description:** Visual builder for creating AI agents with drag-and-drop tools, memory, and multi-step reasoning. "Build a research agent that searches the web and writes reports."
- **AI Angle:** No-code agent composition. LangGraph/CrewAI backend.
- **Backend:** Agent runtime engine. Tool registry.
- **Frontend:** Visual agent builder with node canvas.
- **Files:** `backend/app/services/agent_runtime.py`, `frontend/src/app/agents/builder.tsx`

#### 2. Tool/Library Marketplace
**Description:** Pre-built tools: web search, calculator, API caller, file reader, code executor.
- **Backend:** Tool execution sandbox. Tool metadata registry.
- **Frontend:** Tool marketplace with install button.
- **Files:** `backend/app/services/tool_registry.py`

#### 3. Multi-Agent Collaboration
**Description:** Orchestrate multiple agents working together: researcher → writer → reviewer → publisher.
- **Backend:** Multi-agent orchestration with state management.
- **Frontend:** Team workflow visualization with agent chat logs.
- **Files:** `backend/app/services/multi_agent.py`

#### 4. Memory & Context Management
**Description:** Long-term memory with vector store, episodic memory, and user preference learning.
- **Backend:** Memory store with retrieval. Summarization for long contexts.
- **Frontend:** Memory inspector with edit/delete.
- **Files:** `backend/app/services/memory.py`

### P1 — Should Have (v1.1–1.2)

#### 5. Autonomous Task Execution
**Description:** Agents that run scheduled tasks, monitor triggers, and execute without human input.
- **Backend:** Task scheduler with agent triggers. Execution audit log.
- **Frontend:** Task timeline with success/failure history.

#### 6. Human-in-the-Loop Approval
**Description:** Pause agent execution for human approval at critical steps. Approve via email/Slack/app.
- **Backend:** Approval workflow engine. Notification system.
- **Frontend:** Approval inbox with context preview.

#### 7. Agent Performance Analytics
**Description:** Track token usage, latency, success rate, cost per task. Optimize agent configs.
- **Backend:** Metrics collection. Cost attribution.
- **Frontend:** Agent dashboard with efficiency KPIs.

#### 8. Custom Tool Builder
**Description:** Build custom tools with natural language or code. Auto-generate tool schemas.
- **AI Angle:** LLM tool schema generation from description.
- **Backend:** Dynamic tool compilation.
- **Frontend:** Tool builder with test console.

### P2 — Could Have (v1.3+)

#### 9. Swarm Intelligence
**Description:** Hundreds of lightweight agents collaborating on complex problems (market simulation, optimization).

#### 10. Agent-to-Agent Negotiation
**Description:** Agents negotiate resource allocation, task delegation, and consensus.

#### 11. Embodied Agents (Browser/Computer Use)
**Description:** Agents that control browsers and desktops to complete real-world tasks.

#### 12. Agent Insurance & Guarantees
**Description:** Financial guarantees on agent output accuracy with escrow and dispute resolution.

---

## Implementation Priority

1. **Week 1–2:** AI Agent Builder (P0.1) + Tool Marketplace (P0.2)
2. **Week 3–4:** Multi-Agent Collaboration (P0.3) + Memory Management (P0.4)
3. **Week 5–6:** Autonomous Execution (P1.5) + Human Approval (P1.6)
4. **Week 7–8:** Performance Analytics (P1.7) + Custom Tool Builder (P1.8)
