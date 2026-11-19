# VerityTrail — Frontend + Supabase Implementation Guide (Taiwo's track)

**For:** Taiwo's AI coding agent. **Scope:** everything the frontend needs, plus the Supabase layer (database, security rules, storage, RPC functions) that the frontend runs on.
**Not in scope:** the AI/pipeline worker (text extraction, diff, priority rules, retrieval, AI drafts, benchmark). That belongs to the AI teammate and is specified in `VerityTrail_AI_Pipeline_Handoff.md`. This guide defines the contract between the two sides (Section 5).
**Source of truth:** `Election_Change_Radar_PRD.docx` (v2.0). The product is named **VerityTrail**. If this guide and the PRD disagree, the PRD wins; record the conflict in `docs/DECISIONS.md`.

---

## 0. How to use this document (read first, agent)

1. Execute phases **F0 → F9** in order (Section 8). Each phase ends with an exit gate of tests. Do not start the next phase until the gate is green.
2. **Build against seeded demo data first.** The AI worker will not exist on day one. Phase F4 onward works from a seeded demo run (Section 7) so the UI is complete and testable without the worker.
3. **The worker is the only writer of pipeline data.** The frontend and its RPCs never create spans, changes, or alerts. The frontend only reads them.
4. **Evidence or nothing.** Never render a claim (summary, category, match) that cannot be traced to a stored span. If data is missing, show the honest empty/unavailable state from Section 2.3.
5. **Use the exact copy strings** in Section 2.3 from a single file. Never paraphrase them.
6. One commit per task: `F<phase>: <task id> <summary>`. Tests ship with the code. Keep `docs/PROGRESS.md` updated.
7. Never commit secrets. The Supabase **service-role key is server-only** and is used in exactly one place (workspace purge, Section 6.9). Never put it in any `NEXT_PUBLIC_*` variable.
8. Don't add features outside the PRD. When the guide says "default", use it and note it in `docs/DECISIONS.md`.

---

## 1. Ownership split

| Area | Owner | Notes |
|---|---|---|
| Next.js app, six screens, Evidence Pack UI and renderers | **Taiwo (this guide)** | |
| Supabase schema, RLS, Storage policies, RPC functions, seed data, job-queue SQL | **Taiwo (this guide)** | Taiwo's agent writes the migrations because they are the contract the UI depends on. The AI teammate reviews them in Phase F0. |
| Python worker: extraction → spans, diff, priority, retrieval, AI drafts, run orchestration, benchmark | **AI teammate** | Connects to the same Supabase project using the service role. |
| Hosting of the worker, model provider, spend cap | **AI teammate + Taiwo to agree** | Open decisions D4, D9 (Section 12). |

If the PRD's backend owner (AY) is still on the team, they take the Supabase layer (Section 4) and this guide's Phase F0–F1 SQL tasks; Taiwo keeps the frontend phases.

**Interface between the two sides = Supabase tables + the `jobs` table.** The frontend creates jobs (through RPCs); the worker claims and completes them and writes results; the frontend reads results.

```
 Browser (Next.js) ──supabase-js (user session, RLS)──▶  Supabase Postgres + Storage ◀──service role / direct SQL── Python worker
       │                                                       ▲
       └── Next.js route handlers (upload, export, original download, purge) ──┘
```

---

## 2. Rules the product must obey

### 2.1 Invariants relevant to this track
| # | Invariant |
|---|---|
| INV3 | Every displayed citation/span reference resolves to a stored span of the correct version. Exports **fail** rather than emit unverifiable evidence. |
| INV4 | AI output can never set review state. Only an authenticated reviewer calling `submit_decision` can. No client code path may write review fields directly. |
| INV5 | If AI is unavailable, capped, or rejected, the diff, priority, and lexical matches still show, with **"AI summary unavailable"** (or the specific note). |
| INV6 | Never present a `partial` run as complete. |
| INV8 | Decisions are append-only; stale edits get a conflict (HTTP 409 / `PT409`); decisions never carry over to a new run. |
| INV9 | Version order is explicitly confirmed by a person. Never infer it from upload time. |
| INV10 | "No matches" is never rendered as "all current". |
| INV11 | Demo data is always badged and never presented as an official notice. |
| INV12 | Every table has RLS; every policy checks workspace membership. Cross-workspace IDs behave as not found. |

### 2.2 Product boundaries (from the PRD)
Not a legal authority ruling, not a public chatbot, no crawling, no auto-correction or publishing, no voter data, no political targeting, no claim of completeness. Never imply institutional endorsement anywhere in UI copy.

### 2.3 Required copy (single source of truth)
Create `src/lib/copy.ts`. Use exactly (including the em dash):

```ts
export const COPY = {
  POTENTIALLY_AFFECTED: "Potentially affected",
  AI_DRAFT_LABEL: "AI draft — review required",
  COMPARED_SELECTED: "Compared selected versions",
  NO_MATCHES: "No matches found in this collection",
  COVERAGE_STATEMENT: "This comparison only covers the materials you uploaded",
  AI_UNAVAILABLE: "AI summary unavailable",
  NOT_CLAIMED_TITLE: "What this tool does not claim",
  DEMO_BADGE: "Demo data",
  NO_CHANGES: "No substantive changes found between the selected versions",
} as const;

export const NOT_CLAIMED_BODY =
  "This tool compares the document versions you selected and searches only the materials you uploaded. It does not determine which document is legally authoritative, does not certify that any information is current or complete, does not publish or correct anything, and its AI drafts are suggestions for a human reviewer, not findings.";
```
Rules: never write "the latest official version" or "all materials are current" (a CI grep test enforces this). Show **published date**, **upload time**, and **comparison time** as three separately labelled values.

---

## 3. Stack, layout, environment

| Layer | Choice |
|---|---|
| App | Next.js 15 (App Router), TypeScript strict, Tailwind CSS |
| UI primitives | Radix UI via shadcn/ui (accessible dialogs, tabs, radio groups, selects) |
| Data | `@supabase/supabase-js` + `@supabase/ssr`; TanStack Query for caching and polling |
| Forms | react-hook-form + zod |
| Types | `supabase gen types typescript` → `src/lib/database.types.ts` (regenerate after every migration) |
| Backend | Supabase (Postgres 15+, Auth, Storage). Local dev with the Supabase CLI (`supabase start`) |
| Testing | Vitest + React Testing Library; Playwright; `@axe-core/playwright`; SQL/RLS tests via Vitest against local Supabase |
| Package manager | pnpm |

**Repo layout:**
```
veritytrail-web/
├─ supabase/
│  ├─ config.toml
│  ├─ migrations/           # 0001_schema.sql, 0002_rls.sql, 0003_rpc.sql, 0004_storage.sql, 0005_worker_queue.sql
│  ├─ seed.sql              # workspace + membership bootstrap (emails as placeholders)
│  └─ tests/                # RLS + RPC tests
├─ scripts/
│  └─ seed-demo.ts          # builds a demo run with correct offsets (Section 7)
├─ docs/                    # PROGRESS.md, DECISIONS.md, CONTRACT.md (copy of Section 5), TRACEABILITY.md
├─ src/
│  ├─ app/
│  │  ├─ (auth)/login/
│  │  ├─ (app)/             # layout with nav + guard
│  │  │  ├─ page.tsx                        # Overview
│  │  │  ├─ sources/ , sources/[id]/
│  │  │  ├─ collections/ , collections/[id]/
│  │  │  ├─ runs/[runId]/ , runs/[runId]/export/
│  │  │  └─ alerts/[alertId]/
│  │  └─ api/                               # uploads go browser → Storage directly (Section 6.4)
│  │     ├─ versions/[id]/original/route.ts # signed URL
│  │     ├─ comparisons/[id]/export/route.ts
│  │     └─ workspace/purge/route.ts        # only place using the service role
│  ├─ components/ , lib/ (supabase clients, copy.ts, format.ts, errors.ts, export/, queries/)
│  └─ tests/
└─ .env.local / .env.example
```

**`.env.example`:**
```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=        # server only. Used only by /api/workspace/purge
NEXT_PUBLIC_APP_NAME=VerityTrail
MAX_FILE_BYTES=10485760           # 10 MB (PRD proposed limit)
MAX_PAGES=20                      # enforced by the worker (it sets status 'rejected'); UI shows the message
MAX_SOURCE_PAIRS=10
MAX_MATERIALS=30
```
Branding: wordmark "VerityTrail" in the header, `<title>` template `"%s · VerityTrail"`, `package.json` name `veritytrail-web`.

---

## 4. Supabase layer

All SQL goes in `supabase/migrations/` and must apply cleanly with `supabase db reset`. IDs are `uuid` (default `gen_random_uuid()`), timestamps `timestamptz`.

### 4.1 Migration 0001 — schema

