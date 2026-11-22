# VerityTrail — Frontend / Supabase ↔ AI Worker Contract (v1.0)

**Status:** Frozen (Phase F0 / Milestone I0)
**Agreed by:** Taiwo (Frontend & Supabase) · Prestige (AI & Pipeline Worker) · AY (Backend)

This document defines the exact database, storage, and job-queue contract between the Next.js/Supabase layer and the Python AI pipeline worker. Any change requires agreement across tracks and a database migration.

---

## 1. Interface Architecture

```
Browser (Next.js) ──supabase-js (user session, RLS)──▶ Supabase Postgres + Storage ◀──service role── Python AI Worker (Prestige)
```

* **The frontend creates jobs only through RPCs** (`register_source_version`, `register_material_version`, `create_comparison`, `request_run_retry`, `request_ai_retry`).
* **The Python worker is the sole writer of pipeline data** (`pages`, `spans`, `changes`, `alerts`, `ai_cache`, extraction status fields on `document_versions`, and stage/progress fields on `comparison_runs`).
* **Strict Human Control Invariant (`INV4`):** The worker must **never** write `alerts.review_state`, `alerts.review_revision`, `alerts.priority_overridden`, or `review_decisions`.

---

## 2. Jobs Queue (`jobs` table)

The worker claims jobs using the `claim_job(p_worker text, p_lease_seconds int default 60)` RPC and periodically runs `sweep_dead_jobs()`.

| Job `type` | Created by RPC | `payload` | Worker Responsibilities |
| :--- | :--- | :--- | :--- |
| `ingest_version` | `register_source_version`, `register_material_version` | `{"version_id": "<uuid>"}` | 1. Download `documents/{workspace_id}/{sha256}`.<br>2. Recompute SHA-256 and compare with `document_versions.sha256` (mismatch → `extraction_status='rejected'`, `extraction_message='HASH_MISMATCH'`).<br>3. Validate: $\le 20$ pages, not encrypted, no active PDF content (`/JS`, `/JavaScript`, `/Launch`), valid PDF or strict UTF-8 text (no NUL bytes).<br>4. Extract page-aware text; write `pages`, `spans`, `full_text`, `page_count`, `extractor_version`; update `extraction_status` and `extraction_message`.<br>5. Idempotent: delete and rewrite that version's `pages` and `spans` in one transaction. |
| `run_comparison` | `create_comparison`, `request_run_retry` | `{"run_id": "<uuid>"}` | Execute stages `validate` (5%) → `prepare` (15%) → `diff` (40%) → `priority` (50%) → `retrieve` (75%) → `ai` (95%) → `finalize` (100%); write `changes` and `alerts`; update `comparison_runs` and `jobs`. |
| `ai_retry` | `request_ai_retry` | `{"alert_id": "<uuid>"}` | Re-run only the AI explanation step for that single alert; validate citations; update `ai_*` fields on `alerts`; update run status if all alerts now have valid AI summaries. |

---

## 3. Extraction Statuses & Offset Invariant (`INV2`)

* **0-Based Code-Point Offsets (`INV2`):** Every `spans` row must satisfy:
  `full_text[start_offset : end_offset] == raw_text` (in Python) and `substr(full_text, start_offset + 1, end_offset - start_offset) = raw_text` (in Postgres).
* **`document_versions.extraction_status` values:**
  * `pending` — waiting for worker
  * `extracting` — worker currently extracting
  * `complete` — all pages readable (`ok` or `blank`)
  * `incomplete` — one or more pages have `pages.status = 'unreadable'` (blocks source comparison; excludes material from snapshot)
  * `failed` — unexpected parser failure
  * `rejected` — failed validation (`> 20` pages, `> 10 MB`, encrypted PDF, active content, `HASH_MISMATCH`, invalid UTF-8)

---

## 4. Comparison Stages & Data Shapes

### 4.1 Run Stages (`comparison_runs`)
| Stage | `progress_pct` | Description |
| :--- | :---: | :--- |
| `validate` | `5` | Verify source versions (`complete`), distinct versions, and frozen `collection_snapshot`. |
| `prepare` | `15` | Load spans and build normalized comparison representations. |
| `diff` | `40` | Align sections, detect `insertion`, `deletion`, `replacement`, `moved`, `token_ops`, and `flags`. |
| `priority` | `50` | Apply Nigerian electoral rules (`categories`, `primary_category`, `matched_rules`, `base_priority`). |
| `retrieve` | `75` | Match changes against included snapshot material spans; compute `match_reasons`, `score`, `confidence_band`. |
| `ai` | `95` | If `ai_enabled=true`, generate grounded draft summary/rationale and validate `cited_span_ids`. |
| `finalize` | `100` | Record `metrics`, `finished_at`, and final `status` (`complete` or `partial`). |

### 4.2 Nigerian Electoral Categories (`changes.categories` & `primary_category`)
* `deadlines_timelines` — "Deadlines & Timelines"
* `eligibility` — "Eligibility Criteria"
* `required_documents` — "Required Documents (PVC, forms, etc.)"
* `polling_unit_accreditation` — "Polling Unit & Accreditation Procedures"
* `cvr_transfer` — "CVR / Transfer Rules"
* `uncategorized` — "Uncategorized"

### 4.3 Change Flags (`changes.flags`)
* `date_change` — "Date changed"
* `number_change` — "Number changed"
* `modal_flip` — "Obligation wording changed"
* `negation_flip` — "Negation changed"

### 4.4 Token Operations (`changes.token_ops`)
Character offsets are 0-based relative to `old_span.raw_text` and `new_span.raw_text`:
```json
[
  {
    "op": "replace",
    "old": { "text": "31 December 2026", "start": 58, "end": 74 },
    "new": { "text": "15 January 2027", "start": 58, "end": 73 }
  }
]
```

### 4.5 Alert Match Reasons (`alerts.match_reasons`)
Character offsets are 0-based relative to `passage_span.raw_text`:
```json
[
  {
    "type": "repeats_old_value",
    "text": "31 December 2026",
    "passage_start": 29,
    "passage_end": 45
  }
]
```
Allowed `type` values: `repeats_old_value`, `old_wording_overlap`, `shared_category_terms`, `topic_related`, `semantic`.

### 4.6 Deterministic Alert IDs (`INV7`)
Every `alert.id` is a deterministic **UUIDv5** derived from `f"{run_id}:{change_key}:{passage_span_id}"` so worker retries never create duplicate alerts.
