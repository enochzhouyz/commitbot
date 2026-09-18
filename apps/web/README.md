# Commitbot Web

This is the first runnable web workbench. It is intentionally static and served by FastAPI so the full-stack baseline can run without a Node build step.

Run:

```powershell
uv run uvicorn services.api.main:app --reload
```

Open:

```txt
http://127.0.0.1:8000
```

Future iterations can replace this static app with Next.js while keeping the same API contracts.