```sql
-- Profiles mirror auth.users
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null, display_name text
);
create function handle_new_user() returns trigger language plpgsql security definer set search_path=public as $$
begin insert into profiles(id,email,display_name) values (new.id,new.email,coalesce(new.raw_user_meta_data->>'name',split_part(new.email,'@',1))); return new; end $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function handle_new_user();

create table workspaces (
  id uuid primary key default gen_random_uuid(), name text not null,
  ai_enabled boolean not null default false,          -- admin switch; AI stays off until retention terms are documented
  created_at timestamptz not null default now(), purge_after timestamptz
);
create table workspace_members (
  workspace_id uuid references workspaces(id) on delete cascade,
  user_id uuid references profiles(id) on delete cascade,
  role text not null check (role in ('curator','reviewer','admin')),
  primary key (workspace_id, user_id)
);

create table source_documents (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  title text not null, issuer text not null, jurisdiction text not null, election_context text not null,
  source_url text,                                         -- stored as a reference, never fetched
  provenance_status text not null default 'unverified' check (provenance_status in ('unverified','verified','conflicting')),
  provenance_verified_by uuid references profiles(id), provenance_verified_at timestamptz,
  is_demo boolean not null default false,
  created_by uuid references profiles(id), created_at timestamptz not null default now()
);
create table collections (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  name text not null, election_context text not null, jurisdiction text not null,
  created_by uuid references profiles(id), created_at timestamptz not null default now()
);
create table materials (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  collection_id uuid not null references collections(id) on delete cascade,
  title text not null, owner text not null, language text not null default 'en', context text not null,
  is_demo boolean not null default false, removed_at timestamptz, created_at timestamptz not null default now()
);

create table file_blobs (
  workspace_id uuid not null references workspaces(id) on delete cascade, sha256 char(64) not null,
  storage_path text not null, size_bytes bigint not null, mime text not null,
  primary key (workspace_id, sha256)
);

create table document_versions (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  kind text not null check (kind in ('source','material')),
  source_id uuid references source_documents(id) on delete cascade,
  material_id uuid references materials(id) on delete cascade,
  declared_version text not null, published_at date,
  uploaded_at timestamptz not null default now(), uploaded_by uuid references profiles(id),
  sha256 char(64) not null, original_filename text not null, size_bytes bigint not null,
  rights_confirmed boolean not null check (rights_confirmed),   -- "public or I am authorized"
  page_count int,
  extraction_status text not null default 'pending'
    check (extraction_status in ('pending','extracting','complete','incomplete','failed','rejected')),
  extraction_message text, extractor_version text,
  full_text text,                                               -- written by worker; never selected by the frontend
  is_demo boolean not null default false, warnings jsonb not null default '[]',
  check ((kind='source' and source_id is not null and material_id is null)
      or (kind='material' and material_id is not null and source_id is null)),
  foreign key (workspace_id, sha256) references file_blobs(workspace_id, sha256)
);
create index on document_versions(source_id, uploaded_at);
create index on document_versions(material_id, uploaded_at);

create table pages (
  version_id uuid references document_versions(id) on delete cascade, page int not null,
  status text not null check (status in ('ok','blank','unreadable')), reason text,
  char_count int not null default 0, start_offset int, end_offset int,
  primary key (version_id, page)
);
create table spans (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null,
  version_id uuid not null references document_versions(id) on delete cascade,
  seq int not null, page int not null, section text, section_path text,
  start_offset int not null, end_offset int not null, raw_text text not null,
  is_heading boolean not null default false, is_boilerplate boolean not null default false,
  unique (version_id, seq), check (end_offset > start_offset)
);
create index on spans(version_id, seq); create index on spans(version_id, page);

create table comparison_runs (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  old_version_id uuid not null references document_versions(id), new_version_id uuid not null references document_versions(id),
  collection_id uuid not null references collections(id),
  collection_snapshot jsonb not null,
  order_confirmed_by uuid not null references profiles(id), order_confirmed_at timestamptz not null default now(),
  pipeline_version text, model_version text, prompt_version text,       -- set by worker when it starts
  ai_enabled boolean not null default false,                             -- copied from workspace at creation
  status text not null default 'queued' check (status in ('queued','running','partial','complete','failed')),
  stage text, progress_pct int not null default 0,
  errors jsonb not null default '[]', metrics jsonb not null default '{}',
  created_by uuid references profiles(id), created_at timestamptz not null default now(),
  started_at timestamptz, finished_at timestamptz,
  check (old_version_id <> new_version_id)
);

create table changes (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null,
  run_id uuid not null references comparison_runs(id) on delete cascade, change_key text not null,
  type text not null check (type in ('insertion','deletion','replacement')), moved boolean not null default false,
  old_span_id uuid references spans(id), new_span_id uuid references spans(id),
  old_excerpt text, new_excerpt text,
  token_ops jsonb not null default '[]', flags jsonb not null default '[]',
  categories jsonb not null default '[]', primary_category text not null default 'uncategorized',
  matched_rules jsonb not null default '[]', base_priority text not null check (base_priority in ('high','normal')),
  unique (run_id, change_key), check (old_span_id is not null or new_span_id is not null)
);
create table alerts (
  id uuid primary key, workspace_id uuid not null,
  run_id uuid not null references comparison_runs(id) on delete cascade,
  change_id uuid not null references changes(id) on delete cascade,
  material_version_id uuid not null references document_versions(id),
  passage_span_id uuid not null references spans(id),
  score real not null, confidence_band text not null check (confidence_band in ('strong','likely','uncertain')),
  match_reasons jsonb not null default '[]',
  priority text not null check (priority in ('high','normal')), priority_overridden boolean not null default false,
  ai_status text not null default 'not_run' check (ai_status in ('not_run','disabled','ok','unavailable','rejected_validation','capped')),
  ai_summary text, ai_rationale text, ai_uncertainty text, cited_span_ids jsonb not null default '[]',
  review_state text not null default 'unreviewed' check (review_state in ('unreviewed','confirmed_impact','dismissed','needs_more_information')),
  review_revision int not null default 0,
  unique (run_id, change_id, passage_span_id)
);
create index on alerts(run_id, priority, review_state);

create table review_decisions (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null,
  alert_id uuid not null references alerts(id) on delete cascade,
  kind text not null check (kind in ('review','priority_override')),
  state text, priority text,
  reason text not null check (length(btrim(reason)) >= 10),
  reviewer_id uuid not null references profiles(id), created_at timestamptz not null default now(),
  revision int not null
);
create function forbid_mutation() returns trigger language plpgsql as $$ begin raise exception 'append-only table'; end $$;
create trigger review_decisions_append_only before update or delete on review_decisions
  for each row execute function forbid_mutation();

create table jobs (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id) on delete cascade,
  type text not null check (type in ('ingest_version','run_comparison','ai_retry')),
  payload jsonb not null, status text not null default 'queued' check (status in ('queued','running','partial','complete','failed')),
  idempotency_key text, attempts int not null default 0, max_attempts int not null default 3,
  locked_by text, lease_expires_at timestamptz, run_after timestamptz not null default now(),
  progress_pct int not null default 0, stage text, last_error jsonb,
  created_at timestamptz not null default now(), finished_at timestamptz,
  unique (workspace_id, type, idempotency_key)
);
create index on jobs(status, run_after);

create table ai_cache (
  workspace_id uuid not null, cache_key char(64) not null, response jsonb not null, usage jsonb,
  created_at timestamptz not null default now(), primary key (workspace_id, cache_key)
);
create table export_events (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null,
  run_id uuid not null references comparison_runs(id) on delete cascade,
  format text not null, alert_ids jsonb not null, content_sha256 char(64) not null,
  exported_by uuid not null references profiles(id), created_at timestamptz not null default now()
);
```

**Notes.** Offsets are 0-based code-point offsets into `full_text` (matches Python string indices and Postgres character counting). `warnings` on a version holds items like `{"code":"IDENTICAL_CONTENT","message":"…","other_version_id":"…"}`.

### 4.2 Migration 0002 — RLS

```sql
create function is_member(ws uuid) returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from workspace_members m where m.workspace_id=ws and m.user_id=auth.uid()) $$;
create function has_role(ws uuid, roles text[]) returns boolean language sql stable security definer set search_path=public as $$
  select exists(select 1 from workspace_members m where m.workspace_id=ws and m.user_id=auth.uid() and m.role = any(roles)) $$;

-- Enable RLS everywhere
alter table profiles, workspaces, workspace_members, source_documents, collections, materials, file_blobs,
  document_versions, pages, spans, comparison_runs, changes, alerts, review_decisions, jobs, ai_cache, export_events
  enable row level security;

-- READ: members of the workspace can read everything in it (except ai_cache, which nobody reads from the client)
create policy r_ws on workspaces for select using (is_member(id));
create policy r_members on workspace_members for select using (is_member(workspace_id));
create policy r_profiles on profiles for select using (
  id = auth.uid() or exists(select 1 from workspace_members a join workspace_members b on a.workspace_id=b.workspace_id
                            where a.user_id=auth.uid() and b.user_id=profiles.id));
-- repeat for: source_documents, collections, materials, file_blobs, document_versions, pages, spans,
--             comparison_runs, changes, alerts, review_decisions, jobs, export_events
create policy r_<table> on <table> for select using (is_member(workspace_id));   -- generate one per table

-- DIRECT WRITES from the browser (curator/admin only)
create policy w_sources_ins on source_documents for insert with check (has_role(workspace_id, array['curator','admin']) and created_by = auth.uid());
create policy w_sources_upd on source_documents for update using (has_role(workspace_id, array['curator','admin']))
                                                   with check (has_role(workspace_id, array['curator','admin']));
create policy w_collections_ins on collections for insert with check (has_role(workspace_id, array['curator','admin']) and created_by = auth.uid());
create policy w_collections_upd on collections for update using (has_role(workspace_id, array['curator','admin']));
create policy w_materials_upd  on materials for update using (has_role(workspace_id, array['curator','admin']));  -- used only to soft-remove
create policy w_export_ins on export_events for insert with check (is_member(workspace_id) and exported_by = auth.uid());

-- Everything else (document_versions, file_blobs, jobs, runs, alerts, spans, pages, changes, decisions, ai_cache):
-- NO insert/update/delete policy for authenticated users. They are written only by SECURITY DEFINER RPCs (Migration 0003)
-- or by the worker using the service role (which bypasses RLS).
```
Also `revoke all on all tables in schema public from anon;` and ensure `anon` has no access at all. A `source_documents` update must not allow changing `workspace_id`; add a trigger `prevent_workspace_change` on tables with update policies. Provenance verification (`verified`) is only settable by curator/admin; the app sets verifier fields (`provenance_verified_by = auth.uid()`).

### 4.3 Migration 0003 — RPC functions (the only write path for protected data)

All functions: `security definer set search_path = public`, `revoke execute ... from public, anon`, `grant execute ... to authenticated` (worker-only functions go to `service_role`). **Errors use PostgREST status codes via SQLSTATE `PTxyz`**: `PT400` invalid input, `PT403` forbidden, `PT404` not found, `PT409` conflict, `PT413` capacity, `PT422` blocked. The `message` is the API error code from the table below; `detail` holds JSON.

| Error code (message) | SQLSTATE | Meaning |
|---|---|---|
| `INVALID_INPUT` | PT400 | bad arguments |
| `REASON_REQUIRED` | PT400 | decision reason under 10 trimmed characters |
| `FORBIDDEN` | PT403 | role not allowed |
| `NOT_FOUND` | PT404 | missing, or other workspace |
| `REVISION_CONFLICT` | PT409 | stale `expected_revision`; `detail` = `{"current_revision":n,"current_state":"…"}` |
| `CAPACITY_EXCEEDED` | PT413 | over source/material limits |
| `ORDER_NOT_CONFIRMED`, `CONTEXT_MISMATCH`, `VERSION_INCOMPLETE`, `SAME_VERSION`, `EMPTY_COLLECTION` | PT422 | comparison blocked; `detail` = full preflight JSON |

**(a) `build_snapshot(p_collection uuid, p_context text) returns jsonb`** (internal helper, not granted to clients). Returns the `collection_snapshot` shape:
```json
{"collection_id":"…","collection_name":"…","captured_at":"…",
 "materials":[{"material_id":"…","material_version_id":"…","title":"…","owner":"…","language":"en","sha256":"…",
               "page_count":6,"included":true,"exclusion_reason":null}]}
```
For each material with `removed_at is null`: take the **latest** version (max `uploaded_at`). `included = (extraction_status='complete' and material.context = p_context)`. Otherwise `exclusion_reason` = `EXTRACTION_INCOMPLETE` (any non-complete status) or `CONTEXT_MISMATCH`.

