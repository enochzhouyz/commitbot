# commitbot

Commitbot is a local-first, time-aware AI agent system for developer activity memory.

## Current Baseline

This repository currently contains the first implementation slice:

- shared schema and component contracts
- event type registry
- local SQLite event store for immediate development
- FastAPI service with health and event endpoints
- CLI for logging, listing, status, and Git capture
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

Use the CLI:

```powershell
uv run commitbot status
uv run commitbot log "Started Commitbot"
uv run commitbot events
uv run commitbot capture git
```

Run tests:

```powershell
uv run pytest
```

Design docs:

- [Design plan](docs/design-plan.md)
- [Implementation plan](docs/implementation-plan.md)
