from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from packages.components.collectors.git import GitCollector
from packages.components.storage import default_event_store
from packages.schemas.events import ActivityEvent, EventValidationError


app = FastAPI(title="Commitbot API", version="0.1.0")
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web" / "static"

if WEB_ROOT.exists():
    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")


class EventCreateRequest(BaseModel):
    source: str
    type: str
    actor: str = "user"
    schema_version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary_text: str | None = None


class GoalCreateRequest(BaseModel):
    title: str
    description: str = ""
    type: str = "project"
    target_date: str | None = None


class PlanCreateRequest(BaseModel):
    title: str
    horizon: str = "quarterly"
    start_date: str | None = None
    end_date: str | None = None
    narrative: str = ""


class AskRequest(BaseModel):
    question: str


@app.get("/")
def index() -> FileResponse:
    index_path = WEB_ROOT / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Web app is not built")
    return FileResponse(index_path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, Any]:
    store = default_event_store()
    return {
        "status": "ok",
        "database": str(store.db_path),
        "event_count": store.count_events(),
    }


@app.post("/events")
def create_event(request: EventCreateRequest) -> dict[str, Any]:
    event = ActivityEvent(
        source=request.source,
        type=request.type,
        actor=request.actor,
        schema_version=request.schema_version,
        payload=request.payload,
        metadata=request.metadata,
        summary_text=request.summary_text,
    )
    try:
        stored = default_event_store().add_event(event)
    except (EventValidationError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return stored.to_record()


@app.get("/events")
def list_events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    return [event.to_record() for event in default_event_store().list_events(limit=limit)]


@app.get("/timeline")
def timeline(
    limit: int = Query(default=100, ge=1, le=500),
    source: str | None = None,
    type: str | None = None,
) -> list[dict[str, Any]]:
    events = default_event_store().list_events(limit=limit)
    if source:
        events = [event for event in events if event.source == source]
    if type:
        events = [event for event in events if event.type == type]
    return [_event_view(event) for event in events]


@app.get("/timeline/day/{day}")
def timeline_day(day: date) -> list[dict[str, Any]]:
    events = [
        event
        for event in default_event_store().list_events(limit=500)
        if event.timestamp.date() == day
    ]
    return [_event_view(event) for event in events]


@app.post("/collectors/git")
def collect_git() -> dict[str, Any]:
    store = default_event_store()
    events = GitCollector(".").collect()
    stored = [store.add_event(event).to_record() for event in events]
    return {"captured": len(stored), "events": stored}


@app.get("/projects")
def projects() -> list[dict[str, Any]]:
    project_map: dict[str, dict[str, Any]] = {}
    for event in reversed(default_event_store().list_events(limit=500)):
        if event.source != "git":
            continue
        repo_path = event.payload.get("repo_path") or event.metadata.get("repo_path") or "unknown"
        project = project_map.setdefault(
            repo_path,
            {
                "id": repo_path,
                "name": Path(repo_path).name if repo_path != "unknown" else "Unknown project",
                "root_path": repo_path,
                "latest_branch": None,
                "latest_commit": None,
                "event_count": 0,
                "last_seen_at": None,
            },
        )
        project["event_count"] += 1
        project["last_seen_at"] = event.timestamp.isoformat()
        if event.payload.get("branch"):
            project["latest_branch"] = event.payload["branch"]
        if event.type == "git.commit":
            project["latest_commit"] = {
                "hash": event.payload.get("hash"),
                "message": event.payload.get("message"),
            }
    return sorted(project_map.values(), key=lambda item: item["last_seen_at"] or "", reverse=True)


@app.post("/goals")
def create_goal(request: GoalCreateRequest) -> dict[str, Any]:
    event = ActivityEvent(
        source="goal",
        type="goal.created",
        payload={
            "title": request.title,
            "description": request.description,
            "type": request.type,
            "target_date": request.target_date,
            "status": "active",
            "user_confirmed": True,
        },
    )
    stored = default_event_store().add_event(event)
    return _goal_from_event(stored)


@app.get("/goals")
def goals() -> list[dict[str, Any]]:
    goal_events = [
        event for event in default_event_store().list_events(limit=500) if event.type == "goal.created"
    ]
    return [_goal_from_event(event) for event in goal_events]


@app.post("/plans")
def create_plan(request: PlanCreateRequest) -> dict[str, Any]:
    event = ActivityEvent(
        source="plan",
        type="plan.created",
        payload={
            "title": request.title,
            "horizon": request.horizon,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "narrative": request.narrative,
            "status": "draft",
        },
    )
    stored = default_event_store().add_event(event)
    return _plan_from_event(stored)


@app.get("/plans")
def plans() -> list[dict[str, Any]]:
    plan_events = [
        event for event in default_event_store().list_events(limit=500) if event.type == "plan.created"
    ]
    return [_plan_from_event(event) for event in plan_events]


@app.get("/summaries/daily/{day}")
def daily_summary(day: date) -> dict[str, Any]:
    events = [
        event
        for event in default_event_store().list_events(limit=500)
        if event.timestamp.date() == day
    ]
    counts: dict[str, int] = {}
    for event in events:
        counts[event.type] = counts.get(event.type, 0) + 1
    highlights = [_event_label(event) for event in events[:8]]
    if events:
        text = f"{day.isoformat()} has {len(events)} captured event(s)."
    else:
        text = f"No activity has been captured for {day.isoformat()} yet."
    return {
        "date": day.isoformat(),
        "event_count": len(events),
        "counts": counts,
        "highlights": highlights,
        "text": text,
    }


@app.post("/agent/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    store = default_event_store()
    store.add_event(
        ActivityEvent(
            source="agent",
            type="agent.message",
            payload={"role": "user", "content": question},
        )
    )

    evidence = _search_evidence(question, store.list_events(limit=500))
    answer = _answer_from_evidence(question, evidence)
    assistant_event = store.add_event(
        ActivityEvent(
            source="agent",
            type="agent.message",
            payload={"role": "assistant", "content": answer, "evidence_ids": [item["id"] for item in evidence]},
        )
    )
    return {
        "answer": answer,
        "message": assistant_event.to_record(),
        "evidence": evidence,
    }


def _event_view(event: ActivityEvent) -> dict[str, Any]:
    record = event.to_record()
    record["label"] = _event_label(event)
    return record


def _event_label(event: ActivityEvent) -> str:
    payload = event.payload
    if event.type == "cli.note":
        return str(payload.get("message", "Note"))
    if event.type == "git.commit":
        return f"Commit: {payload.get('message', payload.get('hash', 'unknown'))}"
    if event.type == "git.diff_snapshot":
        return f"Git snapshot on {payload.get('branch', 'unknown branch')}"
    if event.type == "goal.created":
        return f"Goal: {payload.get('title', 'Untitled')}"
    if event.type == "plan.created":
        return f"Plan: {payload.get('title', 'Untitled')}"
    if event.type == "agent.message":
        return f"{payload.get('role', 'agent')}: {payload.get('content', '')}"
    return event.type


def _goal_from_event(event: ActivityEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "title": event.payload.get("title"),
        "description": event.payload.get("description", ""),
        "type": event.payload.get("type", "project"),
        "target_date": event.payload.get("target_date"),
        "status": event.payload.get("status", "active"),
        "created_at": event.timestamp.isoformat(),
    }


def _plan_from_event(event: ActivityEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "title": event.payload.get("title"),
        "horizon": event.payload.get("horizon", "quarterly"),
        "start_date": event.payload.get("start_date"),
        "end_date": event.payload.get("end_date"),
        "narrative": event.payload.get("narrative", ""),
        "status": event.payload.get("status", "draft"),
        "created_at": event.timestamp.isoformat(),
    }


def _search_evidence(question: str, events: list[ActivityEvent]) -> list[dict[str, Any]]:
    terms = [term for term in re.findall(r"[a-zA-Z0-9_/-]+", question.lower()) if len(term) > 2]
    scored: list[tuple[int, ActivityEvent]] = []
    for event in events:
        haystack = f"{event.type} {event.source} {event.payload} {event.summary_text or ''}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, event))
    if not scored:
        scored = [(1, event) for event in events[:5]]
    scored.sort(key=lambda item: (item[0], item[1].timestamp), reverse=True)
    return [_event_view(event) for _, event in scored[:8]]


def _answer_from_evidence(question: str, evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "I do not have enough captured activity yet to answer that. Add notes or capture Git activity first."
    lines = [
        "Based on the captured traces, here is the current read:",
        "",
    ]
    for item in evidence[:5]:
        timestamp = datetime.fromisoformat(item["timestamp"]).strftime("%Y-%m-%d %H:%M")
        lines.append(f"- {timestamp}: {item['label']}")
    lines.extend(
        [
            "",
            "This is a baseline evidence answer, not a deep model-generated analysis yet. The next agent layer can replace this with richer reasoning while keeping these trace references.",
        ]
    )
    return "\n".join(lines)