**(b) `preflight_comparison(p_old uuid, p_new uuid, p_collection uuid) returns jsonb`**
Returns `{"can_run":bool,"blockers":[{code,message,fix}],"warnings":[{code,message}],"snapshot":{…}}`. Requires `is_member`. Logic:
- Load both versions (`kind='source'`) and the collection, all in the caller's workspace, else `NOT_FOUND`.
- `SAME_VERSION` if `p_old = p_new`.
- `CONTEXT_MISMATCH` if the versions belong to different `source_id`s, or the source's `election_context` or `jurisdiction` differs from the collection's.
- `VERSION_INCOMPLETE` if either version's `extraction_status <> 'complete'`. The message lists the unreadable pages from `pages` (`status='unreadable'`) and the `extraction_message`; `fix` = "Upload a text-based PDF."
- `EMPTY_COLLECTION` if the snapshot has no included material.
- Warnings: `IDENTICAL_CONTENT` (same `sha256`), `PROVENANCE_UNVERIFIED` (source not `verified`), `MATERIALS_EXCLUDED` (count + reasons), `LANGUAGE_NOT_SUPPORTED_P0` (included materials whose `language <> 'en'`, informational).
- `can_run = (blockers = [])`. Never infers ordering from upload time.

**(c) `create_comparison(p_old uuid, p_new uuid, p_collection uuid, p_order_confirmed boolean, p_idempotency_key text) returns jsonb`**
Requires role curator/admin (`FORBIDDEN`). `p_order_confirmed` must be true (`ORDER_NOT_CONFIRMED`). Calls `preflight_comparison`; if blockers exist, raise the first blocker code with SQLSTATE `PT422` and the full preflight JSON in `detail`. Otherwise insert `comparison_runs` (`status='queued'`, `collection_snapshot` from preflight, `order_confirmed_by=auth.uid()`, `ai_enabled` copied from `workspaces.ai_enabled`) and a `jobs` row `(type='run_comparison', payload={"run_id":…}, idempotency_key=p_idempotency_key)`. If a job with the same `(workspace_id,'run_comparison',key)` exists, return the existing `{run_id, job_id}` instead (idempotent). Returns `{"run_id":…,"job_id":…}`.

**(d) `register_source_version(p_source uuid, p_declared_version text, p_published_at date, p_sha256 text, p_filename text, p_size bigint, p_mime text, p_rights_confirmed boolean, p_is_demo boolean) returns jsonb`**
Role curator/admin. Source must be in the caller's workspace. Upsert `file_blobs` (`storage_path = workspace_id || '/' || sha256`). Insert `document_versions` (kind `source`, `extraction_status='pending'`). If another version of the same source has the same `sha256`, add warning `IDENTICAL_CONTENT` to the new row's `warnings` (do **not** reuse the old version; AC01 needs identical pairs to be comparable). Insert `jobs` `(ingest_version, {"version_id":…})`. Returns `{"version_id","job_id","warnings"}`.

**(e) `register_material_version(p_collection uuid, p_material uuid /*null for new*/, p_title text, p_owner text, p_language text, p_context text, p_declared_version text, p_sha256 text, p_filename text, p_size bigint, p_mime text, p_rights_confirmed boolean, p_is_demo boolean) returns jsonb`**
Role curator/admin. If `p_material` is null: create a `materials` row (capacity check: active materials in the workspace ≤ 30 else `CAPACITY_EXCEEDED`). If a **non-removed** version of any material **in the same collection** already has the same `sha256`, return `{"deduplicated":true,"material_id","version_id"}` and create nothing. Otherwise insert the version (`kind='material'`) + `ingest_version` job. Returns `{"material_id","version_id","job_id","deduplicated":false}`.
`register_source_version` also enforces source count ≤ 10 when the source itself is created (check in a `before insert` trigger on `source_documents`).

**(f) `submit_decision(p_alert uuid, p_state text, p_reason text, p_expected_revision int) returns jsonb`** — implement exactly:
```sql
create or replace function submit_decision(p_alert uuid, p_state text, p_reason text, p_expected_revision int)
returns jsonb language plpgsql security definer set search_path = public as $$
declare a alerts%rowtype; new_rev int; d_id uuid := gen_random_uuid();
begin
  if p_state not in ('confirmed_impact','dismissed','needs_more_information') then
    raise exception 'INVALID_INPUT' using errcode = 'PT400'; end if;
  if length(btrim(coalesce(p_reason,''))) < 10 then
    raise exception 'REASON_REQUIRED' using errcode = 'PT400'; end if;
  select * into a from alerts where id = p_alert for update;
  if not found or not is_member(a.workspace_id) then
    raise exception 'NOT_FOUND' using errcode = 'PT404'; end if;
  if not has_role(a.workspace_id, array['curator','reviewer','admin']) then
    raise exception 'FORBIDDEN' using errcode = 'PT403'; end if;
  if a.review_revision <> p_expected_revision then
    raise exception 'REVISION_CONFLICT' using errcode = 'PT409',
      detail = jsonb_build_object('current_revision', a.review_revision, 'current_state', a.review_state)::text;
  end if;
  new_rev := a.review_revision + 1;
  update alerts set review_state = p_state, review_revision = new_rev where id = p_alert;
  insert into review_decisions(id, workspace_id, alert_id, kind, state, reason, reviewer_id, revision)
  values (d_id, a.workspace_id, p_alert, 'review', p_state, btrim(p_reason), auth.uid(), new_rev);
  return jsonb_build_object('decision_id', d_id, 'review_revision', new_rev, 'review_state', p_state);
end $$;
```
**(g) `override_priority(p_alert uuid, p_priority text, p_reason text, p_expected_revision int)`** — same pattern; sets `alerts.priority`, `priority_overridden=true`, bumps `review_revision`, inserts a `review_decisions` row with `kind='priority_override'`, `priority=p_priority`.

**(h) `request_ai_retry(p_alert uuid) returns jsonb`** — role curator/reviewer/admin; only when `ai_status in ('unavailable','capped')` and the workspace has `ai_enabled`; inserts a `jobs` row `(ai_retry, {"alert_id":…}, idempotency_key = 'ai_retry:'||p_alert||':'||date_trunc('minute', now()))`.

**(i) `verify_spans(p_span_ids uuid[]) returns table(span_id uuid, ok boolean)`** — for each span in the caller's workspace: `ok = substr(v.full_text, s.start_offset + 1, s.end_offset - s.start_offset) = s.raw_text`. Used by exports (INV3).

**(j) `get_span_context(p_span uuid) returns jsonb`** — returns the span, the previous and next spans (`seq ± 1` in the same version), the page's `status`, the version's title/declared version/published date/is_demo. Used by the evidence drawer.

**(l) `request_run_retry(p_run uuid) returns jsonb`** — role curator/admin; the run must be `failed` or `partial`. Sets the run's `status='queued'`, `stage=null`, `progress_pct=0`, and inserts a `jobs` row `(run_comparison, {"run_id":…}, idempotency_key = 'retry:'||p_run||':'||extract(epoch from now())::bigint)`. The worker's stages are idempotent (deterministic change keys and alert IDs), so a retry never duplicates alerts.

**(k) Worker-only (grant to `service_role`):**
```sql
create or replace function claim_job(p_worker text, p_lease_seconds int default 60)
returns setof jobs language sql security definer set search_path = public as $$
  update jobs set status='running', locked_by=p_worker, attempts=attempts+1,
         lease_expires_at = now() + make_interval(secs => p_lease_seconds)
  where id = (select id from jobs
              where (status='queued' and run_after <= now())
                 or (status='running' and lease_expires_at < now() and attempts < max_attempts)
              order by created_at for update skip locked limit 1)
  returning *;
$$;
create or replace function sweep_dead_jobs() returns int language sql security definer set search_path=public as $$
  with d as (update jobs set status='failed', finished_at=now(),
                    last_error = jsonb_build_object('code','LEASE_EXPIRED_MAX_ATTEMPTS')
             where status='running' and lease_expires_at < now() and attempts >= max_attempts returning 1)
  select count(*)::int from d; $$;
revoke execute on function claim_job(text,int), sweep_dead_jobs() from public, anon, authenticated;
grant  execute on function claim_job(text,int), sweep_dead_jobs() to service_role;
```
Heartbeat/finish are plain `UPDATE jobs` statements run by the worker.

### 4.4 Migration 0004 — Storage
Private bucket `documents` (public = false). Object path: `{workspace_id}/{sha256}` (no filename, no extension).
```sql
insert into storage.buckets (id, name, public, file_size_limit) values ('documents','documents', false, 10485760) on conflict do nothing;
create policy "documents_read"   on storage.objects for select using (bucket_id='documents' and is_member(((storage.foldername(name))[1])::uuid));
create policy "documents_insert" on storage.objects for insert with check (bucket_id='documents'
        and has_role(((storage.foldername(name))[1])::uuid, array['curator','admin']));
-- no update/delete policies (objects are immutable); purge uses the service role.
```

### 4.5 Migration 0005 — seed / bootstrap
`supabase/seed.sql`: create one workspace "VerityTrail Team"; after the three teammates sign in once, add memberships by email:
```sql
insert into workspace_members(workspace_id, user_id, role)
select w.id, p.id, r.role from workspaces w
join (values ('curator@example.com','curator'),('reviewer@example.com','reviewer'),('admin@example.com','admin')) as r(email, role) on true
join profiles p on p.email = r.email where w.name = 'VerityTrail Team' on conflict do nothing;
```
Auth: email + password, **public sign-ups disabled** in the Supabase dashboard; the admin creates users there. A signed-in user with no membership sees an "Ask an admin to add you" page.

---

## 5. The contract with the AI worker (freeze in Phase F0)

Copy this section to `docs/CONTRACT.md`. **Any change to it needs both teammates' agreement and a migration.** The frontend must tolerate missing optional fields.

### 5.1 Jobs
The frontend creates jobs only through RPCs. The worker claims them with `claim_job(worker_id, lease)`.

