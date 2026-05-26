# Commitbot Implementation Plan

This file translates `docs/design-plan.md` into an execution guide for building Commitbot in large, ordered steps. It is written as instructions for a future implementation agent: make the smallest useful system first, keep the event log central, and avoid adding autonomous behavior before memory, evidence, and approvals are solid. The baseline should be modular enough to accept new collectors, memory compilers, UIs, integrations, agent capabilities, and planning components without reorganizing the whole repo.

## 1. Implementation Principles

- Build vertical slices, not isolated infrastructure. Each phase should produce something the user can run or inspect.
- Keep raw activity events append-only. Derived summaries, embeddings, and plans may be regenerated.
- Prefer local-first behavior until the system is personally useful.
- Log every agent message, suggestion, tool request, approval, and tool result as part of the timeline.
- Treat long-term plans as reviewable living records, not static motivational text.
- Keep integrations read-only until the approval system exists.
- Avoid broad framework commitments until a feature actually needs them. Start with FastAPI, Postgres, pgvector, a simple worker, a CLI, and a Next.js UI.
- Design each subsystem around stable contracts rather than direct imports across every boundary.
- Prefer registries and provider interfaces for components likely to grow: collectors, summarizers, retrievers, model providers, integrations, policy rules, and UI feature modules.

## 2. Target Repository Layout

Create this structure during Phase 0. Treat it as a flexible baseline, not a permanent cage:

```txt
apps/
  cli/
  web/
services/
  api/
  worker/
  agent/
packages/
  core/
  schemas/
  components/
  prompts/
infra/
  migrations/
  docker-compose.yml
docs/
  design-plan.md
  implementation-plan.md
```

Responsibilities:

- `apps/cli`: user-facing local commands and activity capture.
- `apps/web`: timeline, project, plan, review, settings, and ask UI.
- `services/api`: HTTP API, validation, persistence, and auth boundary for local clients.
- `services/worker`: scheduled jobs for summaries, embeddings, reviews, and external fetches.
- `services/agent`: retrieval, prompt assembly, intent handling, tool policy, and answer generation.
- `packages/core`: shared domain concepts, component contracts, result types, and common utilities.
- `packages/schemas`: shared event types, payload contracts, API DTOs, and validation rules.
- `packages/components`: optional component implementations such as collectors, retrievers, summarizers, and integrations when they do not belong to a single app.
- `packages/prompts`: versioned prompts for summaries, reviews, planning, and agent answers.
- `infra`: local database, migrations, and development orchestration.

Do not initialize the tracked `commitbot` gitlink unless a separate task decides how to handle it.

Component boundaries:

- Collectors produce events and should not write directly to business tables.
- Memory compilers read events and summaries, then write derived summaries or memory chunks.
- Retrievers expose a common search interface across raw events, summaries, goals, plans, and vectors.
- Agent capabilities operate through retrieval, policy, and tool-call interfaces rather than direct database access.
- Integrations expose read and write operations separately so approval policy can wrap writes.
- UI features consume API contracts and should not duplicate domain rules.

## 3. Phase 0: Foundation

Goal: create a runnable local project skeleton and store manual events.

Build:

- Add monorepo directories.
- Add a Python FastAPI service in `services/api`.
- Add a Python CLI in `apps/cli`.
- Add local Postgres and pgvector in `infra/docker-compose.yml`.
- Add migrations under `infra/migrations`.
- Add shared schema definitions under `packages/schemas`.
- Add core component contracts under `packages/core`.
- Add initial registries for event types, collectors, model providers, memory compilers, and integrations.
- Add basic configuration through environment variables.
- Add developer commands in the README for setup, API, CLI, and tests.

Initial database tables:

```txt
events
projects
sessions
goals
plans
summaries
memory_chunks
agent_messages
tool_calls
tool_approvals
integrations
```

Initial `events` fields:

```txt
id UUID primary key
timestamp timestamptz not null
source text not null
type text not null
schema_version integer not null default 1
actor text not null
project_id UUID nullable
session_id UUID nullable
payload jsonb not null default '{}'
metadata jsonb not null default '{}'
summary_text text nullable
embedding vector nullable
created_at timestamptz not null
```

