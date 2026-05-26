create extension if not exists vector;

create table if not exists events (
  id uuid primary key,
  timestamp timestamptz not null,
  source text not null,
  type text not null,
  schema_version integer not null default 1,
  actor text not null,
  project_id uuid null,
  session_id uuid null,
  payload jsonb not null default '{}',
  metadata jsonb not null default '{}',
  summary_text text null,
  embedding vector null,
  created_at timestamptz not null
);

create index if not exists idx_events_timestamp on events(timestamp desc);
create index if not exists idx_events_type on events(type);
create index if not exists idx_events_source on events(source);
create index if not exists idx_events_payload on events using gin(payload);

create table if not exists projects (
  id uuid primary key,
  name text not null,
  root_path text null,
  repo_url text null,
  created_at timestamptz not null,
  last_seen_at timestamptz null
);

create table if not exists goals (
  id uuid primary key,
  title text not null,
  description text null,
  type text not null,
  status text not null,
  target_date date null,
  confidence real null,
  user_confirmed boolean not null default true,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists plans (
  id uuid primary key,
  title text not null,
  horizon text not null,
  start_date date not null,
  end_date date not null,
  status text not null,
  narrative text null,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists plan_reviews (
  id uuid primary key,
  plan_id uuid not null references plans(id),
  period_start date not null,
  period_end date not null,
  evidence_summary text not null,
  drift_summary text null,
  suggested_adjustments jsonb not null default '[]',
  created_at timestamptz not null
);

create table if not exists summaries (
  id uuid primary key,
  scope text not null,
  start_time timestamptz not null,
  end_time timestamptz not null,
  source_event_ids uuid[] not null default '{}',
  prompt_version text not null,
  model text not null,
  text text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null
);

create table if not exists memory_chunks (
  id uuid primary key,
  source_type text not null,
  source_id uuid not null,
  project_id uuid null,
  start_time timestamptz null,
  end_time timestamptz null,
  text text not null,
  tags text[] not null default '{}',
  embedding vector null,
  created_at timestamptz not null
);

create table if not exists agent_messages (
  id uuid primary key,
  role text not null,
  content text not null,
  retrieved_context jsonb not null default '[]',
  prompt_version text null,
  model text null,
  created_at timestamptz not null
);

create table if not exists tool_calls (
  id uuid primary key,
  tool_name text not null,
  status text not null,
  request jsonb not null default '{}',
  response jsonb null,
  policy_decision jsonb not null default '{}',
  created_at timestamptz not null,
  completed_at timestamptz null
);

create table if not exists tool_approvals (
  id uuid primary key,
  tool_call_id uuid not null references tool_calls(id),
  status text not null,
  reason text null,
  created_at timestamptz not null,
  decided_at timestamptz null
);

create table if not exists integrations (
  id uuid primary key,
  name text not null,
  provider text not null,
  enabled boolean not null default false,
  capabilities jsonb not null default '[]',
  encrypted_credentials text null,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