| Job `type` | Created by | `payload` | Worker does |
|---|---|---|---|
| `ingest_version` | `register_source_version`, `register_material_version` | `{"version_id": uuid}` | Download `documents/{workspace_id}/{sha256}`; **recompute SHA-256 and compare** with `document_versions.sha256` (mismatch → `rejected`, message `HASH_MISMATCH`); validate (≤ 20 pages, not encrypted, no active content, valid PDF or strict UTF-8); extract; write `pages`, `spans`, `full_text`, `page_count`, `extractor_version`; set `extraction_status` and `extraction_message`. Idempotent (delete and rewrite that version's pages/spans in one transaction). |
| `run_comparison` | `create_comparison` | `{"run_id": uuid}` | Run the stages in 5.3; write `changes` and `alerts`; keep `comparison_runs` and the `jobs` row current. |
| `ai_retry` | `request_ai_retry` | `{"alert_id": uuid}` | Re-run only the AI step for that alert; update its `ai_*` fields; keep the run's final status truthful. |

Job `status` values: `queued → running → complete | partial | failed`. Worker heartbeats extend `lease_expires_at`; failures retry up to `max_attempts`.

### 5.2 `document_versions.extraction_status`
| Value | Meaning | UI |
|---|---|---|
| `pending` | waiting for worker | "Queued" chip |
| `extracting` | in progress | "Extracting…" with spinner (text label too) |
| `complete` | all pages readable | green-independent "Ready" chip |
| `incomplete` | some pages unreadable (`pages.status='unreadable'`) | page grid + `extraction_message`; **blocks comparison** (source) or excludes the material |
| `failed` | extraction error | message + "Upload again" |
| `rejected` | validation failed (too many pages, encrypted, active content, bad hash, invalid text) | message from `extraction_message`, written to be actionable |

`extraction_message` is shown verbatim to the user, so it must be plain, actionable English, e.g. `Pages 4, 7 contain no extractable text (likely scanned). Upload a text-based PDF.`

### 5.3 Run lifecycle (`comparison_runs`)
Worker sets `status='running'`, `started_at`, `pipeline_version`, `model_version`, `prompt_version` on start. It updates `stage` and `progress_pct` at each stage end:

| `stage` | `progress_pct` at end |
|---|---|
| `validate` | 5 |
| `prepare` | 15 |
| `diff` | 40 |
| `priority` | 50 |
| `retrieve` | 75 |
| `ai` | 95 |
| `finalize` | 100 |

Final `status` and `finished_at`: `complete` only if every stage succeeded (or AI was intentionally off: `ai_enabled=false`); `partial` if any per-change retrieval error occurred or the AI step was unavailable/capped; `failed` if stages `validate`…`priority` failed. `errors` is an array of `{"stage","code","message","change_key"?}`. Known codes: `AI_UNAVAILABLE`, `AI_CAPPED`, `PER_CHANGE_FAILURE`, `STAGE_FAILED`.

`metrics` (frontend reads defensively; any key may be missing):
```json
{"counts":{"changes":5,"by_type":{"replacement":3,"deletion":1,"insertion":1},"alerts":4,"moved":0,
           "by_category":{"deadlines_timelines":2,"required_documents":1,"uncategorized":1,"cvr_transfer":1}},
 "stage_durations_ms":{"validate":40,"prepare":300,"diff":900,"priority":50,"retrieve":1200,"ai":4000,"finalize":20},
 "candidates_per_change":{"<change_id>":3},
 "ai":{"calls":4,"cached":0,"rejected":1,"input_tokens":3200,"output_tokens":600,"est_usd":0.03}}
```

### 5.4 Data shapes the UI renders
**Category IDs → labels:**
`deadlines_timelines` "Deadlines & Timelines" · `eligibility` "Eligibility Criteria" · `required_documents` "Required Documents (PVC, forms, etc.)" · `polling_unit_accreditation` "Polling Unit & Accreditation Procedures" · `cvr_transfer` "CVR / Transfer Rules" · `uncategorized` "Uncategorized". `changes.categories` is an ordered array of these IDs; `primary_category` is the first (or `uncategorized`).

**Flags → text chips:** `date_change` "Date changed" · `number_change` "Number changed" · `modal_flip` "Obligation wording changed" · `negation_flip` "Negation changed".

**`changes.old_excerpt` / `new_excerpt`** equal the raw text of `old_span_id` / `new_span_id` exactly, so highlight offsets apply to them. `NULL` on the missing side of insertions/deletions.

**`changes.token_ops`** — offsets are character offsets **relative to the span's `raw_text`**; for an insertion `old` is an empty range at the insertion point; for a deletion `new` is empty:
```json
[{"op":"replace","old":{"text":"31 December 2026","start":58,"end":74},"new":{"text":"15 January 2027","start":58,"end":73}}]
```
**`changes.matched_rules`:** `[{"rule_id":"DL-01","category":"deadlines_timelines","matched_text":"until","side":"old","start":55,"end":60}]`.

**`alerts.match_reasons`** — offsets relative to the **passage span's `raw_text`**:
```json
[{"type":"repeats_old_value","text":"31 December 2026","passage_start":29,"passage_end":45}]
```
Types: `repeats_old_value` "Repeats the earlier value", `old_wording_overlap` "Overlaps the earlier wording", `shared_category_terms` "Shares key terms", `topic_related` "Related topic (new requirement in the newer version)", `semantic` "Semantically similar".
`confidence_band`: `strong` / `likely` / `uncertain` (display "Uncertain match — review carefully"). `score` is a ranking aid only; the UI must say so.

**AI fields:** when `ai_status='ok'`, `ai_summary`, `ai_rationale` are set, `ai_uncertainty` is optional, `cited_span_ids` is a non-empty array of span IDs that the worker has already validated. For any other `ai_status` those text fields are null. UI wording per status: `ok` → label **AI draft — review required**; `unavailable` → **AI summary unavailable** + retry (if workspace AI enabled); `rejected_validation` → "AI draft was withheld because it could not be verified against the source text."; `capped` → "AI draft skipped: usage limit reached for this run."; `disabled`/`not_run` → no AI block, only the note "AI drafts are off for this run."

**Alert IDs** are deterministic UUIDv5 values made by the worker, so retries never duplicate alerts (INV7).

### 5.5 Who may write what
| Table | Browser (RLS) | RPC | Worker (service role) |
|---|---|---|---|
| source_documents, collections | insert/update (curator, admin) | | |
| materials | update (soft remove) | `register_material_version` inserts | |
| file_blobs, document_versions | none | `register_*` | updates extraction fields, `full_text`, `warnings` |
| pages, spans, changes | none | | insert |
| comparison_runs | none | `create_comparison` | all progress/status fields |
| alerts | none | `submit_decision`, `override_priority` (review/priority fields only) | insert; `ai_*`, `cited_span_ids` |
| review_decisions | none | `submit_decision`, `override_priority` | **never** |
| jobs | none | RPCs create | claim/heartbeat/finish |
| ai_cache | none | | all |
| export_events | insert | | |

The worker must **never** write `review_state`, `review_revision`, `priority_overridden` or `review_decisions` (INV4).

---

## 6. Frontend specification

### 6.1 Supabase clients and auth
- `lib/supabase/browser.ts` (`createBrowserClient`), `lib/supabase/server.ts` (`createServerClient` with cookies), `middleware.ts` refreshes the session and redirects unauthenticated users to `/login`.
- `/login`: email + password form with labelled inputs and accessible error text. No sign-up link.
- `(app)/layout.tsx` loads the user's membership (`workspace_members` + `workspaces`). No membership → "You're signed in but not part of a workspace. Ask an admin to add you." Provide `useSession()` returning `{user, workspace, role}`; hide actions the role cannot use (RLS/RPCs still enforce).

### 6.2 Error handling
`lib/errors.ts` maps any Supabase/PostgREST error to `{code, message, retryable, details, requestId}`: for `PTxyz` errors `code = error.message`, `details = JSON.parse(error.details ?? 'null')`. Show human text per code:

| Code | Text |
|---|---|
| `FILE_TOO_LARGE` | "This file is larger than 10 MB. Compress it or split it." |
| `UNSUPPORTED_MEDIA` | "Only text-based PDF and UTF-8 text files are supported." |
| `CAPACITY_EXCEEDED` | "The workspace has reached its limit (10 sources / 30 materials)." |
| `REASON_REQUIRED` | "Add a reason of at least 10 characters." |
| `REVISION_CONFLICT` | opens the conflict dialog (6.7) |
| `ORDER_NOT_CONFIRMED` | "Confirm which version is earlier and which is later." |
| `CONTEXT_MISMATCH`, `VERSION_INCOMPLETE`, `SAME_VERSION`, `EMPTY_COLLECTION` | text from the preflight blocker (`message` + `fix`) |
| `FORBIDDEN` | "Your role can't do this." |
| other | "Something went wrong. Try again." with a "Copy details" button |

### 6.3 Data access (supabase-js `select` strings)
All lists live behind TanStack Query hooks in `lib/queries/*`. **Never select `document_versions.full_text`.** Define `VERSION_COLS = "id,kind,source_id,material_id,declared_version,published_at,uploaded_at,sha256,original_filename,size_bytes,page_count,extraction_status,extraction_message,is_demo,warnings"`.

- **Source detail:** `source_documents` + `document_versions(${VERSION_COLS})` ordered by `uploaded_at`; page grids from `pages` (`version_id`, `page`, `status`, `reason`).
- **Collection detail:** `collections` + `materials(*, document_versions(${VERSION_COLS}))`.
- **Run header:** `comparison_runs` with `old:document_versions!old_version_id(${VERSION_COLS}, source:source_documents(title,issuer,jurisdiction,election_context,provenance_status))`, `new:document_versions!new_version_id(...)` and `collection:collections(name)`.
- **Inbox:** all `changes` for the run (`run_id=eq.X`, paginate with `.range()` in blocks of 1000) plus all `alerts` for the run with `material_version:document_versions!material_version_id(declared_version, material:materials(title,owner,language))` and `passage:spans!passage_span_id(raw_text,page)`. Filter in the browser (data volumes are small: ≤ 10 pairs × hundreds of changes). Keep filters in the URL query string.
- **Alert detail:** `alerts` with `change:changes!change_id(*, old_span:spans!old_span_id(*), new_span:spans!new_span_id(*))`, `passage:spans!passage_span_id(*)`, `material_version:document_versions!material_version_id(${VERSION_COLS}, material:materials(*))`; decisions from `review_decisions` (`alert_id`, order by `created_at desc`) with `reviewer:profiles!reviewer_id(display_name,email)`.
- **Counts:** use `{ count: 'exact', head: true }` for unreviewed alerts and similar.

Polling: use `refetchInterval` of 1500 ms while any displayed version is `pending|extracting` or a run is `queued|running`, easing to 5000 ms after 30 s, and stopping otherwise. Show feedback within 2 s of any submit (optimistic "Queued").

### 6.4 Upload flow (browser → Storage → RPC)
1. `FileDropzone` (drag-drop **and** a real keyboard-focusable button; status announced via `aria-live="polite"`).
2. Client checks (UX only, the worker re-validates): size ≤ `MAX_FILE_BYTES` → else show `FILE_TOO_LARGE`; first bytes `%PDF-` or strict UTF-8 text (`new TextDecoder('utf-8',{fatal:true})`, no NUL bytes) → else `UNSUPPORTED_MEDIA`.
3. Compute SHA-256 with `crypto.subtle.digest`; hex-encode.
4. Upload to bucket `documents` at `${workspaceId}/${sha256}` with `upsert:false` and a fixed content type (`application/pdf` or `text/plain`). If the object already exists, treat that as a successful dedupe and continue.
5. Call `register_source_version` or `register_material_version` (Section 4.3) with the metadata and the "These files are public or I am authorized to use them" checkbox as `p_rights_confirmed` (required; the form blocks submit without it).
6. Show the new version row immediately as **Queued** and start polling. Display RPC warnings (`IDENTICAL_CONTENT`, `deduplicated`).
7. The worker is authoritative on content validity; a bad file ends as `rejected` with its message.

### 6.5 Accessibility and layout rules (NFR04)
Keyboard operability everywhere; visible focus ring (≥ 3:1); skip-to-content link; semantic landmarks; one `h1` per page and ordered headings; labelled inputs with `aria-describedby` for errors; Radix dialogs with focus trap and focus return; tables with `<th scope>`; text contrast ≥ 4.5:1; honour `prefers-reduced-motion`; `aria-live="polite"` for job progress. **Never use color alone:** change type (Added / Removed / Changed), priority (High / Normal), status, flags and highlights always carry text (and an icon). Target WCAG 2.2 AA patterns; do not claim certification.

### 6.6 Routes and screens

| Route | Screen |
|---|---|
| `/` | Overview |
| `/sources`, `/sources/[id]` | Sources & Uploads |
| `/collections`, `/collections/[id]` | Material Collection |
| `/runs/[runId]` | Comparison & Inbox |
| `/alerts/[alertId]` | Evidence & Decision |
| `/runs/[runId]/export` | Export & Run Details |

Primary nav: Overview · Sources · Collection · Inbox (opens the latest run) · Export.

**Overview.** Election context(s), source pairs (title, versions count), collection count, latest runs with status chips, unreviewed-alert count (High first), the coverage sentence ("Coverage is limited to the versions and materials you selected"), a retention note ("Workspace data is kept until `purge_after`"), and the **What this tool does not claim** panel.

**Sources & Uploads.**
- Create-source form (title, issuer, jurisdiction, election context required; URL optional; stored as text and rendered as a plain link with `rel="noopener noreferrer nofollow"`). Provenance control (curator/admin): unverified / verified / conflicting; "verified" records verifier and time.
- Version upload (Section 6.4). Version table: label, short hash, page count, **Published date**, **Uploaded**, extraction status chip, warnings, and a `PageCoverageGrid` (one cell per page with text status `ok / blank / unreadable` and tooltip reason).
- **Pair picker**: Earlier version, Later version, Collection, checkbox "I confirm the earlier/later order". On every change (debounced 300 ms) call `preflight_comparison`; list blockers (each with its recovery text) and warnings. **Compare** is disabled until `can_run` and the confirmation is ticked. Submit calls `create_comparison` with a client-generated idempotency key (reuse the same key across retries of the same click) and navigates to `/runs/[runId]`.

**Material Collection.** Create-collection form; material upload form (title, owner, language, context, rights checkbox); table of materials with latest version, status, language tag, and an **Included in next run?** column computed from the same rules as `build_snapshot` (call `preflight_comparison` result or mirror the logic) with the exclusion reason. "Remove" (soft) allowed only before any run snapshots it; if blocked show "This material is part of an earlier comparison and can't be removed." (the UI checks `comparison_runs.collection_snapshot` for the material ID).

**Comparison & Inbox (`/runs/[runId]`).**
- `ScopeBanner`: election context, old → new version (declared label, **published**, **uploaded**), **compared** time, materials included count, "Compared selected versions".
- Status banner: `queued`/`running` (progress bar + stage name, `aria-live`), `partial` (what's missing from `errors`, with a **Retry run** button for curator/admin and per-alert AI retry), `failed` (error + a **Retry run** button for curator/admin that calls `request_run_retry`), `complete`.
- Filters (URL-synced): priority, category (5 + uncategorized), review state, confidence band, has matches.
- Rows grouped by change: category label, type label (**Added in newer version** / **Removed in newer version** / **Changed**), flag chips, before/after snippet with highlights, priority badge, candidate count, review state. Expanding a row lists its alerts: material title/owner, quoted passage, confidence band, "Potentially affected", and a link to `/alerts/[id]`.
- Distinct, explicit states: loading; `queued/running`; **no changes** (`NO_CHANGES`); change with zero alerts → **"No matches found in this collection"** plus materials-included count and run time; partial; failed. Never "all current".

**Evidence & Decision (`/alerts/[alertId]`).**
- Three panes: **A Old wording** (earlier version), **B New wording** (later version), **C Potentially affected passage**. On narrow screens they become Radix Tabs (still keyboard accessible).
- Each pane header: document title, version label, page number as a button "View original page" that opens the **evidence drawer** (page spans from `get_span_context` with the target highlighted) and a "View original file" (signed URL, opens at `#page=N`) / "Download original" action.
- Highlighting (`DiffText`): take the span text and a list of `{start,end,kind}`; build segments; render `<mark>` with **text styling and screen-reader text** (removed: bold + strikethrough + visually hidden "[removed: …]"; added: bold + underline + hidden "[added: …]"; matched passage terms: underline + hidden "[matched: …]"). Include a visible legend. Validate offsets (`0 ≤ start < end ≤ text.length`) and skip invalid ranges rather than crash.
- Match box: reasons (labels from 5.4), confidence band, and the sentence "Match score is a ranking aid, not the probability that a correction is needed."
- `AiDraftBlock` per Section 5.4. Cited spans render as buttons that open the evidence drawer. The block is visually distinct from verified evidence.
- `DecisionForm`: radio group (Confirmed impact / Dismissed / Needs more information), required reason textarea (≥ 10 chars), submit calls `submit_decision` with `expected_revision` from the loaded alert. Disabled while pending. Success refetches the alert and history.
- Priority override: select High/Normal + reason → `override_priority`.
- `DecisionHistory`: newest first, with reviewer, state/priority change, reason, timestamp.
- Footer: link to **What this tool does not claim**.

**Export & Run Details (`/runs/[runId]/export`).** Run scope (old/new versions with published/uploaded/compared times, collection snapshot with included **and excluded** materials and reasons, pipeline/model/prompt versions, stage timings, errors, AI usage), the alert table with checkboxes (default: all `confirmed_impact`), selected count, a warning when selection includes unreviewed alerts or the run is `partial`, and buttons: **Download Evidence Pack (HTML)**, **Print / Save as PDF** (opens the inline brief; the user prints from the browser), **CSV**, **JSON**.

### 6.7 Conflict handling (FR10, AC04)
On `REVISION_CONFLICT` open `ConflictDialog`: "This alert changed since you opened it." Show the current state/revision from `details`, refetch the history and display the newer decision(s). Keep the user's typed reason. Buttons: "Review latest and re-submit" (reload alert, keep reason, set the new `expected_revision`) and "Cancel". Never overwrite silently.

### 6.8 Export (FR11) — route `/api/comparisons/[id]/export`
Runs on the server with the **user's session** (RLS applies; other-workspace run → 404). Accepts `GET` (`format`, `alert_ids` comma list ≤ 50, `disposition=inline|attachment`) and `POST` (JSON `{format, alert_ids}`) for larger selections.

Steps: (1) load run, snapshot, versions, selected alerts with their change/spans/material/decisions; (2) collect every span ID that will be shown (change old/new, passage, `cited_span_ids`) and call `verify_spans`; **if any is false, abort with `EVIDENCE_UNVERIFIABLE`** (HTTP 500, nothing emitted); (3) build the `EvidencePack` object; (4) render; (5) write an `export_events` row with the SHA-256 of the produced bytes; (6) respond with `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, and `Content-Disposition: attachment; filename="veritytrail-evidence-pack-<run8>.<ext>"` (or `inline` for print preview).

**`EvidencePack` (schema_version "1")** — all formats render from this single object so they cannot disagree:
```json
{
  "schema_version": "1", "product": "VerityTrail", "pack_id": "uuid",
  "generated_at": "ISO-8601 UTC", "generated_by": {"user_id": "…", "name": "…"},
  "coverage_statement": "This comparison only covers the materials you uploaded",
  "not_claimed": "…NOT_CLAIMED_BODY…",
  "run": {"run_id":"…","status":"complete|partial","compared_at":"…","pipeline_version":"…","model_version":null,"prompt_version":null,
    "old_version":{"version_id":"…","title":"…","issuer":"…","declared_version":"v1","published_at":null,"uploaded_at":"…","sha256":"…","is_demo":false},
    "new_version":{"…":"…"}, "election_context":"…", "jurisdiction":"…",
    "collection":{"name":"…","materials_included":[{"title":"…","owner":"…","sha256":"…"}],
                  "materials_excluded":[{"title":"…","reason":"…"}]}},
  "alerts":[{
    "alert_id":"…","change_id":"…","priority":"high","priority_overridden":false,
    "category":"deadlines_timelines","category_label":"Deadlines & Timelines","flags":["date_change"],
    "old_wording":{"span_id":"…","page":1,"section":"…","text":"…","highlights":[{"start":58,"end":74}]},
    "new_wording":{"span_id":"…","page":1,"section":"…","text":"…","highlights":[{"start":58,"end":73}]},
    "affected_passage":{"span_id":"…","material_title":"…","material_owner":"…","material_sha256":"…","page":1,"text":"…","quote":"…","highlights":[{"start":29,"end":45}]},
    "match":{"confidence_band":"strong","score":0.82,"reasons":[]},
    "ai_draft":{"label":"AI draft — review required","status":"ok","summary":"…","rationale":"…","uncertainty":null,"cited_span_ids":["…"]},
    "review":{"state":"confirmed_impact","reason":"…","reviewer":"…","decided_at":"…","revision":1,
              "history":[{"state":"…","reason":"…","reviewer":"…","at":"…"}]}}]
}
```
When `ai_status != 'ok'`: `"ai_draft": {"status":"unavailable|rejected_validation|capped|disabled|not_run","label":"AI summary unavailable"}` with no text fields. Unreviewed alerts export with `review.state = "unreviewed"`. This covers every PRD-required export field: IDs, old vs new wording with page references, affected passage quote, labelled AI draft, reviewer decision/reason/timestamp, and the coverage statement.

**CSV.** One row per alert; columns `alert_id, change_id, priority, category, flags, old_page, old_wording, new_page, new_wording, material_title, material_owner, material_page, affected_passage_quote, match_confidence, ai_draft_label, ai_draft_summary, review_state, review_reason, reviewer, decided_at, run_id, old_version_sha256, new_version_sha256, coverage_statement`. UTF-8 with BOM, CRLF line endings, RFC 4180 quoting. **Formula-injection guard** applied to every string cell:
```ts
export function csvSafe(v: unknown): string {
  let s = v == null ? "" : String(v);
  if (/^[\s]*[=+\-@\t\r]/.test(s)) s = "'" + s;       // neutralise spreadsheet formulas
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
```
Unit-test with `=HYPERLINK("http://x","y")`, `+cmd|' /C calc'!A0`, `@SUM(1+1)`, `-2+3`, and a leading-space `' =1+1'` case.

**HTML brief.** Render with React `renderToStaticMarkup(<EvidenceBrief pack={pack}/>)` (auto-escaped) inside a full HTML document with inline CSS only and no scripts or external requests. Response header `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`. Structure: (1) "VerityTrail — Material Owner Evidence Pack", pack ID, generated time/by; (2) banner with the exact coverage statement and "Compared selected versions" (plus a visible warning if the run is `partial`); (3) scope table: election context, issuer, old/new version (label, **published**, **uploaded**, hash), **compared** time, materials included/excluded, pipeline/model versions, **Demo data** badge when relevant; (4) one card per alert: priority + category (text), flag chips, Old vs New wording with page refs and highlights, "Potentially affected" passage (quote, material, owner, page), the **AI draft — review required** block (or "AI summary unavailable"), the reviewer decision (state, reason, reviewer, timestamp), alert ID; (5) footer: **What this tool does not claim**. Print CSS: A4, page break between alerts, repeating header with pack ID. Highlights use `<mark>` plus visible `[[…]]` markers so they survive black-and-white printing.

**JSON.** The pack object, validated against a committed JSON Schema (`src/lib/export/pack.schema.json`) in tests.

### 6.9 Original-file access and purge
- `GET /api/versions/[id]/original?download=1`: fetch the version with the user session (404 if not visible), then `createSignedUrl(path, 60, { download: download ? filename : undefined })` and redirect. Never expose permanent public URLs.
- `POST /api/workspace/purge` (the **only** use of `SUPABASE_SERVICE_ROLE_KEY`): verify the caller is an `admin` of the workspace through their user session; require `{confirm: "<workspace name>"}`; with the service client list and remove every object under `{workspace_id}/` in `documents` (paginate), then call `purge_workspace_data(workspace_id)` (Migration 0006: service-role-only SQL that sets `set_config('veritytrail.purging','on',true)` and deletes in dependency order: `export_events`, `ai_cache`, `review_decisions`, `alerts`, `changes`, `comparison_runs`, `jobs`, `spans`, `pages`, `document_versions`, `file_blobs`, `materials`, `collections`, `source_documents`). Migration 0006 also redefines `forbid_mutation()` to allow changes only while that setting is `on`. After it finishes, verify zero rows remain and zero storage objects remain.
- Retention: `workspaces.purge_after` defaults to `now() + interval '30 days'` (proposed, D6). Optional: a scheduled call to a protected `/api/cron/purge` route (header `CRON_SECRET`) that purges expired workspaces.

### 6.10 Components to build once and reuse
`ScopeBanner`, `NotClaimedPanel`, `StatusChip` (icon + text), `PriorityBadge`, `ChangeTypeLabel`, `FlagChips`, `CategoryLabel`, `DemoBadge`, `PageCoverageGrid`, `DiffText`, `EvidencePane`, `EvidenceDrawer`, `AiDraftBlock`, `DecisionForm`, `DecisionHistory`, `ConflictDialog`, `JobProgress`, `FileDropzone`, `PairPicker`, `PreflightList`, `AlertTable`, `EmptyState`, `ErrorState`, `EvidenceBrief` (export).

---

## 7. Demo seed (build the UI without the worker)

`scripts/seed-demo.ts` (run with `pnpm tsx scripts/seed-demo.ts`, service-role key, dev only) inserts a complete, **Demo data**-badged scenario that exercises every UI state. Every demo source/material/version has `is_demo = true`, and the demo documents are plain text stamped in their titles with "DEMO". It also sets `workspaces.ai_enabled = true` for the demo workspace so AI states and retry buttons are visible. `--reset` (requires `ALLOW_DEMO_RESET=1`) calls `purge_workspace_data` and re-seeds.

### 7.1 Scenario content

**Source:** "DEMO Continuous Voter Registration Guidelines", issuer "Demo Issuer", jurisdiction "Nigeria (Demo)", context "Demo election cycle". Provenance `unverified`.

| Version | Page 1 | Page 2 |
|---|---|---|
| **v1** (earlier, published 2026-09-01) | H "1. Continuous Voter Registration" · "Eligible citizens may register to vote at any registration centre until 31 December 2026." · H "2. Eligibility" · "A person must be at least 18 years old and a citizen of Nigeria to register." | H "3. Collection of PVC" · "Registered voters must collect their Permanent Voter's Card within 30 days of notification." · H "4. Accreditation" · "Voters must present their PVC for accreditation before voting." · "Voters may be accompanied by one companion while waiting." |
| **v2** (later, published 2026-11-10) | same, but the date reads **15 January 2027** | same, but **60 days**; accreditation sentence becomes "Voters must present their PVC **and a valid form of identification** for accreditation before voting."; the companion sentence is **removed**; new H "5. Transfer of registration" + "Voters who have moved may apply for transfer of registration during the registration window." |
| **v2b** | an identical copy of v2 (same bytes → same blob; carries `IDENTICAL_CONTENT` warning) used for the "no changes" run | |

**Collection** "DEMO Civic collection" (context "Demo election cycle"):
- M1 "DEMO Register Now flyer" (owner "Demo Civic Group"): "Register to vote before 31 December 2026 at any registration centre." · "Bring your friends and family along."
- M2 "DEMO Voter Handbook (excerpt)" (owner "Demo Media House"): "After registration, collect your PVC within 30 days of notification." · "At the polling unit, present your PVC for accreditation before you vote."
- M3 "DEMO Media Guide (excerpt)" (owner "Demo Newsroom"): "Voters may be accompanied by one companion while waiting." · "Election coverage should always name the source of results."
- Excluded examples: M4 "DEMO Other-context handbook" (context "Another election context" → `CONTEXT_MISMATCH`); M5 "DEMO Scanned poster" (version `incomplete`, page 1 `unreadable`, message "Page 1 contains no extractable text (likely scanned). Upload a text-based PDF." → `EXTRACTION_INCOMPLETE`).

### 7.2 Runs
| Run | Compares | Status | Purpose |
|---|---|---|---|
| **R1** | v1 → v2 | `partial` (`errors`: `[{"stage":"ai","code":"AI_UNAVAILABLE"}]`) | main inbox demo with five changes |
| **R2** | v2 → v2b | `complete`, zero changes | "No substantive changes" state |
| **R3** | v1 → v2 | `running`, stage `diff`, 40% | progress UI |
| **R4** | v1 → v2 | `failed`, `errors: [{"stage":"diff","code":"STAGE_FAILED","message":"Demo failure"}]` | failed state |

**R1 changes** (token_ops offsets computed from the real span text):
| # | Type | Old → New | Flags | Categories (primary first) | Priority |
|---|---|---|---|---|---|
| C1 | replacement | "…until **31 December 2026**" → "**15 January 2027**" | `date_change` | `deadlines_timelines`, `cvr_transfer` | high |
| C2 | replacement | "within **30** days" → "**60** days" | `number_change` | `deadlines_timelines`, `required_documents` | high |
| C3 | replacement | accreditation sentence gains "and a valid form of identification" (insert op) | – | `required_documents`, `polling_unit_accreditation` | high |
| C4 | deletion | companion sentence removed | – | `uncategorized` | normal |
| C5 | insertion | new "Transfer of registration" paragraph | – | `cvr_transfer` | high (**zero alerts → "No matches found in this collection"**) |

**R1 alerts:**
| Alert | Change → passage | Band | `ai_status` | Review |
|---|---|---|---|---|
| A1 | C1 → M1 "Register to vote before 31 December 2026…" (reason `repeats_old_value`) | strong | `ok` (summary: "The registration deadline changed from 31 December 2026 to 15 January 2027."; rationale: "The flyer still states 31 December 2026, which matches the earlier official wording."; cited: C1 old, C1 new, passage) | unreviewed |
| A2 | C2 → M2 "…collect your PVC within 30 days…" (`repeats_old_value`) | strong | `unavailable` | `confirmed_impact`, revision 1, one decision row with a reason |
| A3 | C3 → M2 "At the polling unit, present your PVC…" (`old_wording_overlap`) | likely | `rejected_validation` | unreviewed |
| A4 | C4 → M3 "Voters may be accompanied by one companion…" (`old_wording_overlap`) | uncertain | `capped`, priority `normal` | unreviewed |

### 7.3 Implementation sketch (use this; extend to the full scenario)
```ts
import { createClient } from "@supabase/supabase-js";
import { createHash, randomUUID } from "node:crypto";

const sb = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } });
const ok = (r: { error: any }) => { if (r.error) throw r.error; return r; };