Baseline contracts:

```txt
Collector: discover context, emit one or more ActivityEvent records.
EventValidator: validate event type, schema version, and payload shape.
MemoryCompiler: read source records and produce summaries or memory chunks.
Retriever: search a bounded data source and return evidence records.
ModelProvider: generate text or embeddings behind a replaceable interface.
Integration: expose read operations and separately expose approval-gated write operations.
PolicyRule: classify an action as allowed, approval_required, or denied.
```

Initial API:

```txt
POST /events
GET /events
GET /health
```

Initial CLI:

```txt
commitbot log "message"
commitbot events
commitbot status
```

Acceptance criteria:

- `docker compose up` starts Postgres.
- API starts and responds to `/health`.
- `commitbot log "..."` creates a `cli.note` event.
- `commitbot events` prints recent events.
- Event payloads include `schema_version` and can be validated through the registry.
- Tests cover schema validation and event creation.

## 4. Phase 1: Git Activity Timeline

Goal: capture meaningful developer traces and view them as a timeline.

Build:

- Add project detection from current Git repository path.
- Add `projects` table fields for name, root path, repo URL, created time, and last seen time.
- Add Git collector as a registered collector implementation.
- Add event ingestion for commits, branch switches, and lightweight diff snapshots.
- Add timeline APIs with date range, project, source, and event type filters.
- Add first Next.js UI with a dense workbench layout.
- Keep timeline rendering event-type aware, but allow unknown event types to fall back to a generic renderer.

CLI:

```txt
commitbot capture git
commitbot timeline --today
commitbot timeline --since 2026-05-01
```

API:

```txt
GET /timeline
GET /timeline/day/{date}
GET /projects
GET /projects/{id}
```

Git event payloads:

- `git.commit`: commit hash, message, author time, branch, files changed, insertions, deletions.
- `git.branch_switch`: old branch if known, new branch, repo path.
- `git.diff_snapshot`: branch, changed file count, staged count, unstaged count, untracked count.

UI screens:

- Today: latest events, active project, quick note form.
- Timeline: filterable chronological list.
- Projects: project list and recent activity.

Acceptance criteria:

- Running `commitbot capture git` inside this repo records at least current branch and recent commit context.
- Timeline endpoint can filter by date and project.
- Web UI renders recent events without requiring agent features.
- Adding another collector should not require changing the timeline API shape.
- Tests cover Git parsing with fixture outputs.

## 5. Phase 2: Memory Compiler

Goal: turn raw traces into summaries and searchable memory.

Build:

- Add `summaries` table with scope, start time, end time, source event IDs, model/prompt version, text, and metadata.
- Add `memory_chunks` table with source type, source ID, text, embedding, project ID, time range, and tags.
- Add worker service with scheduled and manual jobs.
- Add prompt templates for daily summaries and project summaries.
- Add embedding generation behind a provider interface.
- Add retrieval service as a composition of registered retrievers for raw events, summaries, projects, goals, plans, text search, and vector search.

Jobs:

```txt
compile_daily_summary(date)
compile_project_summary(project_id, start, end)
embed_summary(summary_id)
embed_event(event_id)
```

CLI:

```txt
commitbot summarize today
commitbot summarize --date 2026-05-25
commitbot memory search "debugging loop"
```

API:

```txt
GET /summaries/daily/{date}
POST /summaries/daily/{date}/compile
GET /memory/search
```

Acceptance criteria:

- Daily summaries can be regenerated from raw events.
- Summary rows record prompt/model version.
- Retrieval can answer simple searches using recent event text and summary text.
- A new memory compiler can be registered without changing existing summary jobs.
- Tests cover summary compilation with deterministic fake model output.

## 6. Phase 3: Ask and Agent Runtime

Goal: answer questions about past work with evidence.

Build:

