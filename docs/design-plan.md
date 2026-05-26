# Commitbot Design Plan

## 1. Product Vision

Commitbot is a local-first, time-aware AI agent system for programmers. Its purpose is to track long-running development activity, turn raw traces into useful memory, and provide feedback or tool-assisted help based on what actually happened over time.

The first useful version should answer questions like:

- What did I work on today, yesterday, or last week?
- Which project has been quietly stalled?
- What recurring blockers or context-switching patterns are visible in my work?
- What should I focus on next?
- What long-term direction am I moving toward across months or a year?
- Which goals, skills, or projects deserve more sustained investment?
- What external context, such as calendar events or AI news, matters for my current work?

The core design principle is that Commitbot should not start as a chatbot with plugins. It should start as a memory system for programmer activity, with an AI agent layered on top.

## 2. Reviewed Architecture

The recommended architecture is a local-first, event-sourced fullstack system:

```txt
CLI / local collectors / future desktop app
        |
        v
FastAPI API service
        |
        v
Postgres + pgvector
        |
        v
Worker scheduler
        |
        v
Memory compiler + agent runtime
        |
        v
Next.js web UI
        |
        v
MCP gateway + direct integrations
```

The system should preserve raw activity traces as append-only events. Summaries, embeddings, project timelines, long-term plans, and agent interpretations should be treated as derived data that can be regenerated later.

This architecture is preferred over a chat-history-first system because the important data is not only conversation. The valuable signal comes from commits, branches, commands, tests, notes, calendar context, project state, and repeated behavior over time.

The architecture should also support long-horizon planning. Commitbot should help a developer reason across weeks, months, quarters, and roughly year-long arcs, connecting daily activity to larger goals, skill growth, project bets, and recurring constraints.

## 3. Tech Stack Choices

### Backend: Python + FastAPI

FastAPI is the recommended backend framework for the first implementation.

Reasons:

- Strong fit for AI, data, and automation workflows.
- Excellent typed request/response models through Python type hints and Pydantic-style schemas.
- Lightweight enough for a local-first service.
- Async-friendly for tool calls, integrations, and long-running operations.
- Easy to pair with workers and scripts.

Rejected alternatives:

- Django: strong for traditional CRUD apps, but heavier than needed for an agent API and worker system.
- Flask: flexible, but requires assembling validation, OpenAPI, structure, and async behavior manually.
- Node/Express: workable, but less natural for AI/data workflows.
- NestJS: strong TypeScript backend, but adds more structure than the first version needs.

### Database: Postgres

Postgres should be the primary source of truth.

Reasons:

- Durable relational data for projects, sessions, summaries, tool calls, and approvals.
- JSONB support for flexible event payloads.
- Strong indexing and query capabilities for time-based activity analysis.
- Good migration path from local development to hosted/cloud deployment.

Rejected alternatives:

- SQLite only: good for very early prototypes, but weaker for concurrent workers and cloud-readiness.
- MongoDB: flexible, but less ideal for relational project/session/tool data.
- ClickHouse: excellent analytics engine, but not a good first primary application database.
- Kafka/EventStoreDB first: architecturally attractive, but too heavy before the product proves useful.

### Vector Memory: pgvector First

Use pgvector initially rather than a dedicated vector database.

Reasons:

- Keeps semantic memory near structured memory.
- Allows SQL filtering by project, time range, event source, and summary level.
- Reduces infrastructure complexity.
- Good enough for the first single-user or small-user version.

Dedicated vector databases such as Qdrant, Weaviate, or Pinecone can be introduced later if retrieval scale or latency becomes a real constraint.

### Workers: Simple Scheduler First, Temporal Later

Start with APScheduler, RQ, or a similar simple background worker setup.

Reasons:

- Easy to run locally.
- Enough for daily summaries, periodic ingestion, embeddings, and morning briefs.
- Avoids overengineering before workflows are well understood.