type Block = { text: string; heading?: boolean };
type Page = { blocks: Block[]; status?: "ok" | "blank" | "unreadable"; reason?: string };

// Builds full_text + spans so that full_text.slice(start,end) === raw_text for every span (INV2).
function build(pages: Page[]) {
  let full = "", seq = 0, section: string | null = null;
  const spans: any[] = [], pageRows: any[] = [];
  pages.forEach((p, i) => {
    if (i > 0) full += "\n\f\n";
    const pStart = full.length;
    p.blocks.forEach((b, j) => {
      if (j > 0) full += "\n\n";
      const start = full.length; full += b.text;
      if (b.heading) section = b.text;
      spans.push({ id: randomUUID(), seq: seq++, page: i + 1, section, section_path: section,
        start_offset: start, end_offset: full.length, raw_text: b.text, is_heading: !!b.heading, is_boilerplate: false });
    });
    pageRows.push({ page: i + 1, status: p.status ?? "ok", reason: p.reason ?? null,
      char_count: full.length - pStart, start_offset: pStart, end_offset: full.length });
  });
  if ([...full].length !== full.length) throw new Error("Seed text must be BMP-only (JS vs Postgres offsets)");
  return { full, spans, pageRows };
}

async function addVersion(o: { ws: string; kind: "source" | "material"; parent: string; label: string; pages: Page[];
  status: string; message?: string; userId: string; published?: string; filename: string }) {
  const b = build(o.pages);
  const bytes = Buffer.from(b.full || "[demo scanned page: no extractable text]", "utf8");
  const sha = createHash("sha256").update(bytes).digest("hex");
  ok(await sb.storage.from("documents").upload(`${o.ws}/${sha}`, bytes, { contentType: "text/plain", upsert: true }));
  ok(await sb.from("file_blobs").upsert({ workspace_id: o.ws, sha256: sha, storage_path: `${o.ws}/${sha}`,
    size_bytes: bytes.length, mime: "text/plain" }));
  const id = randomUUID();
  ok(await sb.from("document_versions").insert({ id, workspace_id: o.ws, kind: o.kind,
    source_id: o.kind === "source" ? o.parent : null, material_id: o.kind === "material" ? o.parent : null,
    declared_version: o.label, published_at: o.published ?? null, uploaded_by: o.userId, sha256: sha,
    original_filename: o.filename, size_bytes: bytes.length, rights_confirmed: true, page_count: o.pages.length,
    extraction_status: o.status, extraction_message: o.message ?? null, extractor_version: "seed",
    full_text: b.full, is_demo: true }));
  ok(await sb.from("pages").insert(b.pageRows.map((r) => ({ ...r, version_id: id }))));
  if (b.spans.length)
    ok(await sb.from("spans").insert(b.spans.map((s) => ({ ...s, workspace_id: o.ws, version_id: id }))));
  return { id, sha, ...b };
}