- Add `agent_messages` table for user messages, assistant messages, retrieved context IDs, prompt version, model, and timestamps.
- Add intent classification for timeline questions, project questions, planning questions, and tool/action requests.
- Add retrieval planner with this order: recent raw events, daily summaries, project summaries, goal/plan memories, long-horizon summaries, semantic memory.
- Add answer generator that cites dates, event IDs, project names, or summary IDs when possible.
- Add agent capability registry for question answering, planning, brief generation, and later tool use.
- Store every user question and assistant answer as timeline events.

API:

```txt
POST /agent/ask
GET /agent/messages
```

CLI:

```txt
commitbot ask "What did I work on yesterday?"
commitbot ask "Why did this project stall?"
```

Agent behavior:

- If evidence is weak, say what is missing instead of inventing patterns.
- Prefer concrete trace references over broad advice.
- Distinguish observed facts from inferred interpretations.
- Do not execute external tool writes in this phase.

Acceptance criteria:

- Asking about a date retrieves events and summaries from that period.
- Answers include enough evidence for the user to inspect the underlying traces.
- Agent messages are stored back into the event timeline.
- Adding a new agent capability does not require rewriting the base ask endpoint.
- Tests cover retrieval planning, weak-evidence behavior, and message persistence.

## 7. Phase 4: Long-Term Planning

Goal: connect daily activity to monthly, quarterly, and yearly direction.

Build:

- Add complete `goals`, `plans`, and `plan_reviews` behavior.
- Add goal types: project, skill, career, habit, research, personal.
- Add plan horizons: monthly, quarterly, yearly.
- Add links between goals, projects, summaries, and events.
- Add monthly and quarterly review jobs.
- Add plan drift detection based on mismatch between explicit goals and actual activity.
- Add planning strategy interface so different review styles can coexist later.
- Add Plans UI with goals, plan horizon, review history, evidence, and suggested adjustments.

Core records:

```txt
goals: title, description, type, status, created_at, target_date, confidence, user_confirmed
plans: title, horizon, start_date, end_date, status, narrative, created_at, updated_at
plan_reviews: plan_id, period_start, period_end, evidence_summary, drift_summary, suggested_adjustments
```

CLI:

```txt
commitbot goal add "Get stronger at AI infra"
commitbot plan quarter
commitbot review month
commitbot review quarter
```

API:

```txt
POST /goals
GET /goals
PATCH /goals/{id}
POST /plans
GET /plans
POST /plans/{id}/review
GET /plans/{id}/reviews
```

Planning rules:

- Explicit user goals outrank inferred goals.
- Inferred goals must be labeled as inferred until confirmed.
- Long-term recommendations must cite actual activity, summaries, or review history.
- Plan updates are suggestions until the user accepts them.
- Planning strategies may evolve, but accepted plans and reviews must remain readable with their original strategy and prompt versions.

Acceptance criteria:

- User can create goals and a quarterly plan.
- Monthly review compares actual activity against plan goals.
- Agent can identify neglected goals using evidence.
- UI shows plan status and review history.
- Tests cover explicit vs inferred goals and drift detection.

## 8. Phase 5: Calendar and News Context

Goal: add useful external context while preserving approval and auditability.

Build:

- Add integration account records with encrypted tokens.
- Add Google Calendar read-only sync first.
- Add free/busy lookup for planning focus blocks.
- Add AI news fetcher through RSS or a small curated source list.
- Add morning brief job that combines calendar, recent activity, goals, and news.
- Add approval flow before calendar writes.
- Add integration registry with capability flags such as read_calendar, write_calendar, fetch_news, send_message, and update_task.

API:

```txt
GET /integrations
POST /integrations/google-calendar/connect
POST /briefs/morning
POST /agent/actions/{id}/approve
POST /agent/actions/{id}/reject
```

Tool/event records:

- `calendar.event_seen`
- `news.item_seen`
- `agent.suggestion`
- `tool.call_requested`
- `tool.call_approved`
- `tool.call_rejected`
- `tool.call_completed`

Acceptance criteria:

