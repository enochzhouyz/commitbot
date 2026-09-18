# commitbot

Commitbot is a local-first, time-aware AI agent system for developer activity memory.

## Current Baseline

This repository currently contains the first implementation slice:

- shared schema and component contracts
- event type registry
- local SQLite event store for immediate development
- FastAPI service with health, event, timeline, project, goal, plan, summary, and ask endpoints
- CLI for logging, listing, status, and Git capture
- static full-stack web workbench served by the API
- Postgres/pgvector migration and Docker Compose foundation

## Development

Install dependencies:

```powershell
uv sync
```

Run the API:

```powershell
uv run uvicorn services.api.main:app --reload
```

Open the web workbench:

```txt
http://127.0.0.1:8000
```

Use the CLI:

```powershell
uv run commitbot status
uv run commitbot log "Started Commitbot"
uv run commitbot events
uv run commitbot capture git
```

Useful API endpoints:

```txt
GET  /status
GET  /timeline
GET  /projects
GET  /goals
POST /goals
GET  /plans
POST /plans
POST /agent/ask
```

Run tests:

```powershell
uv run pytest
```

Design docs:

- [Design plan](docs/design-plan.md)
- [Implementation plan](docs/implementation-plan.md)