const rng = (t: string, sub: string) => {            // token_ops helper: offsets relative to span raw_text
  const s = t.indexOf(sub); if (s < 0) throw new Error(`"${sub}" not in "${t}"`);
  return { text: sub, start: s, end: s + sub.length };
};
const at = (p: number) => ({ text: "", start: p, end: p });   // empty range for the missing side
const spanStarting = (v: { spans: any[] }, prefix: string) => v.spans.find((s) => s.raw_text.startsWith(prefix))!;
// …then: insert source, collection, materials, versions; runs R1–R4; changes C1–C5; alerts A1–A4;
// decision row for A2 (reviewer = first workspace member); set alerts.review_state/review_revision for A2.
```
Test `seed-demo` itself: after seeding, a Vitest check calls `verify_spans` over **all** seeded span IDs and expects every `ok` to be true.

---

## 8. Phased implementation plan (frontend + Supabase)

Each phase is a vertical slice with an exit gate. Track tags: `[DB]` Supabase SQL, `[WEB]` Next.js, `[ALL]`.

| Phase | Name | PRD milestone | Covers |
|---:|---|---|---|
| F0 | Foundation and contract freeze | M1 | scaffolding, schema, RLS, contract |
| F1 | Auth, roles, sources & collections | M2 | FR01, NFR03 (part) |
| F2 | Demo seed and purge migration | M2 | decouples UI from the worker |
| F3 | Uploads and ingestion UI | M2 | FR02 (UI side), FR03 (display) |
| F4 | Preflight, run creation, run shell | M2→M3 | FR04, FR12 (display) |
| F5 | Comparison & Inbox | M3 | FR05/06/07 (display), FR09 |
| F6 | Evidence & Decision (read-only) + AI states | M3 | FR08 (display), FR09 |
| F7 | Review decisions and concurrency | M4 | FR10 |
| F8 | Export & Run Details, Evidence Pack | M4 | FR11 |
| F9 | Hardening, integration with the worker, release support | M4→M5 | NFR02–06, Section 9 of the PRD |

**Definition of done (every phase):** listed tasks complete; tests pass in CI (`vitest`, SQL tests, Playwright where listed); `tsc --noEmit` and lint clean; `database.types.ts` regenerated; `docs/PROGRESS.md` updated; deviations in `docs/DECISIONS.md`; `supabase db reset` still works.

### F0 — Foundation and contract freeze
| ID | Track | Task |
|---|---|---|
| F0-T1 | WEB | Create the Next.js app (`veritytrail-web`), Tailwind, shadcn/Radix, TanStack Query, lint/format, Vitest, Playwright, axe. |
| F0-T2 | DB | `supabase init`; write migrations 0001–0005 exactly per Section 4 (including generating one `r_<table>` select policy per table). |
| F0-T3 | WEB | `supabase gen types` script; typed browser/server clients; `middleware.ts` session refresh; `lib/errors.ts`; `lib/copy.ts`. |
| F0-T4 | WEB | App shell: header wordmark, nav, skip link, landmarks, `<title>` template; design tokens (AA contrast, focus ring, type scale); primitives `StatusChip`, `PriorityBadge`, `ChangeTypeLabel`, `FlagChips`, `CategoryLabel`, `DemoBadge`, `EmptyState`, `ErrorState`, `NotClaimedPanel`, `ScopeBanner`; a `/dev/components` page. |
| F0-T5 | ALL | Write `docs/CONTRACT.md` (Section 5). **Send it with the migrations to the AI teammate for review.** Record their sign-off in `docs/DECISIONS.md`. |
| F0-T6 | ALL | CI: lint, typecheck, unit tests, `supabase db reset` + SQL tests. |
**Tests:** `supabase db reset` applies cleanly; the append-only trigger blocks `UPDATE`/`DELETE` on `review_decisions`; an `anon` client can read nothing; a CI grep test fails if the code contains "latest official version" or "all materials are current".
**Exit gate:** shell runs; migrations applied; AI teammate has signed off the contract.

### F1 — Auth, roles, sources & collections
| ID | Track | Task |
|---|---|---|
| F1-T1 | WEB | `/login`, session, route guard, "no workspace" page, role-aware UI (`useSession`). |
| F1-T2 | WEB | Sources list/create/detail shell; provenance control; collections list/create/detail shell. zod validation with accessible errors. |
| F1-T3 | WEB | Overview v1: context, counts, retention note, **What this tool does not claim**, empty states. |
| F1-T4 | DB | SQL tests (`supabase/tests`): three users + two workspaces. |
**Tests:** reviewer cannot insert a source (policy denies); curator can; user in workspace B cannot see workspace A's sources (empty result, not an error that leaks existence); `anon` denied; Playwright: login → create source → create collection; axe clean on login/Overview/Sources/Collection.
**Exit gate:** role matrix enforced by RLS, not just hidden in the UI.

### F2 — Demo seed and purge migration
| ID | Track | Task |
|---|---|---|
| F2-T1 | DB | Migration 0006: `purge_workspace_data(p_workspace uuid)` (service role only) + redefine `forbid_mutation()` to allow changes only when `current_setting('veritytrail.purging', true) = 'on'`. |
| F2-T2 | WEB | `scripts/seed-demo.ts` per Section 7 (all of R1–R4, versions v1/v2/v2b, five materials incl. the two excluded). |
**Tests:** after seeding, `verify_spans` returns `ok=true` for every seeded span; after `purge_workspace_data` there are zero rows in all content tables; a normal session still cannot delete decisions.
**Exit gate:** `pnpm seed:demo` produces a workspace where every later screen has data to show.

### F3 — Uploads and ingestion UI
| ID | Track | Task |
|---|---|---|
| F3-T1 | DB | Migration RPCs `register_source_version`, `register_material_version` and the capacity/dedupe logic (Section 4.3 d, e). |
| F3-T2 | WEB | `FileDropzone`, client checks, SHA-256, direct Storage upload, RPC call, optimistic "Queued" row, polling (Section 6.4). |
| F3-T3 | WEB | Version tables with **Published / Uploaded** columns, status chips for all six `extraction_status` values, `PageCoverageGrid`, warnings, per-code error text, rights-confirmation checkbox. |
| F3-T4 | WEB | Material upload form and collection table (language tag, included/excluded with reasons). |
| F3-T5 | ALL | Test helper `fakeWorker.complete(versionId)` / `.reject(versionId, msg)` (service role) so Playwright can move versions through statuses without the real worker. |
**Tests:** 11 MB file blocked client-side; non-PDF/non-UTF-8 file blocked; identical bytes as two source versions → two rows, one blob, `IDENTICAL_CONTENT`; identical bytes as a material in the same collection → `deduplicated:true`, no new row; 31st material → `CAPACITY_EXCEEDED`; reviewer calling `register_*` → `FORBIDDEN`; stored object path has no filename; Playwright: upload → Queued → fake worker completes → Ready with grid; rejected/incomplete messages displayed verbatim.
**Exit gate:** uploads work end to end in the UI.

### F4 — Preflight, run creation, run shell
| ID | Track | Task |
|---|---|---|
| F4-T1 | DB | `build_snapshot`, `preflight_comparison`, `create_comparison`, `request_run_retry` (Section 4.3 a–c, l). |
| F4-T2 | WEB | `PairPicker` + `PreflightList` (debounced preflight, blockers with recovery text, warnings, confirm-order checkbox), Compare disabled until valid. |
| F4-T3 | WEB | `/runs/[runId]` shell: `ScopeBanner` (published/uploaded/compared as separate values), status banner for all five states, progress + stage with `aria-live`, polling. |
**Tests (SQL + Playwright):** each blocker (`SAME_VERSION`, `CONTEXT_MISMATCH`, `VERSION_INCOMPLETE` with unreadable page numbers, `EMPTY_COLLECTION`) has an RPC test and a UI test showing Compare disabled with the right text (**AC03**); `create_comparison` without confirmation → `ORDER_NOT_CONFIRMED`; same idempotency key twice → same run; **snapshot immutability** (add a material after the run exists → snapshot unchanged); reviewer cannot create a run; progress visible within 2 s.
**Exit gate:** AC03 passes end to end in the UI.

### F5 — Comparison & Inbox
| ID | Track | Task |
|---|---|---|
| F5-T1 | WEB | Queries for changes + alerts (Section 6.3), URL-synced filters, grouping by change, expandable alert rows. |
| F5-T2 | WEB | `DiffText` with highlight ranges, text legend, offset validation; `ChangeTypeLabel`, `FlagChips`, `CategoryLabel`, `PriorityBadge`. |
| F5-T3 | WEB | All distinct states: loading, running, `NO_CHANGES`, zero-alert change → `NO_MATCHES` with collection size and run time, partial, failed (R1–R4). |
| F5-T4 | WEB | Handle 500+ changes smoothly (memoized rows; virtualize only if measured to be slow). |
**Tests:** unit tests for `DiffText` (ranges inside/outside bounds, overlapping, empty, Unicode); filter combinations; Playwright on R1 (five changes; C5 shows "No matches found in this collection"), R2 ("No substantive changes…"), R3 (progress), R4 (failed); no screen ever says "all current"; axe clean.
**Exit gate:** a reviewer sees exact old/new wording with page references (AC01 UI side) and affected passages (AC02 UI side) from seeded data.

### F6 — Evidence & Decision (read-only) and AI states
| ID | Track | Task |
|---|---|---|
| F6-T1 | WEB | `/alerts/[id]` three panes (Radix Tabs on narrow screens), highlight rendering, page links. |
| F6-T2 | DB/WEB | `get_span_context` RPC, `EvidenceDrawer`, `/api/versions/[id]/original` signed-URL route. |
| F6-T3 | WEB | `AiDraftBlock` for all six `ai_status` values; cited-span buttons; match box with the ranking-aid sentence; the **"AI draft — review required"** and **"AI summary unavailable"** wording. |
**Tests:** every `ai_status` fixture renders the right text; an AI block never renders without its label; drawer opens at the right span and returns focus on close; signed URL route returns 404 for a version in another workspace; Playwright keyboard-only walkthrough of inbox → alert → drawer; axe clean.
**Exit gate:** a reviewer can reach full evidence without AI.

### F7 — Review decisions and concurrency
| ID | Track | Task |
|---|---|---|
| F7-T1 | DB | `submit_decision` and `override_priority` exactly per Section 4.3 f–g, plus grants. |
| F7-T2 | WEB | `DecisionForm`, `DecisionHistory`, priority override, `ConflictDialog`; reasons preserved on conflict; inbox rows and Overview counts update. |
| F7-T3 | DB | Verify that no client can write protected tables or fields directly. |
**Tests:** **AC04**: confirm and dismiss persist after refresh; two sessions with the same `expected_revision` → one succeeds and one gets `REVISION_CONFLICT` (`PT409`) with current revision/state in `details`; missing/short reason → `REASON_REQUIRED`; direct `update alerts set review_state…` from a reviewer session changes nothing or errors; direct insert/update/delete on `review_decisions` fails; `reviewer` of another workspace → `NOT_FOUND`; a new run for the same versions starts with all alerts `unreviewed` (INV8); Playwright two-browser-context conflict test.
**Exit gate:** decisions are durable, append-only, and conflict-safe.

### F8 — Export & Run Details
| ID | Track | Task |
|---|---|---|
| F8-T1 | DB | `verify_spans` RPC. |
| F8-T2 | WEB | `buildEvidencePack()` (server), JSON/CSV/HTML renderers, `/api/comparisons/[id]/export` (GET + POST), `export_events` write, headers (Section 6.8). |
| F8-T3 | WEB | `EvidenceBrief` print layout (A4, repeating pack-ID header, `<mark>` + `[[…]]`), print preview via `disposition=inline`. |
| F8-T4 | WEB | Export & Run Details screen with selectable alerts, snapshot (included and excluded), timings, errors, AI usage, warnings for unreviewed selection and partial runs. |
**Tests:** all four formats carry the same decision/reason/timestamp/coverage statement (field-by-field equality from the same `EvidencePack`); CSV injection payloads neutralised; `<script>` inside a material passage is escaped in HTML; a tampered span (test sets `raw_text` wrong via service role) makes export fail with `EVIDENCE_UNVERIFIABLE`; other-workspace run → 404; partial run shows the warning; JSON validates against the committed schema; Playwright print-preview snapshot; **AC04** export part.
**Exit gate:** full compare → inspect → decide → export flow works on seeded data with AI off.

### F9 — Hardening, integration with the worker, release support
| ID | Track | Task |
|---|---|---|
| F9-T1 | WEB | Accessibility pass on all six screens: keyboard-only walkthrough, focus management after dialogs/route changes, heading order, live regions, contrast, reduced motion; fix every serious/critical axe issue. |
| F9-T2 | WEB/DB | Security checklist (Section 9) implemented and tested; security headers (strict CSP with nonces, `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`); upload/export rate limiting. |
| F9-T3 | WEB | Purge route + admin UI ("Delete all workspace data" with typed confirmation); optional protected cron route. Verify zero rows and zero storage objects afterward. |
| F9-T4 | ALL | **Integration milestones with the AI teammate** (table below); fix contract drift through migrations, not by editing data by hand. |
| F9-T5 | WEB | Run-time UX checks: progress visible ≤ 2 s; NFR01 (≤ 120 s p95) is measured by the AI teammate's perf harness — the UI must display the run timings. |
| F9-T6 | WEB | Usability-test kit (`docs/USABILITY_PROTOCOL.md`): three tasks (compare, inspect, decide), script, success criteria (≥ 8/9 completed without coaching), time capture vs a manual baseline. Help run the sessions. |
| F9-T7 | ALL | Demo script and fallback: if the worker or AI fails live, demo from the seeded run with AI off. |
**Exit gate:** AC04, AC06 (UI/RLS parts) pass; the checklists in Sections 9 and 13 are complete or have recorded exceptions.

#### Integration milestones with the worker
| ID | What the AI teammate delivers | What you verify in the UI |
|---|---|---|
| I0 | Reviewed and agreed contract + migrations (F0) | sign-off recorded |
| I1 | `ingest_version` working on fixtures | a real upload reaches **Ready**; scanned fixture shows `incomplete` with page grid and message; over-limit file shows `rejected` message |
| I2 | `run_comparison` through `priority` | R-new shows real changes with correct offsets/highlights; categories and flags render |
| I3 | retrieval + alerts | real alerts open in the 3-pane view; a zero-match change shows **No matches found in this collection** |
| I4 | AI drafts with guardrails | `ok`/`unavailable`/`rejected_validation`/`capped` states render correctly; export labels AI text |
| I5 | benchmark report | release-gate numbers recorded; UI usability sessions scheduled |

---

## 9. Security and privacy checklist (verify in F9)
- [ ] RLS enabled on **every** table; every policy checks `is_member`/`has_role`; `anon` has no access; cross-workspace IDs read as not found (INV12, AC06).
- [ ] No client write path to `document_versions`, `spans`, `changes`, `alerts` review fields, `review_decisions`, `jobs`; all go through RPCs.
- [ ] RPCs are `security definer` with `set search_path = public`; `execute` revoked from `public`/`anon`; worker-only functions granted to `service_role` only.
- [ ] Service-role key never in a `NEXT_PUBLIC_*` variable and never imported by client code (add a lint rule / test that greps the client bundle).
- [ ] Storage bucket private; object paths contain no filenames; signed URLs expire in ≤ 60 s.
- [ ] `source_url` stored as text only; never fetched; links use `rel="noopener noreferrer nofollow"`.
- [ ] CSV formula escaping and HTML escaping tested; export CSP header set.
- [ ] Rights confirmation required for every upload; only public or authorized material admitted; no voter data fields anywhere.
- [ ] AI stays off (`workspaces.ai_enabled=false`) until data-retention terms of the chosen provider are documented (`docs/DATA_HANDLING.md`, shared with the AI teammate).
- [ ] Purge verified including Storage objects and caches; 30-day retention default shown in the UI.
- [ ] UI copy never implies institutional endorsement or legal authority.

## 10. Traceability (maintain `docs/TRACEABILITY.md`)
| Requirement | Where | Phase | Test |
|---|---|---|---|
| FR01 | sources/collections screens, RLS | F1 | RLS + Playwright |
| FR02 (UI/DB side) | `FileDropzone`, `register_*`, Storage policies | F3 | upload/dedupe tests |
| FR03 (display) | coverage grid, status chips | F3 | Playwright with fake worker |
| FR04 | preflight, snapshot, order confirmation | F4 | AC03 tests |
| FR05–FR07 (display) | Inbox, evidence panes | F5–F6 | AC01/AC02 UI tests |
| FR08 (display) | `AiDraftBlock`, citation links | F6 | status-state tests |
| FR09 | all six screens | F1–F8 | Playwright + axe |
| FR10 | `submit_decision`, UI | F7 | AC04 |
| FR11 | export route + renderers | F8 | AC04 export tests |
| FR12 (display/retry) | run banners, `request_run_retry`, `request_ai_retry` | F4, F6 | state tests |
| NFR03, NFR04, NFR05 | RLS, a11y, purge | F1, F9 | AC06, axe, purge test |
Name tests with the AC ID, e.g. `test_AC04_stale_decision_returns_409`.

## 11. Open decisions (defaults assumed until you confirm)
| ID | Question | Default |
|---|---|---|
| D1 | Election context/issuer/notice family for the MVP | Demo family (Section 7); swap in permission-cleared real documents later |
| D2 | Admission, team size, submission and demo rules | unknown; not assumed |
| D4 | Hosting and model provider/spend cap | Vercel + Supabase for the app; worker hosting and provider chosen by the AI teammate; AI off by default |
| D5 | Roles | curator / reviewer / admin as in Section 4 |
| D6 | Retention | 30 days (proposed) |
| D7 | Three reviewers for the usability gate | recruit three; record any shortfall |
| D9 | Who triggers retries when a run fails | `request_run_retry` RPC (curator/admin) re-queues the job; the worker's stages are idempotent |
| D10 | Worker hosting and uptime during judging | AI teammate decides; run the worker locally with a stable connection if no host is available, and demo with seeded data as fallback |
Also assumed here (not in the PRD): `extraction_status='rejected'`; `ai_retry` and `run_comparison` retries via RPCs; unified `document_versions` table; blank pages are warnings; `date_change` auto-categorizes as Deadlines & Timelines (worker side); reason required for all three decision states; `preflight_comparison` and `override_priority` added to support disabling Compare and the PRD's priority override.

## 12. Final acceptance checklist
- [ ] AC01–AC06: each has a passing named test (UI/DB parts here; pipeline parts in the worker repo).
- [ ] INV3–INV6 and INV8–INV12 each have a passing test.
- [ ] All six screens pass axe and the keyboard-only walkthrough.
- [ ] Required copy appears exactly as in Section 2.3; no forbidden phrases.
- [ ] Demo data is badged everywhere it appears, including exports.
- [ ] The demo runs entirely from seeded data with AI off if needed.
- [ ] README states the supported scope and known limits with measured numbers from the benchmark.

## Appendix — Glossary
**Change:** a difference between two source versions. **Alert:** a link between one change and one potentially affected material passage. **Span:** an offset-addressed slice of a version's extracted text. **Snapshot:** the frozen list of material versions used by a run. **Evidence Pack:** the exported hand-off for a material owner. **Confirmed impact:** a reviewer judgment that a material needs attention, not an official ruling or a published correction.