- Calendar read sync creates events without writing to the calendar.
- Morning brief references current goals and recent work.
- Any calendar write requires approval and creates audit events.
- Adding a new read-only integration does not require changing the approval model.
- Tests cover token absence, expired credentials, and approval gating.

## 9. Phase 6: MCP Gateway

Goal: make external tools extensible without letting the agent bypass policy.

Build:

- Add MCP client service inside `services/agent` or a dedicated gateway module.
- Add MCP server registry with name, command/config, enabled flag, allowed tools, and risk level.
- Add tool discovery endpoint.
- Add policy engine for read-only, approval-required, and denied tools.
- Add redaction step before sending sensitive context to tools.
- Add adapter layer so MCP tools and direct API integrations can share the same internal Tool interface.
- Log all MCP requests and responses through `tool_calls`.

API:

```txt
GET /tools
POST /tools/{tool_id}/call
GET /tool-calls
```

Policy defaults:

- Read-only local inspection tools may run automatically if enabled.
- File writes, calendar writes, messages, repo mutation, and network side effects require approval.
- Unknown tools are disabled by default.
- Tool results become events when they affect user-visible memory.

Acceptance criteria:

- Registered MCP tools are discoverable.
- A denied tool cannot be called by the agent.
- Approval-required tools create pending actions.
- Tool calls are visible in the timeline.
- Direct integrations and MCP tools appear through a shared tool catalog.
- Tests cover allow, deny, approval, and redaction paths.

## 10. Cross-Cutting Engineering Tasks

Testing:

- Unit tests for schemas, event validation, Git parsing, retrieval, summaries, goals, and policy.
- API tests for endpoints using a test database.
- Worker tests with deterministic fake model and fake embedding providers.
- UI smoke tests for Today, Timeline, Projects, Plans, Ask, and Reviews.

Observability:

- Structured logs for API requests, worker jobs, agent runs, and tool calls.
- Store job status for summary and embedding compilation.
- Add health endpoints for API, database, worker, and model provider configuration.

Privacy and safety:

- Keep local-first defaults.
- Do not send raw files, private diffs, or calendar details to models unless the user enables that context.
- Support deletion of user data later, but preserve append-only semantics until deletion is explicitly requested.
- Redact secrets from command outputs, environment variables, and tool results.

Prompt management:

- Version every prompt.
- Store prompt version on summaries, reviews, and agent messages.
- Allow regeneration when prompts improve.

Compatibility:

- Add `schema_version` to versioned records and event payloads that may evolve.
- Keep old event payloads readable through migration or adapter functions.
- Prefer additive schema changes for events and public APIs.
- If a component contract changes, provide a compatibility adapter for at least the previous stable version.
- Store implementation names and versions for collectors, compilers, planning strategies, retrievers, model providers, integrations, and policy decisions.

## 11. Suggested Build Order

1. Create repo structure, API, CLI, Postgres, and migrations.
2. Implement core contracts, registries, `POST /events`, `GET /events`, and `commitbot log`.
3. Add Git project detection as a registered collector and `commitbot capture git`.
4. Build Timeline and Projects API.
5. Build minimal Next.js Today and Timeline UI.
6. Add daily summary compiler and deterministic worker tests.
7. Add retriever registry, memory search, and pgvector embeddings.
8. Add agent capability registry, `commitbot ask`, and `POST /agent/ask`.
9. Add agent message persistence and evidence references.
10. Add goals, planning strategy interface, and basic Plans UI.
11. Add monthly/quarterly reviews and drift detection.
12. Add integration registry, calendar read-only sync, and morning brief.
13. Add approval flow for calendar writes.
14. Add shared tool interface, MCP gateway, and policy engine.

## 12. Definition of Done for v1

Commitbot v1 is complete when:

- A user can run the system locally.
- Manual notes and Git activity are captured as append-only events.
- The web UI shows a useful timeline and project activity.
- Daily summaries are generated from raw events.
- The ask interface answers questions about recent work using evidence.
- Goals and quarterly plans can be created and reviewed against actual activity.
- Agent suggestions are logged.
- External side effects require approval.
- The core memory model can be regenerated from raw events.
