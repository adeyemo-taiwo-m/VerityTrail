# VerityTrail — AI & Intelligence Pipeline Implementation Guide (Prestige's Track)

**For:** Prestige and Prestige's AI coding agent.
**Scope:** Everything the Python AI & intelligence worker (`worker/`) needs: file validation, page-aware text extraction, immutable span indexing, deterministic section alignment and diffing, Nigerian electoral priority rules, snapshot passage retrieval, grounded AI draft generation, server-side citation and faithfulness validation, Supabase job queue consumption, and the 10-pair / 30-material Nigerian electoral benchmark evaluation harness.
**Companion to:** `VerityTrail_Frontend_Implementation_Guide.md` (Taiwo's track) and `VerityTrail_Design_System.md`.
**Source of truth:** `Election_Change_Radar_PRD.docx` / `PRD.md` (v2.0). The product is named **VerityTrail**. If this guide and the PRD disagree, the PRD wins; record any conflict in `docs/DECISIONS.md`.

---

## 0. How to use this document (read first, agent)

1. Execute milestones **I0 → I5** in order (Section 7). Each milestone ends with an automated test and exit gate. Do not advance until the current gate is green.
2. **Deterministic evidence comes first; AI is strictly an optional, validated layer.** Every comparison run must produce 100% complete diffs, Nigerian priority tags, and passage matches even when `ai_enabled = false` or when the LLM provider is unreachable (`INV5`).
3. **The worker is the sole writer of pipeline outputs, and must never touch human review state (`INV4`).** Never write to `alerts.review_state`, `alerts.review_revision`, `alerts.priority_overridden`, or `review_decisions`.
4. **Zero-tolerance citation and faithfulness validation (`INV3`).** Every `span_id` cited by an AI draft must exist in `{old_span_id, new_span_id, passage_span_id}`, resolve to stored text, and every number or date in the AI summary/rationale must appear in the cited evidence text. On any violation, set `ai_status = 'rejected_validation'` and clear all AI text fields.
5. **0-based BMP-safe character offsets everywhere (`INV2`).** Every span must satisfy `full_text[start_offset:end_offset] == raw_text`, every `token_op` must index into its span's `raw_text`, and every `match_reason` must index into the passage span's `raw_text`.
6. Keep `docs/PROGRESS.md`, `docs/DECISIONS.md`, and `docs/BENCHMARK_REPORT.md` updated as milestones pass.

---

## 1. Ownership & Architecture Boundary

| Area | Owner | Notes |
| :--- | :--- | :--- |
| Next.js 15 app, 6 accessible screens, Evidence Pack UI & export renderers | **Taiwo** | Specified in `VerityTrail_Frontend_Implementation_Guide.md` |
| Supabase schema, RLS policies, Storage policies, RPC functions (`0001–0006`) | **Taiwo / AY** | Reviewed and signed off by Prestige in Milestone `I0` (`docs/CONTRACT.md`) |
| Python AI Worker (`worker/`): extraction → spans, deterministic diff, Nigerian priority rules, retrieval, grounded AI drafts, citation validator, job daemon, benchmark | **Prestige (this guide)** | Connects to Supabase via `SUPABASE_SERVICE_ROLE_KEY` or runs in-memory for tests and offline benchmarks |

```
Browser (Next.js) ──supabase-js (user session, RLS)──▶ Supabase Postgres + Storage ◀──service role / RPCs── Python AI Worker (worker/)
```

The frontend creates jobs exclusively through Postgres RPCs (`register_source_version`, `register_material_version`, `create_comparison`, `request_run_retry`, `request_ai_retry`). The Python worker claims jobs via `claim_job(p_worker, p_lease_seconds)`, executes the pipeline, writes `pages`, `spans`, `changes`, `alerts`, and `ai_cache`, and updates `document_versions`, `comparison_runs`, and `jobs`.

---

## 2. System Invariants (`INV1 → INV12`)

| # | Invariant | Enforced By |
| :--- | :--- | :--- |
| **INV1** | Original uploaded bytes and raw extracted text are immutable. Whitespace normalization and header suppression happen only in a comparison representation mapped back to raw spans. | Worker (`extractor.py`, `diff_engine.py`) |
| **INV2** | For every `spans` row, `full_text[start_offset:end_offset] == raw_text` (0-based code-point offsets, BMP-sanitized so Python, Postgres `substr()`, and JS `.slice()` agree). | Worker (`extractor.py`) + DB (`verify_spans`) |
| **INV3** | Every displayed citation/span ID resolves to a stored span of the correct version, and AI summaries introduce zero unsupported dates or numbers. Unverifiable AI outputs are withheld (`rejected_validation`). | Worker (`ai_explainer.py`) + Export route |
| **INV4** | AI output and worker upserts can never set or overwrite `review_state`, `review_revision`, `priority_overridden`, or `review_decisions`. | Worker (`models.py`, `runner.py`) + DB RLS/RPC |
| **INV5** | If AI is disabled, unavailable, capped, or rejected, deterministic diffs, Nigerian priority categories, and passage matches remain 100% usable with `"AI summary unavailable"` (or status-specific label). | Worker (`ai_explainer.py`) + UI |
| **INV6** | Never present a `partial` run as `complete`. Any `AI_UNAVAILABLE`, `AI_CAPPED`, or per-change error sets `comparison_runs.status = 'partial'`. | Worker (`runner.py`) |
| **INV7** | Alert IDs (`uuid5(NAMESPACE, f"{run_id}:{change_key}:{passage_span_id}")`) and change keys (`chg-0001`…) are deterministic so worker retries never duplicate alerts or changes. | Worker (`models.py`, `diff_engine.py`, `retriever.py`) |
| **INV8** | Review decisions are append-only; stale concurrent edits return `409` (`REVISION_CONFLICT`); decisions never silently carry over to a new comparison run. | DB RPC (`submit_decision`) |
| **INV9** | Document version ordering (`old_version_id` vs. `new_version_id`) is explicitly confirmed by a human curator, never inferred from upload timestamp. | DB RPC (`create_comparison`) |
| **INV10** | Zero candidate matches on a change is rendered as `"No matches found in this collection"`, never `"All materials are current"`. | UI + Worker metrics |
| **INV11** | Synthetic/demo fixtures carry `is_demo = true` (`"Demo data"`) and never masquerade as official notices. | Seed + UI + Benchmark |
| **INV12** | Every table has Row-Level Security (RLS) checking workspace membership; cross-workspace queries return not found. | DB RLS (`0002_rls.sql`) |

---

## 3. Worker Stack, Layout & Environment

| Component | Choice | Rationale |
| :--- | :--- | :--- |
| Language | Python 3.11+ (tested on Python 3.14) | Fast text processing, native `difflib`, `hashlib`, `uuid`, `unittest` |
| PDF Extraction | PyMuPDF (`pymupdf` / `fitz`) | Accurate page-by-page text, image/drawing detection for scanned pages, encryption & metadata checks |
| Diff & Alignment | Deterministic 2-pass section/paragraph aligner + `difflib.SequenceMatcher` | 100% reproducible token-level character offsets (`token_ops`) |
| Retrieval | Hybrid topic-anchored lexical + old-value repetition + phrase overlap | High precision ($\ge 80\%$) and high recall ($\ge 85\%$) without opaque vector false positives |
| Database / Queue | Supabase PostgREST + Storage REST client (`urllib.request`, zero external HTTP bloat) | Claims jobs via `claim_job` RPC using `SUPABASE_SERVICE_ROLE_KEY` |

### Repository Layout (`worker/`)
```
VerityTrail/
├─ docs/
│  ├─ VerityTrail_Frontend_Implementation_Guide.md
│  ├─ VerityTrail_Design_System.md
│  ├─ VerityTrail_AI_Pipeline_Handoff.md     # This specification
│  ├─ CONTRACT.md                            # Frozen Supabase ↔ Worker interface
│  ├─ DATA_HANDLING.md                       # Privacy, retention & AI provider guardrails
│  ├─ TRACEABILITY.md                        # End-to-end FR / NFR / AC / INV matrix
│  ├─ DECISIONS.md                           # Architecture decision log
│  ├─ PROGRESS.md                            # Milestone status tracker
│  └─ BENCHMARK_REPORT.md                    # Measured release-gate scorecard
└─ worker/
   ├─ __init__.py                            # PIPELINE_VERSION, EXTRACTOR_VERSION, PROMPT_VERSION
   ├─ models.py                              # Dataclasses & deterministic UUIDv5 helpers
   ├─ extractor.py                           # Milestone I1: PDF/UTF-8 validation, page status & span indexing
   ├─ diff_engine.py                         # Milestone I2: Section alignment, token_ops & mutation flags
   ├─ priority_rules.py                      # Milestone I2: Nigerian electoral taxonomy & matched_rules
   ├─ retriever.py                           # Milestone I3: Snapshot passage matcher & match_reasons
   ├─ ai_explainer.py                        # Milestone I4: Grounded AI drafts, prompt shield & citation validator
   ├─ runner.py                              # Milestone I4: 7-stage run orchestrator & InMemoryWorkspaceStore
   ├─ supabase_worker.py                     # Milestone I4: Live Supabase job polling daemon
   ├─ evaluate.py                            # Milestone I5: Automated 10-pair / 30-material benchmark harness
   ├─ fixtures/
   │  ├─ __init__.py
   │  └─ nigerian_benchmark.py               # Milestone I5: Nigerian electoral benchmark dataset (dev + held-out)
   └─ tests/
      ├─ __init__.py
      └─ test_pipeline.py                    # End-to-end tests for I1–I5, AC01–AC06, INV2–INV7
```

### Environment Variables
```bash
SUPABASE_URL=                     # Or NEXT_PUBLIC_SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY=        # Server-only key used by the worker daemon
MAX_FILE_BYTES=10485760           # 10 MB limit (FR02)
MAX_PAGES=20                      # 20-page limit (FR02)
MAX_AI_CALLS_PER_RUN=50           # Spend/usage cap per comparison run (NFR06)
MAX_USD_PER_RUN=1.00              # Spend cap in USD per comparison run (NFR06)
```

---

## 4. Stage-by-Stage Technical Specification

### 4.1 Milestone I1 — `ingest_version` (`worker/extractor.py`)

When the worker claims an `ingest_version` job (`payload = {"version_id": "<uuid>"}`):

1. **Set `extraction_status = 'extracting'`** on `document_versions`.
2. **Download bytes** from Supabase Storage bucket `documents` at `{workspace_id}/{sha256}`.
3. **Verify SHA-256 Integrity:** Compute `hashlib.sha256(file_bytes).hexdigest()`. If it does not match `document_versions.sha256`, abort with:
   * `extraction_status = 'rejected'`
   * `extraction_message = 'HASH_MISMATCH'`
4. **Enforce Size & Format Guards (`FR02`, `NFR03`):**
   * If `len(file_bytes) > 10,485,760` (10 MB) $\rightarrow$ `rejected`, `"This file is larger than 10 MB. Compress it or split it."`
   * **If PDF (`%PDF-` magic header):**
     * Reject if raw bytes contain active PDF action tokens (`/JS`, `/JavaScript`, `/Launch`, `/RichMedia`, `/AA`).
     * Open with PyMuPDF (`pymupdf.open(stream=file_bytes, filetype="pdf")`).
     * Reject if `doc.is_encrypted` or `doc.needs_pass` $\rightarrow$ `"Encrypted or password-protected PDFs are not supported. Upload an unencrypted text-based PDF."`
     * Reject if `len(doc) > 20` $\rightarrow$ `"Document has N pages, exceeding the 20-page limit."`
   * **If UTF-8 Text:**
     * Reject if binary NUL byte (`\x00`) is present or `file_bytes.decode("utf-8", errors="strict")` fails $\rightarrow$ `"Only text-based PDF and UTF-8 text files are supported."`
     * Split pages on form-feed `\f`; reject if page count $> 20$.
5. **Classify Each Page (`ok`, `blank`, `unreadable`) & Index Spans (`INV2`):**
   * Sanitize non-BMP code points (`ord(ch) > 0xFFFF`) so Python code-point indices, Postgres `substr()`, and JavaScript UTF-16 `.slice()` offsets never drift.
   * For each PDF page: if extracted text is empty but the page contains raster images (`page.get_images()`) or vector drawings (`page.get_drawings()`), mark `status = 'unreadable'` with `reason = "Page contains no extractable text (likely scanned)."`. If a page has neither text nor drawings/images, mark `status = 'blank'`.
   * Split readable pages into paragraph and heading blocks. Join pages with `"\n\f\n"` and blocks with `"\n\n"`, recording `start_offset` and `end_offset` for each `SpanRecord`.
   * Detect headings (`is_heading = True`) and update the running `section` and `section_path`. Flag page-number footers (`Page 1 of 2`) with `is_boilerplate = True`.
   * **Verify `INV2` before writing:** Assert `full_text[s.start_offset:s.end_offset] == s.raw_text` for every span.
6. **Set Final Extraction Status:**
   * If any page is `unreadable`: set `extraction_status = 'incomplete'` and `extraction_message = "Page X contains no extractable text (likely scanned). Upload a text-based PDF."` (or `"Pages X, Y contain no extractable text..."`).
   * Else if zero spans were extracted: set `extraction_status = 'incomplete'`.
   * Else: set `extraction_status = 'complete'`, `extraction_message = None`.
7. **Idempotent Write:** Delete any existing `spans` and `pages` for `version_id` and insert the new rows.

---

### 4.2 Milestone I2 — Deterministic Diff & Nigerian Electoral Priority Rules (`worker/diff_engine.py`, `worker/priority_rules.py`)

#### Stage `diff` (`progress_pct = 40`)
1. **Boilerplate & Whitespace Filtering (`FR05`):** Exclude `is_boilerplate = True` spans. Compare paragraphs using `normalize_whitespace(raw_text)` so whitespace-only changes produce zero diff while preserving untouched `raw_text` in `old_excerpt` and `new_excerpt` (`INV1`).
2. **Two-Pass Alignment:**
   * *Pass 1 (Exact Normalized Match):* Pair unchanged spans across `old_spans` and `new_spans`.
   * *Pass 2 (Best-First Similarity Pairing):* Pair modified body paragraphs with combined token-Jaccard + `SequenceMatcher` similarity $\ge 0.38$ as `replacement`. Flag `moved = True` when a modified paragraph moved to a different section header and shifted sequence position by $\ge 2$.
   * *Unpaired Spans:* Unmatched non-heading spans in `old_spans` become `deletion`; unmatched non-heading spans in `new_spans` become `insertion`.
3. **Token-Level Character Diffs (`token_ops`):**
   * For every `replacement`, tokenize `old_excerpt` and `new_excerpt` with exact character offsets and compute `difflib.SequenceMatcher` opcodes (`replace`, `insert`, `delete`).
   * Trim shared leading/trailing punctuation so highlight ranges tightly wrap changed values (e.g., `"31 December 2026"` $\rightarrow$ `"15 January 2027"`, `"30"` $\rightarrow$ `"60"`).
4. **High-Stakes Token Flags (`flags`):**
   * `date_change`: Changed calendar dates (`31 December 2026`, `2026-11-10`) or clock times (`2:00 PM` $\rightarrow$ `2:30 PM`, `8:30 AM`).
   * `number_change`: Changed non-date numeric quantities (`30 days` $\rightarrow$ `60 days`, `1,000 voters` $\rightarrow$ `750 voters`, `20` $\rightarrow$ `1`).
   * `modal_flip`: Shift between permissive modals (`may`, `can`, `optional`, `permitted`) and obligatory modals (`must`, `shall`, `required`, `mandatory`, `compulsory`).
   * `negation_flip`: Addition or removal of negation/prohibition markers (`not`, `no`, `never`, `without`, `prohibited`, `banned`, `disallowed`, `ineligible`).

#### Stage `priority` (`progress_pct = 50`) — Nigerian Electoral Domain Taxonomy (`FR06`)
Grounded in INEC's *Regulations and Guidelines for the Conduct of Elections*, the *Electoral Act 2022*, the *CVR Operational Framework*, and the *IDP Voting Framework*, changes are classified using transparent, auditable rules:

| Category ID | UI Label | Rule IDs & Nigerian Electoral Triggers |
| :--- | :--- | :--- |
| `deadlines_timelines` | **Deadlines & Timelines** | **Auto-triggered by `date_change` flag**, plus:`DL-01` (`deadline`, `timeline`, `closing date`, `commencement`, `expiration`, `extended`, `postponed`, `rescheduled`), `DL-02` (`until <date>`, `before <date>`, `not later than <date>`), `DL-03` (`within N days/hours/weeks`, `N days before/after/of notification`, `between <time> and <time>`). |
| `eligibility` | **Eligibility Criteria** | `EL-01` (`at least 18 years old`, `citizen of Nigeria`, `eligible to vote`, `qualified to vote/register`, `disqualified`, `ineligible`, `ordinarily resident`, `internally displaced person / IDP voter`, `first-time voter`). |
| `required_documents` | **Required Documents (PVC, forms, etc.)** | `RD-01` (`Permanent Voter's Card`, `PVC`, `valid form of identification`, `National Identification Number / NIN`, `voter's slip`, `registration slip`, `affidavit`, `Form EC8A / EC60E / EC40H / EC-9B`, `Incident Form`). |
| `polling_unit_accreditation` | **Polling Unit & Accreditation Procedures** | `PU-01` (`accreditation`, `accredited`, `BVAS`, `Bimodal Voter Accreditation`, `polling unit`, `Presiding Officer`, `fingerprint`, `biometric`, `facial authentication`, `ballot paper/box`, `voting cubicle`, `collation`, `IReV`, `Braille ballot guide`). |
| `cvr_transfer` | **CVR / Transfer Rules** | `CV-01` (`Continuous Voter Registration`, `CVR`, `transfer of registration`, `voter transfer`, `registration centre`, `register to vote`, `claims and objections`, `preliminary register`, `replacement of lost PVC`). |
| `uncategorized` | **Uncategorized** | Any change matching none of the 5 pillars above (`categories = []`, `primary_category = 'uncategorized'`). |

* **Priority Rule:** Any change matching at least one of the 5 Nigerian electoral categories (or carrying a high-stakes flag `date_change`, `number_change`, `modal_flip`, `negation_flip`) starts with `base_priority = 'high'`; other changes start with `base_priority = 'normal'`.
* **Auditability:** Every matched rule is recorded in `changes.matched_rules` with `{rule_id, category, matched_text, side, start, end}` so reviewers can see *why* a change was prioritized.

---

### 4.3 Milestone I3 — Snapshot Passage Retrieval (`worker/retriever.py`)

#### Stage `retrieve` (`progress_pct = 75`)
1. **Snapshot Isolation (`FR04`, `FR07`):** Only inspect material versions where `included == True` in `comparison_runs.collection_snapshot`.
2. **Topic-Anchored Hybrid Matching:**
   For each `(change, passage_span)` pair (excluding headings and boilerplate):
   * Extract normalized content stems and specific topic stems (filtering out broad electoral nouns like `polling`, `unit`, `presiding`, `officer`, `voter`, `pvc` when checking clause specificity).
   * Require that the passage aligns with the specific topic of the modified clause and touches the modified concept (`diff_old_stems`) or overlaps $\ge 60\%$ of the old clause's content stems.
   * **Match Reason 1 — `repeats_old_value` (`"Repeats the earlier value"`):** The passage contains an exact case-insensitive match of the replaced old value from `token_ops` (e.g., `"31 December 2026"`, `"30 days"`, `"2:00 PM"`, `"10 October 2026"`) and shares topical context with the clause.
   * **Match Reason 2 — `old_wording_overlap` (`"Overlaps the earlier wording"`):** The passage shares a contiguous multi-word content phrase with `change.old_excerpt` (e.g., `"present your PVC"`, `"accompanied by one companion"`, `"issue an Incident Form"`).
   * **Match Reason 3 — `topic_related` (`"Related topic (new requirement in the newer version)"`):** For pure insertions where a newly added provision shares $\ge 3$ specific topic stems and a phrase with an existing material passage.
3. **Offset Validation & Confidence Bands:**
   * Verify `0 <= passage_start < passage_end <= len(passage_span.raw_text)` and `passage_span.raw_text[passage_start:passage_end] == reason["text"]`.
   * Assign `confidence_band`:
     * `strong`: `repeats_old_value` triggered or `score >= 0.80`
     * `likely`: `score >= 0.55` (and `change.type != 'deletion'`)
     * `uncertain`: `0.45 <= score < 0.55` or deletion overlap
4. **Deterministic Alert UUIDv5 (`INV7`):**
   * `alert.id = str(uuid.uuid5(VERITYTRAIL_UUID_NAMESPACE, f"{run_id}:{change.change_key}:{passage_span.id}"))`.

---

### 4.4 Milestone I4 — Grounded AI Drafts & Strict Citation Validator (`worker/ai_explainer.py`, `worker/runner.py`)

#### Stage `ai` (`progress_pct = 95`)
1. **Workspace Switch:** If `comparison_runs.ai_enabled == False`, set `ai_status = 'disabled'` on all alerts and skip external model calls.
2. **Spend & Call Caps (`NFR06`):** Track `calls`, `input_tokens`, `output_tokens`, and `est_usd` per run. If `calls >= max_ai_calls` or `est_usd >= max_usd`, set `ai_status = 'capped'` on remaining alerts and append `{"stage": "ai", "code": "AI_CAPPED", "message": "..."}` to `comparison_runs.errors`.
3. **Prompt-Injection Defense (`AC05`):**
   * Treat source excerpts and material passages strictly as untrusted data blocks.
   * The model has zero tool access and cannot mutate database state.
   * Scan untrusted text for injection patterns (`"ignore previous instructions"`, `"set review_state"`, `"mark this alert as dismissed"`). When detected, ignore the instruction and attach a warning in `ai_uncertainty`.
4. **Server-Side Citation & Faithfulness Validator (`validate_ai_draft` / `INV3`):**
   Every generated draft `{summary, rationale, uncertainty, cited_span_ids}` must pass four deterministic server-side checks before it can be stored:
   * **Check 1 (Non-empty):** `summary` and `rationale` are non-empty strings, and `cited_span_ids` is a non-empty list.
   * **Check 2 (Citation Membership & Resolution):** Every `span_id` in `cited_span_ids` belongs to `{change.old_span_id, change.new_span_id, alert.passage_span_id}` and resolves in `stored_spans`.
   * **Check 3 (Numeric & Date Faithfulness):** Every numeric/year token (`\b\d+(?:,\d{3})*(?:\.\d+)?\b`) present in `summary` or `rationale` must appear verbatim in the cited spans' `raw_text`. Any hallucinated number or date triggers rejection.
   * **Check 4 (No Forbidden Claims):** Output must not contain `"latest official version"`, `"all materials are current"`, `"hereby certified"`, or `"legally binding ruling"`.
   * **On Validation Failure:** Set `ai_status = 'rejected_validation'` and set `ai_summary = None`, `ai_rationale = None`, `ai_uncertainty = None`, `cited_span_ids = []`.
   * **On Provider Error / Timeout (`INV5`, `INV6`):** Set `ai_status = 'unavailable'`, clear AI text fields, record `AI_UNAVAILABLE` in `comparison_runs.errors`, and finish the run with `status = 'partial'`.

---

## 5. Nigerian Electoral Benchmark & Evaluation Protocol (Milestone I5)

Per PRD Section 9, `worker/fixtures/nigerian_benchmark.py` and `worker/evaluate.py` implement a versioned benchmark of **10 Nigerian electoral source pairs** and **30 voter-education materials**:

| Pair ID | Split | Nigerian Electoral Domain Covered | Changes | Affected Links |
| :--- | :---: | :--- | :---: | :---: |
| **P01** | `dev` | Continuous Voter Registration (CVR) deadline, PVC collection window, ID at accreditation, companion rule & voter transfer (Demo Scenario `R1`) | 5 | 6 |
| **P02** | `dev` | Polling unit closing hours (`2:00 PM` → `2:30 PM`), BVAS facial fallback replacing Incident Forms, and ward residency eligibility | 4 | 6 |
| **P03** | `dev` | Voter transfer deadline (`30 days` → `90 days`), preliminary register display (`7 days` → `14 days`), and Form EC-9B lost PVC replacement | 4 | 6 |
| **P04** | `dev` | IDP camp voter revalidation deadline, prohibition of camp slips for accreditation, and out-of-state IDP Presidential-only ballot scope | 4 | 6 |
| **P05** | `dev` | PWD Braille ballot guide deployment threshold (`20` → `1` voter), `8:30 AM` priority queue access, and exclusion of party agents as companions | 4 | 3 |
| **P06** | `dev` | Polling unit splitting threshold (`1,000` → `750` voters), `30-day` relocation notice, and emergency flood relocation within registration area | 4 | 3 |
| **P07** | `dev` | Online CVR biometric capture window (`14` → `21 days`), 774 LGA capture centres, and duplicate registration retention rule | 4 | 3 |
| **P08** | `held_out` | Mandatory polling-unit posting of Form EC8A/EC60E, direct polling-unit IReV upload, and BVAS accredited-voter over-voting definition | 4 | 3 |
| **P09** | `held_out` | Strict prohibition of PVC collection by proxy/power of attorney, ward PVC collection deadline shift, and weekend collection hours | 4 | 3 |
| **P10** | `held_out` | Domestic observer portal deadline, QR-coded INEC observer badge requirement, and voting cubicle photography prohibition | 6 | 3 |
| **Total** | **70% / 30%** | **10 Source Pairs · 30 Civic Materials · 30 Unaffected Distractor Passages** | **43** | **42** |

### Release Gates & Measured Results (`python3 -m worker.evaluate`)

| Metric | PRD Release Gate | Measured Overall | Measured Held-Out (30%) | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Meaningful Change Recall** | $\ge 95.0\%$ (`100%` critical held-out) | **100.0%** (`43/43`) | **100.0%** (`14/14`, critical `8/8`) | ✅ **PASS** |
| **Affected Passage Precision** | $\ge 80.0\%$ | **87.5%** (`42/48`) | **81.82%** (`9/11`) | ✅ **PASS** |
| **Affected Passage Recall** | $\ge 85.0\%$ | **100.0%** (`42/42`) | **100.0%** (`9/9`) | ✅ **PASS** |
| **Evidence Citation Validity** | $100.0\%$ (`0` fabricated) | **100.0%** (`143/143`) | **100.0%** | ✅ **PASS** |
| **Summary Faithfulness** | $100.0\%$ (`0` unsupported claims) | **100.0%** (`48/48`) | **100.0%** | ✅ **PASS** |
| **Warm-Index p95 Latency (`NFR01`)** | $\le 120.0\text{s}$ | **0.0332s** (`20` runs) | — | ✅ **PASS** |

---

## 6. Phased Implementation & Verification Commands

| Milestone | Scope | Verification Command |
| :--- | :--- | :--- |
| **I0** | Contract freeze (`docs/CONTRACT.md`, `docs/DECISIONS.md`) | Diff against `VerityTrail_Frontend_Implementation_Guide.md` Section 4–5 |
| **I1** | `worker/extractor.py` (`FR02`, `FR03`, `INV2`) | `PYTHONPATH=. python3 -m unittest worker.tests.test_pipeline.VerityTrailWorkerTestSuite.test_INV2_and_I1_ingest_pdf_and_utf8_validation` |
| **I2** | `worker/diff_engine.py` & `worker/priority_rules.py` (`FR05`, `FR06`, `AC01`) | `PYTHONPATH=. python3 -m unittest worker.tests.test_pipeline.VerityTrailWorkerTestSuite.test_AC01_deadline_change_and_identical_pair` |
| **I3** | `worker/retriever.py` (`FR07`, `INV7`, `AC02`) | `PYTHONPATH=. python3 -m unittest worker.tests.test_pipeline.VerityTrailWorkerTestSuite.test_AC02_demo_scenario_R1_exact_contract_match` |
| **I4** | `worker/ai_explainer.py`, `worker/runner.py`, `worker/supabase_worker.py` (`FR08`, `AC05`, `AC06`) | `PYTHONPATH=. python3 -m unittest discover -s worker/tests -v` |
| **I5** | `worker/evaluate.py` & `worker/fixtures/nigerian_benchmark.py` (`Section 9`) | `PYTHONPATH=. python3 -m worker.evaluate` |
