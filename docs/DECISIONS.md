# VerityTrail — Architecture & Implementation Decisions Log

## Decision Record

| ID | Date | Owner | Decision | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-01** | 2026-11-22 | Prestige / Taiwo | **Contract Freeze (Phase F0 / Milestone I0)** | Signed off on Section 5 of `VerityTrail_Frontend_Implementation_Guide.md` as `docs/CONTRACT.md`. Offsets are 0-based code-point indices into `full_text` and span `raw_text`. |
| **DEC-02** | 2026-11-22 | Prestige | **Deterministic UUIDv5 for Alerts (`INV7`)** | Using `uuid.uuid5(VERITYTRAIL_NAMESPACE, f"{run_id}:{change_key}:{passage_span_id}")` guarantees idempotent retries across `run_comparison` and `request_run_retry`. |
| **DEC-03** | 2026-11-22 | Prestige | **Strict Server-Side Span & Fact Grounding (`INV3`, `INV5`)** | Every AI draft must cite valid span IDs from `{old_span_id, new_span_id, passage_span_id}` and may not introduce numbers or dates absent from those spans. Invalid outputs set `ai_status = 'rejected_validation'` and clear text fields automatically. |
| **DEC-04** | 2026-11-22 | Prestige | **Auto-Categorize `date_change` as `deadlines_timelines`** | Per Section 11 of the implementation guide, any change carrying the `date_change` flag automatically includes `deadlines_timelines` in `categories` and receives `base_priority = 'high'`. |
