# VerityTrail — End-to-End Requirement & Invariant Traceability Matrix

| ID | Requirement / Invariant | Frontend / DB Phase (`Taiwo / AY`) | AI Worker Milestone (`Prestige`) | Automated Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **FR01** | Source & collection provenance records | `F1` (`0001_schema.sql`, `0002_rls.sql`) | `I0` (`docs/CONTRACT.md`) | `supabase/tests` RLS + Playwright |
| **FR02** | Immutable version upload, SHA-256, dedupe, 10 MB / 20-page limits | `F3` (`register_source_version`, `register_material_version`) | `I1` (`worker/extractor.py`) | `test_INV2_and_I1_ingest_pdf_and_utf8_validation` |
| **FR03** | Page-aware text extraction, stable spans & unreadable page blocking | `F3` (`PageCoverageGrid`, status chips) | `I1` (`worker/extractor.py`) | `test_INV2_and_I1_ingest_pdf_and_utf8_validation` |
| **FR04** | Explicit version ordering & frozen collection snapshot | `F4` (`preflight_comparison`, `create_comparison`) | `I2`, `I3` (`worker/runner.py`) | `test_AC03_incomplete_source_blocks_comparison` |
| **FR05** | Deterministic section alignment, exact diff & token flags | `F5` (`DiffText`, `ChangeTypeLabel`, `FlagChips`) | `I2` (`worker/diff_engine.py`) | `test_AC01_deadline_change_and_identical_pair` |
| **FR06** | Nigerian electoral priority categories & transparent rules | `F5` (`CategoryLabel`, `PriorityBadge`) | `I2` (`worker/priority_rules.py`) | `test_AC02_demo_scenario_R1_exact_contract_match` |
| **FR07** | Snapshot passage retrieval, match reasons & confidence bands | `F5`, `F6` (Inbox & Evidence panes) | `I3` (`worker/retriever.py`) | `test_AC02_demo_scenario_R1_exact_contract_match` |
| **FR08** | Citation-verified alerts & grounded AI draft summaries | `F6` (`AiDraftBlock`, `EvidenceDrawer`) | `I4` (`worker/ai_explainer.py`) | `test_AC05_and_INV3_INV5_ai_outage_hallucination_and_injection` |
| **FR09** | Review inbox filters, 3-pane evidence view & coverage disclosure | `F5`, `F6` (`ScopeBanner`, `NotClaimedPanel`) | — | Playwright + `@axe-core/playwright` |
| **FR10** | Concurrency-safe human review decisions (`409` conflict) | `F7` (`submit_decision`, `ConflictDialog`) | `I4` (`INV4` preservation) | `test_AC06_and_INV4_INV7_idempotent_retry_preserves_human_decisions` |
| **FR11** | Material Owner Evidence Pack export (HTML/PDF Brief + CSV/JSON) | `F8` (`/api/comparisons/[id]/export`, `csvSafe`) | `I1` (`INV2` offset integrity) | `F8` export & CSV formula-injection tests |
| **FR12** | Job lifecycle (`queued` → `running` → `partial`/`complete`/`failed`) & safe retry | `F4`, `F6` (`request_run_retry`, `request_ai_retry`) | `I4` (`worker/runner.py`, `worker/supabase_worker.py`) | `test_AC06_and_INV4_INV7_idempotent_retry_preserves_human_decisions` |
| **NFR01** | Warm-index run completes $\le 120\text{s}$ at p95 over 20 runs | `F9` (displays run timings) | `I5` (`worker/evaluate.py`: measured `0.0332s`) | `test_I5_nigerian_benchmark_release_gates` |
| **NFR02–06** | Reliability, RLS security, WCAG 2.2 AA accessibility, purge, cost caps | `F1–F9` | `I4`, `I5` | `test_AC05_*`, `test_AC06_*`, `supabase/tests` |
