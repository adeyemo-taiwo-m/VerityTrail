"""Job queue consumer and 7-stage comparison run orchestrator (Section 5.1 & 5.3)."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from worker import EXTRACTOR_VERSION, PIPELINE_VERSION, PROMPT_VERSION
from worker.ai_explainer import (
    compute_ai_cache_key,
    default_grounded_draft_generator,
    populate_ai_drafts_for_alerts,
    validate_ai_draft,
)
from worker.diff_engine import diff_version_spans
from worker.extractor import ingest_document_bytes
from worker.models import AlertRecord, ChangeRecord, ExtractionResult, PageRecord, SpanRecord
from worker.priority_rules import classify_change_priority
from worker.retriever import retrieve_affected_passages


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ComparisonRunResult:
    run_id: str
    workspace_id: str
    status: str  # 'complete' | 'partial' | 'failed'
    stage: str
    progress_pct: int
    pipeline_version: str
    model_version: Optional[str]
    prompt_version: Optional[str]
    changes: List[ChangeRecord] = field(default_factory=list)
    alerts: List[AlertRecord] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    stage_history: List[Tuple[str, int]] = field(default_factory=list)


def execute_comparison_pipeline(
    *,
    run_id: str,
    workspace_id: str,
    old_version: Dict[str, Any],
    new_version: Dict[str, Any],
    old_spans: List[SpanRecord],
    new_spans: List[SpanRecord],
    collection_snapshot: Dict[str, Any],
    material_spans_by_version: Dict[str, List[SpanRecord]],
    ai_enabled: bool = False,
    model_version: str = "veritytrail-grounded-v1",
    max_ai_calls: int = 50,
    max_usd: float = 1.00,
    ai_cache: Optional[Dict[str, Dict[str, Any]]] = None,
    ai_generator_fn: Optional[Callable[[ChangeRecord, SpanRecord], Dict[str, Any]]] = None,
    on_stage_progress: Optional[Callable[[str, int], None]] = None,
) -> ComparisonRunResult:
    """
    Execute the 7-stage comparison pipeline per Section 5.3:
    validate (5%) -> prepare (15%) -> diff (40%) -> priority (50%) -> retrieve (75%) -> ai (95%) -> finalize (100%)
    """
    stage_durations_ms: Dict[str, int] = {}
    stage_history: List[Tuple[str, int]] = []
    errors: List[Dict[str, Any]] = []

    def report_stage(stage_name: str, pct: int) -> None:
        stage_history.append((stage_name, pct))
        if on_stage_progress:
            on_stage_progress(stage_name, pct)

    # Stage 1: validate (5%)
    t0 = time.perf_counter()
    if old_version.get("id") == new_version.get("id"):
        return ComparisonRunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            status="failed",
            stage="validate",
            progress_pct=5,
            pipeline_version=PIPELINE_VERSION,
            model_version=model_version if ai_enabled else None,
            prompt_version=PROMPT_VERSION if ai_enabled else None,
            errors=[{"stage": "validate", "code": "SAME_VERSION", "message": "Earlier and later versions cannot be identical IDs."}],
            stage_history=[("validate", 5)],
        )

    if old_version.get("extraction_status") != "complete" or new_version.get("extraction_status") != "complete":
        return ComparisonRunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            status="failed",
            stage="validate",
            progress_pct=5,
            pipeline_version=PIPELINE_VERSION,
            model_version=model_version if ai_enabled else None,
            prompt_version=PROMPT_VERSION if ai_enabled else None,
            errors=[{"stage": "validate", "code": "VERSION_INCOMPLETE", "message": "Both source versions must have extraction_status='complete'."}],
            stage_history=[("validate", 5)],
        )

    snapshot_materials = collection_snapshot.get("materials") or []
    included_mat_version_ids = [
        m["material_version_id"]
        for m in snapshot_materials
        if m.get("included") is True and m.get("material_version_id")
    ]
    if not included_mat_version_ids:
        return ComparisonRunResult(
            run_id=run_id,
            workspace_id=workspace_id,
            status="failed",
            stage="validate",
            progress_pct=5,
            pipeline_version=PIPELINE_VERSION,
            model_version=model_version if ai_enabled else None,
            prompt_version=PROMPT_VERSION if ai_enabled else None,
            errors=[{"stage": "validate", "code": "EMPTY_COLLECTION", "message": "Collection snapshot has no included materials."}],
            stage_history=[("validate", 5)],
        )

    stage_durations_ms["validate"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("validate", 5)

    # Stage 2: prepare (15%)
    t0 = time.perf_counter()
    stored_spans: Dict[str, SpanRecord] = {}
    for s in old_spans:
        stored_spans[s.id] = s
    for s in new_spans:
        stored_spans[s.id] = s

    included_material_spans: Dict[str, List[SpanRecord]] = {}
    for mv_id in included_mat_version_ids:
        m_spans = material_spans_by_version.get(mv_id, [])
        included_material_spans[mv_id] = m_spans
        for s in m_spans:
            stored_spans[s.id] = s

    stage_durations_ms["prepare"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("prepare", 15)

    # Stage 3: diff (40%)
    t0 = time.perf_counter()
    changes = diff_version_spans(
        workspace_id=workspace_id,
        run_id=run_id,
        old_spans=old_spans,
        new_spans=new_spans,
    )
    stage_durations_ms["diff"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("diff", 40)

    # Stage 4: priority (50%)
    t0 = time.perf_counter()
    for chg in changes:
        classify_change_priority(chg)
    stage_durations_ms["priority"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("priority", 50)

    # Stage 5: retrieve (75%)
    t0 = time.perf_counter()
    alerts, candidates_per_change = retrieve_affected_passages(
        workspace_id=workspace_id,
        run_id=run_id,
        changes=changes,
        included_material_spans=included_material_spans,
    )
    stage_durations_ms["retrieve"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("retrieve", 75)

    # Stage 6: ai (95%)
    t0 = time.perf_counter()
    changes_by_id = {c.id: c for c in changes}
    alerts, ai_metrics, ai_errors = populate_ai_drafts_for_alerts(
        alerts=alerts,
        changes_by_id=changes_by_id,
        stored_spans=stored_spans,
        ai_enabled=ai_enabled,
        model_version=model_version,
        max_ai_calls=max_ai_calls,
        max_usd=max_usd,
        cache=ai_cache,
        generator_fn=ai_generator_fn,
    )
    errors.extend(ai_errors)
    stage_durations_ms["ai"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("ai", 95)

    # Stage 7: finalize (100%)
    t0 = time.perf_counter()
    by_type: Dict[str, int] = {"replacement": 0, "deletion": 0, "insertion": 0}
    by_category: Dict[str, int] = {}
    moved_count = 0
    for c in changes:
        by_type[c.type] = by_type.get(c.type, 0) + 1
        by_category[c.primary_category] = by_category.get(c.primary_category, 0) + 1
        if c.moved:
            moved_count += 1

    stage_durations_ms["finalize"] = max(1, int((time.perf_counter() - t0) * 1000))
    report_stage("finalize", 100)

    metrics = {
        "counts": {
            "changes": len(changes),
            "by_type": by_type,
            "alerts": len(alerts),
            "moved": moved_count,
            "by_category": by_category,
        },
        "stage_durations_ms": stage_durations_ms,
        "candidates_per_change": candidates_per_change,
        "ai": ai_metrics,
    }

    # INV6: Never present a partial run as complete
    final_status = "partial" if len(errors) > 0 else "complete"

    return ComparisonRunResult(
        run_id=run_id,
        workspace_id=workspace_id,
        status=final_status,
        stage="finalize",
        progress_pct=100,
        pipeline_version=PIPELINE_VERSION,
        model_version=model_version if ai_enabled else None,
        prompt_version=PROMPT_VERSION if ai_enabled else None,
        changes=changes,
        alerts=alerts,
        errors=errors,
        metrics=metrics,
        stage_history=stage_history,
    )


class InMemoryWorkspaceStore:
    """
    In-memory simulation of the Supabase tables + RPCs so the worker pipeline,
    idempotency, retry invariants (INV2-INV8), and single-alert ai_retry can be
    tested end-to-end without requiring a running Postgres instance.
    """

    def __init__(self) -> None:
        self.storage_blobs: Dict[str, bytes] = {}
        self.document_versions: Dict[str, Dict[str, Any]] = {}
        self.pages: Dict[str, List[PageRecord]] = {}
        self.spans: Dict[str, List[SpanRecord]] = {}
        self.comparison_runs: Dict[str, Dict[str, Any]] = {}
        self.changes: Dict[str, List[ChangeRecord]] = {}
        self.alerts: Dict[str, Dict[str, Any]] = {}  # alert_id -> full row dict (including review_state)
        self.review_decisions: List[Dict[str, Any]] = []
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.ai_cache: Dict[str, Dict[str, Any]] = {}

    def run_ingest_job(self, version_id: str) -> ExtractionResult:
        v = self.document_versions[version_id]
        ws_id = v["workspace_id"]
        sha = v["sha256"]
        storage_key = f"{ws_id}/{sha}"
        file_bytes = self.storage_blobs.get(storage_key, b"")

        v["extraction_status"] = "extracting"
        res = ingest_document_bytes(
            version_id=version_id,
            workspace_id=ws_id,
            file_bytes=file_bytes,
            expected_sha256=sha,
        )

        # Idempotent delete-and-rewrite of pages & spans for this version
        self.pages[version_id] = list(res.pages)
        self.spans[version_id] = list(res.spans)

        v["extraction_status"] = res.extraction_status
        v["extraction_message"] = res.extraction_message
        v["extractor_version"] = res.extractor_version
        v["page_count"] = res.page_count
        v["full_text"] = res.full_text
        if res.warnings:
            existing_warnings = list(v.get("warnings") or [])
            v["warnings"] = existing_warnings + res.warnings

        return res

    def run_comparison_job(
        self,
        run_id: str,
        ai_generator_fn: Optional[Callable[[ChangeRecord, SpanRecord], Dict[str, Any]]] = None,
        max_ai_calls: int = 50,
    ) -> ComparisonRunResult:
        run_row = self.comparison_runs[run_id]
        ws_id = run_row["workspace_id"]
        old_v = self.document_versions[run_row["old_version_id"]]
        new_v = self.document_versions[run_row["new_version_id"]]
        old_spans = self.spans.get(old_v["id"], [])
        new_spans = self.spans.get(new_v["id"], [])
        snapshot = run_row["collection_snapshot"]

        run_row["status"] = "running"
        run_row["started_at"] = utc_now_iso()
        run_row["pipeline_version"] = PIPELINE_VERSION

        def update_progress(stage_name: str, pct: int) -> None:
            run_row["stage"] = stage_name
            run_row["progress_pct"] = pct

        res = execute_comparison_pipeline(
            run_id=run_id,
            workspace_id=ws_id,
            old_version=old_v,
            new_version=new_v,
            old_spans=old_spans,
            new_spans=new_spans,
            collection_snapshot=snapshot,
            material_spans_by_version=self.spans,
            ai_enabled=bool(run_row.get("ai_enabled", False)),
            ai_cache=self.ai_cache,
            ai_generator_fn=ai_generator_fn,
            max_ai_calls=max_ai_calls,
            on_stage_progress=update_progress,
        )

        # Idempotent write of changes
        self.changes[run_id] = list(res.changes)

        # Idempotent upsert of alerts preserving any existing human review fields (INV4, INV7)
        for alert in res.alerts:
            insert_dict = alert.to_insert_dict()
            if alert.id in self.alerts:
                existing = self.alerts[alert.id]
                # Preserve human review fields untouched
                insert_dict["review_state"] = existing.get("review_state", "unreviewed")
                insert_dict["review_revision"] = existing.get("review_revision", 0)
                insert_dict["priority_overridden"] = existing.get("priority_overridden", False)
                if insert_dict["priority_overridden"]:
                    insert_dict["priority"] = existing["priority"]
            else:
                insert_dict["review_state"] = "unreviewed"
                insert_dict["review_revision"] = 0
                insert_dict["priority_overridden"] = False
            self.alerts[alert.id] = insert_dict

        run_row["status"] = res.status
        run_row["stage"] = res.stage
        run_row["progress_pct"] = res.progress_pct
        run_row["model_version"] = res.model_version
        run_row["prompt_version"] = res.prompt_version
        run_row["errors"] = res.errors
        run_row["metrics"] = res.metrics
        run_row["finished_at"] = utc_now_iso()

        return res

    def run_ai_retry_job(
        self,
        alert_id: str,
        ai_generator_fn: Optional[Callable[[ChangeRecord, SpanRecord], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Re-run only the AI explanation step for a single alert (Section 5.1 ai_retry)."""
        alert_row = self.alerts[alert_id]
        run_id = alert_row["run_id"]
        run_row = self.comparison_runs[run_id]

        change_obj = next(c for c in self.changes[run_id] if c.id == alert_row["change_id"])
        all_spans: Dict[str, SpanRecord] = {}
        for s_list in self.spans.values():
            for s in s_list:
                all_spans[s.id] = s

        passage_span = all_spans[alert_row["passage_span_id"]]
        gen = ai_generator_fn or default_grounded_draft_generator

        try:
            draft = gen(change_obj, passage_span)
            ok, _ = validate_ai_draft(
                draft=draft,
                change=change_obj,
                passage_span=passage_span,
                stored_spans=all_spans,
            )
            if ok:
                alert_row["ai_status"] = "ok"
                alert_row["ai_summary"] = draft["summary"].strip()
                alert_row["ai_rationale"] = draft["rationale"].strip()
                alert_row["ai_uncertainty"] = (draft.get("uncertainty") or "").strip() or None
                alert_row["cited_span_ids"] = list(draft["cited_span_ids"])
            else:
                alert_row["ai_status"] = "rejected_validation"
                alert_row["ai_summary"] = None
                alert_row["ai_rationale"] = None
                alert_row["ai_uncertainty"] = None
                alert_row["cited_span_ids"] = []
        except Exception:
            alert_row["ai_status"] = "unavailable"

        # Update run status if all alerts for this run are no longer unavailable/capped
        run_alerts = [a for a in self.alerts.values() if a["run_id"] == run_id]
        if all(a["ai_status"] in ("ok", "disabled", "rejected_validation") for a in run_alerts):
            run_row["errors"] = [
                e for e in run_row.get("errors", []) if e.get("code") not in ("AI_UNAVAILABLE", "AI_CAPPED")
            ]
            if not run_row["errors"]:
                run_row["status"] = "complete"

        return alert_row