Temporal should be considered later when workflows become long-lived, approval-gated, failure-sensitive, or multi-step across days.

### Frontend: Next.js

Use Next.js for the first web UI.

Reasons:

- Good fit for dashboards, timelines, settings, and chat-like surfaces.
- Mature routing and deployment story.
- Can support auth and cloud features later.
- Faster to build a rich UI than a native desktop app first.

Rejected alternatives:

- Streamlit or Gradio: good demos, but not enough for a durable personal workbench.
- Plain Vite React: viable, but Next.js gives stronger routing and future app structure.
- Electron or Tauri first: useful later for desktop capture, but too much for the initial product surface.

### Agent Integration: MCP Behind a Gateway

MCP should be used as an integration layer, not as the authority layer.

The agent should call tools through this path:

```txt
Agent runtime
    |
Policy and approval layer
    |
MCP gateway
    |
External MCP servers
```

Reasons:

- Every tool call should be logged.
- Risky actions should require user approval.
- Sensitive context may need redaction.
- The system needs stable internal policies even if external tools change.

Direct API integrations should still be allowed for high-value services such as Google Calendar or GitHub when their official APIs provide clearer control than an MCP wrapper.

## 4. Core Services

### CLI

The CLI is the first activity capture surface.

Initial commands:

```txt
commitbot log "Worked on auth bug"
commitbot status
commitbot summarize today
commitbot ask "What did I do yesterday?"
commitbot capture git
```

Later commands:

```txt
commitbot start-session
commitbot end-session
commitbot mood
commitbot plan-day
commitbot review-week
```

### API Service

The API service validates and stores events, exposes timelines, runs chat/agent endpoints, and manages integration state.

Initial endpoints:

```txt
POST /events
GET /events
GET /timeline/day/{date}
GET /projects
POST /agent/ask
POST /agent/actions/{id}/approve
GET /summaries/daily/{date}
```

### Worker Service

The worker service handles background and scheduled work.

Responsibilities:

- Generate daily and weekly summaries.
- Generate embeddings for memory chunks.
- Compile project-level memories.
- Fetch external context such as AI news.
- Run morning and evening review jobs.
- Recompute derived memory from raw events when prompts or summarizers improve.

### Agent Runtime

The agent runtime turns memory and tools into useful responses.

Responsibilities:

- Classify user intent.
- Retrieve relevant raw events, summaries, and project memories.
- Decide whether tool context is needed.
- Generate evidence-based answers.
- Propose actions when appropriate.
- Store all agent messages and proposed actions as events.

The agent should not silently perform external side effects such as editing calendar events, sending messages, or modifying repositories without an explicit approval path.

### Web UI

The first UI should be a workbench, not a landing page.

Primary screens:

- Today: current work, recent activity, active projects, pending suggestions.
- Timeline: chronological event stream with filters.
- Projects: project state, recent work, blockers, linked repos.
- Plans: monthly, quarterly, and yearly goals connected to real activity traces.
- Ask: chat over personal work history.
- Reviews: daily and weekly summaries.
- Integrations: calendar, GitHub, MCP servers, news sources.
- Settings: privacy, retention, model configuration, approval rules.

## 5. Data Model

### Main Tables

The initial database should include:

```txt
events
projects
sessions
goals
plans
plan_reviews
summaries
memory_chunks
agent_messages
tool_calls
tool_approvals
integrations
```

### Events Table

The `events` table is the most important table.

Suggested fields:

```txt
id
timestamp
source
type
project_id
session_id
actor
payload JSONB
summary_text
embedding vector
created_at
```

Raw events should be append-only. If a past event needs correction, add a new correction event instead of mutating history.

### Initial Event Types

```txt
git.commit
git.branch_switch
git.diff_snapshot
cli.note
cli.session_start
cli.session_end
test.run
test.failure
calendar.event_seen
agent.message
agent.suggestion
tool.call_requested
tool.call_completed
mood.checkin
task.created
task.completed
goal.created
goal.updated
plan.created
plan.reviewed
```

