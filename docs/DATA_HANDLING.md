# VerityTrail — Data Handling, Privacy & Responsible AI Policy

**Applies to:** Both Frontend/Supabase (`veritytrail-web`) and Python AI Worker (`worker/`).
**PRD References:** `NFR03` (Security), `NFR05` (Privacy & Retention), `NFR06` (Observability & Cost), Section 2 (Program Constraints).

---

## 1. Admissible Data Policy
1. **Public or Expressly Authorized Materials Only:** Every file upload requires explicit curator confirmation (`rights_confirmed = true`: *"These files are public or I am authorized to use them"*).
2. **Strict Exclusion of Personal Voter Records:** VerityTrail never ingests, stores, or processes voter registration records, BVAS biometric logs, National Identification Numbers (NINs) of individuals, phone numbers, or private institutional data.
3. **Synthetic Demo Labelling (`INV11`):** All synthetic or benchmark documents carry `is_demo = true` and render a visible **Demo data** badge across the UI and all exported Evidence Packs.

---

## 2. AI Provider & External Model Call Rules
1. **Off by Default (`workspaces.ai_enabled = false`):** External LLM calls are disabled by default at workspace creation and only enabled when an administrator explicitly toggles `ai_enabled = true` after confirming provider retention terms.
2. **Minimal Context Window:** Only the specific changed source span(s) (`old_excerpt`, `new_excerpt`) and the candidate material passage span (`passage_span.raw_text`) are sent to the model—never full documents or workspace metadata.
3. **Zero Tool Access & Prompt-Injection Isolation (`AC05`):** Uploaded text is encapsulated strictly as untrusted data. The model has no web-browsing, database-writing, or publishing tools and cannot alter `review_state`.
4. **Spend and Token Caps (`NFR06`):** Each comparison run enforces `MAX_AI_CALLS_PER_RUN` (default `50`) and `MAX_USD_PER_RUN` (default `$1.00`). Exceeding either cap immediately switches remaining alerts to `ai_status = 'capped'` while preserving all deterministic diffs and passage matches (`INV5`).

---

## 3. Retention and Workspace Purge (`NFR05`)
1. **30-Day Default Demo Retention:** `workspaces.purge_after` defaults to `created_at + interval '30 days'`.
2. **Complete Cascade Purge (`/api/workspace/purge` & `purge_workspace_data`):** Purging a workspace deletes all objects under `documents/{workspace_id}/` in Supabase Storage and removes all database records (`export_events`, `ai_cache`, `review_decisions`, `alerts`, `changes`, `comparison_runs`, `jobs`, `spans`, `pages`, `document_versions`, `file_blobs`, `materials`, `collections`, `source_documents`), leaving zero dangling evidence links or cached extracts.
