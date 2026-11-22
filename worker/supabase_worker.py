"""Live Supabase background job consumer for VerityTrail (Section 5.1 & 4.3k, with INV4 protection, persistent ai_cache, and lease heartbeats)."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from worker import PIPELINE_VERSION, PROMPT_VERSION
from worker.ai_explainer import resolve_configured_ai_generator, validate_ai_draft
from worker.extractor import ingest_document_bytes
from worker.models import ChangeRecord, SpanRecord
from worker.runner import execute_comparison_pipeline, utc_now_iso


def future_lease_iso(seconds: int = 120) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


class SupabaseServiceClient:
    """Zero-dependency PostgREST + Storage client using the service-role key."""

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self.base_url = supabase_url.rstrip("/")
        self.service_key = service_role_key

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def rpc(self, fn_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/rest/v1/rpc/{fn_name}"
        data = json.dumps(params or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None

    def select(self, table: str, query_params: str = "") -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        if query_params:
            url = f"{url}?{query_params}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def insert(self, table: str, rows: Any, upsert: bool = False) -> Any:
        url = f"{self.base_url}/rest/v1/{table}"
        prefer = "return=representation"
        if upsert:
            prefer = "resolution=merge-duplicates,return=representation"
        req = urllib.request.Request(
            url,
            data=json.dumps(rows).encode("utf-8"),
            headers=self._headers({"Prefer": prefer}),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None

    def update(self, table: str, filter_query: str, values: Dict[str, Any]) -> Any:
        url = f"{self.base_url}/rest/v1/{table}?{filter_query}"
        req = urllib.request.Request(
            url,
            data=json.dumps(values).encode("utf-8"),
            headers=self._headers({"Prefer": "return=representation"}),
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None

    def delete(self, table: str, filter_query: str) -> None:
        url = f"{self.base_url}/rest/v1/{table}?{filter_query}"
        req = urllib.request.Request(url, headers=self._headers(), method="DELETE")
        with urllib.request.urlopen(req, timeout=30):
            return

    def download_storage_blob(self, bucket: str, path: str) -> bytes:
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        req = urllib.request.Request(
            url,
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()


class VerityTrailWorkerDaemon:
    """Claims jobs from Supabase (`claim_job`) and processes `ingest_version`, `run_comparison`, and `ai_retry`."""

    def __init__(self, client: SupabaseServiceClient, worker_id: Optional[str] = None) -> None:
        self.client = client
        self.worker_id = worker_id or f"worker-{socket.gethostname()}-{os.getpid()}"

    def _heartbeat_job(self, job_id: str, stage: str, progress_pct: int) -> None:
        """Extend lease_expires_at and update stage/progress on the active job row."""
        self.client.update(
            "jobs",
            f"id=eq.{job_id}",
            {
                "stage": stage,
                "progress_pct": progress_pct,
                "lease_expires_at": future_lease_iso(120),
            },
        )

    def process_next_job(self) -> bool:
        jobs = self.client.rpc("claim_job", {"p_worker": self.worker_id, "p_lease_seconds": 120})
        if not jobs:
            return False

        job = jobs[0] if isinstance(jobs, list) else jobs
        job_id = job["id"]
        job_type = job["type"]
        payload = job.get("payload") or {}

        try:
            if job_type == "ingest_version":
                self._handle_ingest_version(job_id, payload["version_id"])
            elif job_type == "run_comparison":
                self._handle_run_comparison(job_id, payload["run_id"])
            elif job_type == "ai_retry":
                self._handle_ai_retry(job_id, payload["alert_id"])
            else:
                raise ValueError(f"Unknown job type: {job_type}")
        except Exception as exc:
            self.client.update(
                "jobs",
                f"id=eq.{job_id}",
                {
                    "status": "failed",
                    "finished_at": utc_now_iso(),
                    "last_error": {"code": "WORKER_EXCEPTION", "message": str(exc)},
                },
            )
        return True

    def _handle_ingest_version(self, job_id: str, version_id: str) -> None:
        rows = self.client.select("document_versions", f"id=eq.{version_id}")
        if not rows:
            raise ValueError(f"document_versions row not found: {version_id}")
        v = rows[0]
        ws_id = v["workspace_id"]
        sha = v["sha256"]

        self.client.update("document_versions", f"id=eq.{version_id}", {"extraction_status": "extracting"})
        self._heartbeat_job(job_id, "extracting", 25)
        file_bytes = self.client.download_storage_blob("documents", f"{ws_id}/{sha}")

        res = ingest_document_bytes(
            version_id=version_id,
            workspace_id=ws_id,
            file_bytes=file_bytes,
            expected_sha256=sha,
        )

        self._heartbeat_job(job_id, "indexing_spans", 75)
        # Idempotent delete and rewrite of pages and spans
        self.client.delete("spans", f"version_id=eq.{version_id}")
        self.client.delete("pages", f"version_id=eq.{version_id}")

        if res.pages:
            self.client.insert("pages", [p.to_dict() for p in res.pages])
        if res.spans:
            self.client.insert("spans", [s.to_dict() for s in res.spans])

        # Preserve existing warnings while deduplicating warning codes
        existing_warnings = list(v.get("warnings") or [])
        existing_codes = {w.get("code") for w in existing_warnings if isinstance(w, dict)}
        merged_warnings = existing_warnings + [w for w in res.warnings if w.get("code") not in existing_codes]

        self.client.update(
            "document_versions",
            f"id=eq.{version_id}",
            {
                "extraction_status": res.extraction_status,
                "extraction_message": res.extraction_message,
                "extractor_version": res.extractor_version,
                "page_count": res.page_count,
                "full_text": res.full_text,
                "warnings": merged_warnings,
            },
        )
        self.client.update(
            "jobs",
            f"id=eq.{job_id}",
            {"status": "complete", "progress_pct": 100, "stage": "complete", "finished_at": utc_now_iso()},
        )

    def _load_spans_for_version(self, version_id: str) -> List[SpanRecord]:
        rows = self.client.select("spans", f"version_id=eq.{version_id}&order=seq.asc")
        return [
            SpanRecord(
                id=r["id"],
                workspace_id=r["workspace_id"],
                version_id=r["version_id"],
                seq=r["seq"],
                page=r["page"],
                section=r.get("section"),
                section_path=r.get("section_path"),
                start_offset=r["start_offset"],
                end_offset=r["end_offset"],
                raw_text=r["raw_text"],
                is_heading=bool(r.get("is_heading", False)),
                is_boilerplate=bool(r.get("is_boilerplate", False)),
            )
            for r in rows
        ]

    def _handle_run_comparison(self, job_id: str, run_id: str) -> None:
        runs = self.client.select("comparison_runs", f"id=eq.{run_id}")
        if not runs:
            raise ValueError(f"comparison_runs row not found: {run_id}")
        run_row = runs[0]
        ws_id = run_row["workspace_id"]
        ai_enabled = bool(run_row.get("ai_enabled", False))

        ai_gen_fn, configured_model = resolve_configured_ai_generator()

        old_v = self.client.select("document_versions", f"id=eq.{run_row['old_version_id']}")[0]
        new_v = self.client.select("document_versions", f"id=eq.{run_row['new_version_id']}")[0]

        old_spans = self._load_spans_for_version(old_v["id"])
        new_spans = self._load_spans_for_version(new_v["id"])

        snapshot = run_row["collection_snapshot"]
        material_spans_by_version: Dict[str, List[SpanRecord]] = {}
        for m in snapshot.get("materials") or []:
            if m.get("included") and m.get("material_version_id"):
                mv_id = m["material_version_id"]
                material_spans_by_version[mv_id] = self._load_spans_for_version(mv_id)

        # Load persistent ai_cache for this workspace
        workspace_cache: Dict[str, Dict[str, Any]] = {}
        initial_cache_keys = set()
        if ai_enabled:
            try:
                cache_rows = self.client.select("ai_cache", f"workspace_id=eq.{ws_id}")
                for cr in cache_rows:
                    ck = cr["cache_key"]
                    workspace_cache[ck] = cr["response"]
                    initial_cache_keys.add(ck)
            except Exception:
                pass

        self.client.update(
            "comparison_runs",
            f"id=eq.{run_id}",
            {
                "status": "running",
                "started_at": utc_now_iso(),
                "pipeline_version": PIPELINE_VERSION,
                "model_version": configured_model if ai_enabled else None,
                "prompt_version": PROMPT_VERSION if ai_enabled else None,
            },
        )

        def on_stage(stage_name: str, pct: int) -> None:
            self.client.update("comparison_runs", f"id=eq.{run_id}", {"stage": stage_name, "progress_pct": pct})
            self._heartbeat_job(job_id, stage_name, pct)

        max_calls = int(os.environ.get("MAX_AI_CALLS_PER_RUN", "50"))
        max_usd = float(os.environ.get("MAX_USD_PER_RUN", "1.00"))

        res = execute_comparison_pipeline(
            run_id=run_id,
            workspace_id=ws_id,
            old_version=old_v,
            new_version=new_v,
            old_spans=old_spans,
            new_spans=new_spans,
            collection_snapshot=snapshot,
            material_spans_by_version=material_spans_by_version,
            ai_enabled=ai_enabled,
            model_version=configured_model,
            max_ai_calls=max_calls,
            max_usd=max_usd,
            ai_cache=workspace_cache,
            ai_generator_fn=ai_gen_fn,
            on_stage_progress=on_stage,
        )

        if res.changes:
            self.client.insert("changes", [c.to_dict() for c in res.changes], upsert=True)

        # Persist any new ai_cache entries
        if ai_enabled:
            new_cache_rows = [
                {
                    "workspace_id": ws_id,
                    "cache_key": ck,
                    "response": draft_val,
                    "usage": draft_val.get("usage"),
                }
                for ck, draft_val in workspace_cache.items()
                if ck not in initial_cache_keys
            ]
            if new_cache_rows:
                try:
                    self.client.insert("ai_cache", new_cache_rows, upsert=True)
                except Exception:
                    pass

        # Safe INV4-preserving alert persistence: check existing alerts for this run_id first
        if res.alerts:
            existing_alert_rows = self.client.select(
                "alerts",
                f"run_id=eq.{run_id}&select=id,priority,priority_overridden,review_state,review_revision",
            )
            existing_by_id = {r["id"]: r for r in existing_alert_rows}

            new_inserts: List[Dict[str, Any]] = []
            for alert in res.alerts:
                payload_dict = alert.to_insert_dict()
                if alert.id in existing_by_id:
                    ex = existing_by_id[alert.id]
                    # Preserve human priority override if set; never touch review_state or review_revision (INV4)
                    if ex.get("priority_overridden"):
                        payload_dict.pop("priority", None)
                    self.client.update("alerts", f"id=eq.{alert.id}", payload_dict)
                else:
                    new_inserts.append(payload_dict)

            if new_inserts:
                self.client.insert("alerts", new_inserts, upsert=False)

        self.client.update(
            "comparison_runs",
            f"id=eq.{run_id}",
            {
                "status": res.status,
                "stage": res.stage,
                "progress_pct": res.progress_pct,
                "errors": res.errors,
                "metrics": res.metrics,
                "finished_at": utc_now_iso(),
            },
        )
        self.client.update(
            "jobs",
            f"id=eq.{job_id}",
            {"status": res.status, "stage": res.stage, "progress_pct": 100, "finished_at": utc_now_iso()},
        )

    def _handle_ai_retry(self, job_id: str, alert_id: str) -> None:
        alert_rows = self.client.select("alerts", f"id=eq.{alert_id}")
        if not alert_rows:
            raise ValueError(f"Alert not found: {alert_id}")
        alert_row = alert_rows[0]
        run_id = alert_row["run_id"]
        change_row = self.client.select("changes", f"id=eq.{alert_row['change_id']}")[0]

        change_obj = ChangeRecord(
            id=change_row["id"],
            workspace_id=change_row["workspace_id"],
            run_id=change_row["run_id"],
            change_key=change_row["change_key"],
            type=change_row["type"],
            moved=bool(change_row.get("moved", False)),
            old_span_id=change_row.get("old_span_id"),
            new_span_id=change_row.get("new_span_id"),
            old_excerpt=change_row.get("old_excerpt"),
            new_excerpt=change_row.get("new_excerpt"),
            token_ops=change_row.get("token_ops") or [],
            flags=change_row.get("flags") or [],
            categories=change_row.get("categories") or [],
            primary_category=change_row.get("primary_category", "uncategorized"),
            matched_rules=change_row.get("matched_rules") or [],
            base_priority=change_row.get("base_priority", "normal"),
        )

        span_ids = [s for s in [change_obj.old_span_id, change_obj.new_span_id, alert_row["passage_span_id"]] if s]
        stored_spans: Dict[str, SpanRecord] = {}
        for sid in span_ids:
            s_rows = self.client.select("spans", f"id=eq.{sid}")
            if s_rows:
                r = s_rows[0]
                stored_spans[sid] = SpanRecord(
                    id=r["id"],
                    workspace_id=r["workspace_id"],
                    version_id=r["version_id"],
                    seq=r["seq"],
                    page=r["page"],
                    section=r.get("section"),
                    section_path=r.get("section_path"),
                    start_offset=r["start_offset"],
                    end_offset=r["end_offset"],
                    raw_text=r["raw_text"],
                    is_heading=bool(r.get("is_heading", False)),
                    is_boilerplate=bool(r.get("is_boilerplate", False)),
                )

        passage_span = stored_spans[alert_row["passage_span_id"]]
        ai_gen_fn, _ = resolve_configured_ai_generator()

        try:
            draft = ai_gen_fn(change_obj, passage_span)
            ok, _ = validate_ai_draft(
                draft=draft,
                change=change_obj,
                passage_span=passage_span,
                stored_spans=stored_spans,
            )
            if ok:
                self.client.update(
                    "alerts",
                    f"id=eq.{alert_id}",
                    {
                        "ai_status": "ok",
                        "ai_summary": draft["summary"].strip(),
                        "ai_rationale": draft["rationale"].strip(),
                        "ai_uncertainty": (draft.get("uncertainty") or "").strip() or None,
                        "cited_span_ids": list(draft["cited_span_ids"]),
                    },
                )
            else:
                self.client.update(
                    "alerts",
                    f"id=eq.{alert_id}",
                    {
                        "ai_status": "rejected_validation",
                        "ai_summary": None,
                        "ai_rationale": None,
                        "ai_uncertainty": None,
                        "cited_span_ids": [],
                    },
                )
        except Exception:
            self.client.update(
                "alerts",
                f"id=eq.{alert_id}",
                {
                    "ai_status": "unavailable",
                    "ai_summary": None,
                    "ai_rationale": None,
                    "ai_uncertainty": None,
                    "cited_span_ids": [],
                },
            )

        # Keep comparison_runs.status truthful (Section 5.1): if all alerts for run_id are now resolved, promote to 'complete'
        run_alerts = self.client.select("alerts", f"run_id=eq.{run_id}&select=id,ai_status")
        if all(a.get("ai_status") in ("ok", "disabled", "rejected_validation") for a in run_alerts):
            run_rows = self.client.select("comparison_runs", f"id=eq.{run_id}&select=id,errors,status")
            if run_rows:
                rem_errors = [
                    e
                    for e in (run_rows[0].get("errors") or [])
                    if e.get("code") not in ("AI_UNAVAILABLE", "AI_CAPPED")
                ]
                new_run_status = "complete" if not rem_errors else "partial"
                self.client.update(
                    "comparison_runs",
                    f"id=eq.{run_id}",
                    {"status": new_run_status, "errors": rem_errors},
                )

        self.client.update(
            "jobs",
            f"id=eq.{job_id}",
            {"status": "complete", "progress_pct": 100, "stage": "complete", "finished_at": utc_now_iso()},
        )


def main() -> None:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) and SUPABASE_SERVICE_ROLE_KEY to start the live worker.")
        return

    client = SupabaseServiceClient(url, key)
    daemon = VerityTrailWorkerDaemon(client)
    print(f"[VerityTrail Worker {daemon.worker_id}] Connected to {url}. Polling for jobs...")
    last_sweep = 0.0
    while True:
        now = time.time()
        if now - last_sweep > 60:
            try:
                client.rpc("sweep_dead_jobs")
            except Exception:
                pass
            last_sweep = now

        worked = daemon.process_next_job()
        if not worked:
            time.sleep(1.5)


if __name__ == "__main__":
    main()