### Memory Layers

Commitbot should use layered memory:

```txt
Raw events
Hourly summaries
Daily summaries
Weekly summaries
Monthly summaries
Quarterly summaries
Yearly direction reviews
Project memories
Goal memories
Semantic memory chunks
```

Retrieval should prefer concrete recent data before vague semantic matches:

1. Recent raw events.
2. Daily summaries.
3. Project summaries.
4. Goal and plan memories.
5. Monthly, quarterly, and yearly summaries.
6. Semantic memory chunks.
7. External tools, only when needed.

Long-horizon memory should not replace short-term evidence. A yearly plan should be grounded in accumulated traces, explicit user goals, project progress, calendar constraints, and recurring review outcomes.

## 6. Agent Workflows

### Question Answering

```txt
User asks a question
        |
Classify intent
        |
Retrieve relevant time/project context
        |
Optionally call read-only tools
        |
Generate answer with evidence
        |
Store answer as an agent.message event
```

Example question:

```txt
Why did I stop working on Commitbot last week?
```

Expected behavior:

- Retrieve Git events.
- Retrieve daily summaries.
- Check project memory.
- Identify blockers, context switches, or unresolved tasks.
- Answer with references to specific days or traces.

### Tool Actions

```txt
User asks agent to schedule focus time
        |
Agent checks calendar availability
        |
Agent proposes a calendar event
        |
User approves
        |
Agent writes to Google Calendar
        |
Tool result is logged as an event
```

Actions with external side effects should require approval by default.

Read-only actions may be allowed automatically depending on user settings, but should still be logged.

### Long-Term Planning

Commitbot should support planning across months and roughly one-year horizons.

```txt
User creates or revises long-term goals
        |
Commitbot links goals to projects, skills, habits, and calendar constraints
        |
Monthly and quarterly reviews compare plans against actual activity
        |
Agent identifies drift, compounding progress, blockers, and neglected goals
        |
Agent proposes plan adjustments or focus themes
        |
User accepts, edits, or rejects the plan update
```

Examples:

```txt
Help me plan the next three months around becoming stronger at AI infra.
What projects have I actually invested in this quarter?
Am I still moving toward my yearly goals?
Which skills have I practiced consistently, and which ones are just aspirations?
```

The agent should distinguish between explicit goals and inferred goals. Inferred goals may be suggested, but should not be treated as authoritative until the user confirms them.

## 7. MVP Scope

The first MVP should be narrow:

```txt
A local CLI + backend + timeline UI that records manual notes and Git activity,
generates daily summaries, and lets the user ask questions about recent work.
```

Included:

- Manual activity logging.
- Git activity capture.
- Postgres event storage.
- Basic project detection.
- Timeline API.
- Simple timeline UI.
- Daily summary generation.
- Basic ask endpoint over recent events and summaries.
- Basic goal records, so early activity can be connected to longer-term plans later.

Not included in MVP:

- Full cloud sync.
- Multi-user auth.
- Complex autonomous agents.
- Calendar write permissions.
- Broad MCP tool ecosystem.
- IDE extension.
- Mobile app.
- Full yearly planning automation.

## 8. Phased Roadmap

### Phase 0: Foundation

Goal: make the repository a real project foundation.

Tasks:

- Create monorepo structure.
- Add FastAPI service.
- Add Postgres docker-compose.
- Add database migrations.
- Add event schema.
- Add CLI skeleton.
- Add architecture documentation.

Deliverable:

```txt
commitbot log "message"
```

stores a real event.

### Phase 1: Activity Timeline

Goal: capture and view activity.

Tasks:

- Add events API.
- Add CLI event submission.
- Add Git collector.
- Add project detection.
- Add timeline endpoint.
- Add simple Next.js timeline UI.

Deliverable:

```txt
User can see a timeline of manual notes and Git events.
```

### Phase 2: Memory Compiler

Goal: summarize time.

Tasks:

- Add daily summary job.
- Add summary table.
- Add embeddings with pgvector.
- Add retrieval service.
- Add `summarize today`.
- Add `ask about yesterday`.

Deliverable:

```txt
Agent can answer questions using recent events and daily summaries.
```

### Phase 3: Agent Runtime

Goal: make the system reason with structure.

Tasks:

- Add intent classification.
- Add retrieval planning.
- Add answer generation.
- Add tool-call audit log.
- Add approval model.
- Add prompt versioning.

Deliverable:

```txt
Agent explains past work with evidence and stores its own replies.
```

### Phase 4: Long-Term Planning

Goal: connect daily work to monthly, quarterly, and yearly direction.

Tasks:

- Add goal and plan records.
- Add monthly and quarterly review generation.
- Add plan drift detection.
- Add project-to-goal linking.
- Add plan revision workflow.
- Add Plans UI.

Deliverable:

```txt
Agent can help the user review a quarter, identify drift, and revise a long-term plan.
```

### Phase 5: Calendar and News

Goal: add useful external context.

Tasks:

- Add Google Calendar OAuth.
- Add read-only calendar sync.
- Add free/busy checks.
- Add AI news fetcher.
- Add morning brief job.
- Add approval flow for calendar writes.

Deliverable:

```txt
Agent can identify focus blocks and provide relevant external updates.
```

### Phase 6: MCP Gateway

Goal: make tools extensible.

Tasks:

- Add MCP client service.
- Register MCP servers.
- Expose available tools to the agent runtime.
- Add policy rules.
- Add approval requirements.
- Log all tool calls.

Deliverable:

```txt
Agent can use MCP tools safely through Commitbot's permission and audit layer.
```

## 9. Risks and Tradeoffs

### Local-First vs Cloud-First

Local-first protects privacy and makes early development easier. The tradeoff is that always-on tasks are harder when the user's machine is offline.

Decision: start local-first. Add cloud sync only after the product is personally useful.

### Event-Sourced Memory vs CRUD Simplicity

Append-only events add schema discipline and require derived projections. The tradeoff is worthwhile because long-term interpretation will improve over time.

Decision: store raw events append-only and regenerate summaries as needed.

### pgvector vs Dedicated Vector Database

pgvector is simpler and keeps retrieval tied to project/time metadata. Dedicated vector databases may scale better later.

Decision: start with pgvector. Revisit only when scale or retrieval quality demands it.

### Simple Workers vs Temporal

Simple workers are easier to understand and run locally. Temporal is better for durable long-running workflows but adds operational complexity.

Decision: start with simple workers. Introduce Temporal after workflows become approval-gated or multi-day.

### MCP Gateway vs Direct Tool Calls

A gateway adds implementation work, but prevents unsafe or unlogged actions.

Decision: all MCP tool calls should pass through policy and audit logic.

### Short-Term Feedback vs Long-Term Planning

Short-term feedback is easier to make concrete because it can cite recent events. Long-term planning is more valuable but risks becoming vague or aspirational if it is not grounded in traces.

Decision: add explicit goals and plan reviews, but require long-term advice to cite actual activity patterns, project progress, and review history.

## 10. Current Repository Context

As of this design plan, the repository is mostly empty:

- `README.md` contains only the project title.
- `commitbot` is tracked as a gitlink-style entry.
- There is no existing application code to preserve.

This document is therefore a foundation plan for the first implementation, not a description of existing behavior.

## 11. Guiding Rules

- Store raw events forever unless the user explicitly deletes their data.
- Never rely only on vector memory.
- Make summaries regeneratable.
- Log every agent action.
- Require approval before external side effects.
- Keep local-first until the product feels personally useful.
- Treat MCP tools as capabilities, not authority.
- Make time a first-class concept in schemas, APIs, UI, and agent reasoning.
- Treat long-term plans as living documents that are reviewed against evidence, not static declarations.
