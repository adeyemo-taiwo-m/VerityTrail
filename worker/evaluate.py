"""Automated evaluation harness for the VerityTrail Nigerian Electoral Benchmark (Milestone I5 / PRD Section 9)."""

from __future__ import annotations
import json
import math
import time
from typing import Any, Dict, List, Set, Tuple

from worker.ai_explainer import validate_ai_draft
from worker.extractor import compute_sha256, ingest_document_bytes
from worker.fixtures.nigerian_benchmark import (
    LabelledChangeSpec,
    MaterialFixture,
    SourcePairFixture,
    get_benchmark_dataset,
)
from worker.models import ChangeRecord, SpanRecord
from worker.runner import execute_comparison_pipeline


def _matches_labelled_change(change: ChangeRecord, spec: LabelledChangeSpec) -> bool:
    if change.type != spec.expected_type:
        return False
    if spec.old_substring and (not change.old_excerpt or spec.old_substring.lower() not in change.old_excerpt.lower()):
        return False
    if spec.new_substring and (not change.new_excerpt or spec.new_substring.lower() not in change.new_excerpt.lower()):
        return False
    return True


def run_benchmark_evaluation() -> Dict[str, Any]:
    pairs, materials = get_benchmark_dataset()
    ws_id = "00000000-0000-0000-0000-000000000001"

    # 1. Ingest all 30 materials once (warm index)
    material_spans_by_version: Dict[str, List[SpanRecord]] = {}
    material_id_to_version_id: Dict[str, str] = {}
    version_id_to_material_id: Dict[str, str] = {}
    all_stored_spans: Dict[str, SpanRecord] = {}
    total_unaffected_passages = 0

    for mat in materials:
        mv_id = f"mv-{mat.material_id}"
        material_id_to_version_id[mat.material_id] = mv_id
        version_id_to_material_id[mv_id] = mat.material_id
        raw_bytes = "\f".join(mat.pages).encode("utf-8")
        ext = ingest_document_bytes(
            version_id=mv_id,
            workspace_id=ws_id,
            file_bytes=raw_bytes,
            expected_sha256=compute_sha256(raw_bytes),
        )
        assert ext.extraction_status == "complete"
        assert ext.verify_inv2()
        material_spans_by_version[mv_id] = ext.spans
        for s in ext.spans:
            all_stored_spans[s.id] = s
            if not s.is_heading and not s.is_boilerplate:
                total_unaffected_passages += 1

    # Total non-heading body passages across 30 materials minus 42 affected = unaffected passages count
    # Build collection snapshot for each pair's corresponding materials (plus cross-collection noise materials)
    total_labelled_changes = 0
    found_labelled_changes = 0
    held_out_labelled_changes = 0
    held_out_found_changes = 0
    held_out_critical_total = 0
    held_out_critical_found = 0

    total_labelled_links = 0
    found_labelled_links = 0
    total_surfaced_links = 0
    relevant_surfaced_links = 0

    held_out_labelled_links = 0
    held_out_found_links = 0
    held_out_surfaced_links = 0
    held_out_relevant_surfaced = 0

    total_citations_checked = 0
    valid_citations_count = 0
    total_summaries_checked = 0
    faithful_summaries_count = 0

    per_category_stats: Dict[str, Dict[str, int]] = {}
    run_durations_sec: List[float] = []

    # Map each pair to all 30 materials in the snapshot (or pair-scoped + distractors)
    all_snapshot_items = [
        {
            "material_id": mat.material_id,
            "material_version_id": material_id_to_version_id[mat.material_id],
            "title": mat.title,
            "owner": mat.owner,
            "language": mat.language,
            "included": True,
            "exclusion_reason": None,
        }
        for mat in materials
    ]
    collection_snapshot = {
        "collection_id": "col-benchmark-30",
        "collection_name": "Nigerian Civic Voter Education Benchmark (30 Materials)",
        "materials": all_snapshot_items,
    }

    for pair in pairs:
        v1_id = f"src-{pair.pair_id}-v1"
        v2_id = f"src-{pair.pair_id}-v2"
        v1_bytes = "\f".join(pair.v1_pages).encode("utf-8")
        v2_bytes = "\f".join(pair.v2_pages).encode("utf-8")

        ext_v1 = ingest_document_bytes(
            version_id=v1_id,
            workspace_id=ws_id,
            file_bytes=v1_bytes,
            expected_sha256=compute_sha256(v1_bytes),
        )
        ext_v2 = ingest_document_bytes(
            version_id=v2_id,
            workspace_id=ws_id,
            file_bytes=v2_bytes,
            expected_sha256=compute_sha256(v2_bytes),
        )
        assert ext_v1.verify_inv2() and ext_v2.verify_inv2()
        for s in ext_v1.spans + ext_v2.spans:
            all_stored_spans[s.id] = s

        t_start = time.perf_counter()
        run_res = execute_comparison_pipeline(
            run_id=f"run-{pair.pair_id}",
            workspace_id=ws_id,
            old_version={"id": v1_id, "extraction_status": "complete"},
            new_version={"id": v2_id, "extraction_status": "complete"},
            old_spans=ext_v1.spans,
            new_spans=ext_v2.spans,
            collection_snapshot=collection_snapshot,
            material_spans_by_version=material_spans_by_version,
            ai_enabled=True,
        )
        elapsed_sec = time.perf_counter() - t_start
        run_durations_sec.append(elapsed_sec)

        is_held_out = pair.split == "held_out"

        # Match detected changes against ground-truth specs
        matched_change_map: Dict[int, ChangeRecord] = {}
        for spec_idx, spec in enumerate(pair.expected_changes):
            total_labelled_changes += 1
            cat_stat = per_category_stats.setdefault(
                spec.expected_category, {"labelled_changes": 0, "found_changes": 0}
            )
            cat_stat["labelled_changes"] += 1

            if is_held_out:
                held_out_labelled_changes += 1
                if spec.is_critical_date_or_eligibility:
                    held_out_critical_total += 1

            matched_chg = next((c for c in run_res.changes if _matches_labelled_change(c, spec)), None)
            if matched_chg is not None:
                found_labelled_changes += 1
                cat_stat["found_changes"] += 1
                matched_change_map[spec_idx] = matched_chg
                if is_held_out:
                    held_out_found_changes += 1
                    if spec.is_critical_date_or_eligibility:
                        held_out_critical_found += 1

        # Evaluate passage retrieval links (Precision & Recall)
        expected_alert_keys: Set[Tuple[str, str]] = set()  # (change_id, span_id)
        for spec_idx, spec in enumerate(pair.expected_changes):
            matched_chg = matched_change_map.get(spec_idx)
            for mat_id, quote_sub in spec.affected_material_ids:
                total_labelled_links += 1
                if is_held_out:
                    held_out_labelled_links += 1
                mv_id = material_id_to_version_id[mat_id]
                target_span = next(
                    (
                        s
                        for s in material_spans_by_version[mv_id]
                        if not s.is_heading and quote_sub.lower() in s.raw_text.lower()
                    ),
                    None,
                )
                assert target_span is not None, f"Benchmark fixture error: '{quote_sub}' not found in {mat_id}"
                if matched_chg is not None:
                    expected_alert_keys.add((matched_chg.id, target_span.id))
                    surfaced = any(
                        a.change_id == matched_chg.id and a.passage_span_id == target_span.id
                        for a in run_res.alerts
                    )
                    if surfaced:
                        found_labelled_links += 1
                        if is_held_out:
                            held_out_found_links += 1

        for alert in run_res.alerts:
            total_surfaced_links += 1
            if is_held_out:
                held_out_surfaced_links += 1
            if (alert.change_id, alert.passage_span_id) in expected_alert_keys:
                relevant_surfaced_links += 1
                if is_held_out:
                    held_out_relevant_surfaced += 1

            # Verify citation validity (INV3) & summary faithfulness
            for cid in alert.cited_span_ids:
                total_citations_checked += 1
                sp = all_stored_spans.get(cid)
                if sp is not None and len(sp.raw_text) == (sp.end_offset - sp.start_offset):
                    valid_citations_count += 1

            if alert.ai_status == "ok":
                total_summaries_checked += 1
                chg = next(c for c in run_res.changes if c.id == alert.change_id)
                p_span = all_stored_spans[alert.passage_span_id]
                valid_draft, _ = validate_ai_draft(
                    draft={
                        "summary": alert.ai_summary,
                        "rationale": alert.ai_rationale,
                        "uncertainty": alert.ai_uncertainty,
                        "cited_span_ids": alert.cited_span_ids,
                    },
                    change=chg,
                    passage_span=p_span,
                    stored_spans=all_stored_spans,
                )
                if valid_draft:
                    faithful_summaries_count += 1

    # Also run 10 additional warm benchmark iterations to compute 20-run p95 latency per NFR01
    while len(run_durations_sec) < 20:
        pair = pairs[len(run_durations_sec) % len(pairs)]
        v1_id = f"src-{pair.pair_id}-v1"
        v2_id = f"src-{pair.pair_id}-v2"
        ext_v1 = ingest_document_bytes(
            version_id=v1_id, workspace_id=ws_id, file_bytes="\f".join(pair.v1_pages).encode("utf-8")
        )
        ext_v2 = ingest_document_bytes(
            version_id=v2_id, workspace_id=ws_id, file_bytes="\f".join(pair.v2_pages).encode("utf-8")
        )
        t_start = time.perf_counter()
        execute_comparison_pipeline(
            run_id=f"perf-{len(run_durations_sec)}",
            workspace_id=ws_id,
            old_version={"id": v1_id, "extraction_status": "complete"},
            new_version={"id": v2_id, "extraction_status": "complete"},
            old_spans=ext_v1.spans,
            new_spans=ext_v2.spans,
            collection_snapshot=collection_snapshot,
            material_spans_by_version=material_spans_by_version,
            ai_enabled=True,
        )
        run_durations_sec.append(time.perf_counter() - t_start)

    sorted_durations = sorted(run_durations_sec)
    p95_idx = min(len(sorted_durations) - 1, math.ceil(0.95 * len(sorted_durations)) - 1)
    p95_sec = round(sorted_durations[p95_idx], 4)

    change_recall = found_labelled_changes / max(1, total_labelled_changes)
    held_out_change_recall = held_out_found_changes / max(1, held_out_labelled_changes)
    held_out_critical_recall = held_out_critical_found / max(1, held_out_critical_total)
    passage_precision = relevant_surfaced_links / max(1, total_surfaced_links)
    passage_recall = found_labelled_links / max(1, total_labelled_links)
    held_out_precision = held_out_relevant_surfaced / max(1, held_out_surfaced_links)
    held_out_recall = held_out_found_links / max(1, held_out_labelled_links)
    evidence_validity = valid_citations_count / max(1, total_citations_checked)
    summary_faithfulness = faithful_summaries_count / max(1, total_summaries_checked)

    report = {
        "dataset": {
            "source_pairs": len(pairs),
            "dev_pairs": sum(1 for p in pairs if p.split == "dev"),
            "held_out_pairs": sum(1 for p in pairs if p.split == "held_out"),
            "materials": len(materials),
            "labelled_changes": total_labelled_changes,
            "labelled_affected_links": total_labelled_links,
            "unaffected_passages": total_unaffected_passages - total_labelled_links,
        },
        "overall_metrics": {
            "meaningful_change_recall": {
                "found": found_labelled_changes,
                "total": total_labelled_changes,
                "pct": round(change_recall * 100, 2),
                "gate_pct": 95.0,
                "passed": change_recall >= 0.95,
            },
            "affected_passage_precision": {
                "relevant": relevant_surfaced_links,
                "surfaced": total_surfaced_links,
                "pct": round(passage_precision * 100, 2),
                "gate_pct": 80.0,
                "passed": passage_precision >= 0.80,
            },
            "affected_passage_recall": {
                "found": found_labelled_links,
                "total": total_labelled_links,
                "pct": round(passage_recall * 100, 2),
                "gate_pct": 85.0,
                "passed": passage_recall >= 0.85,
            },
            "evidence_validity": {
                "valid_citations": valid_citations_count,
                "total_citations": total_citations_checked,
                "pct": round(evidence_validity * 100, 2),
                "gate_pct": 100.0,
                "passed": evidence_validity == 1.0,
            },
            "summary_faithfulness": {
                "faithful": faithful_summaries_count,
                "total": total_summaries_checked,
                "pct": round(summary_faithfulness * 100, 2),
                "gate_pct": 100.0,
                "passed": summary_faithfulness == 1.0,
            },
            "performance_nfr01": {
                "runs_measured": len(run_durations_sec),
                "p95_seconds": p95_sec,
                "gate_seconds": 120.0,
                "passed": p95_sec <= 120.0,
            },
        },
        "held_out_metrics": {
            "change_recall_pct": round(held_out_change_recall * 100, 2),
            "critical_date_eligibility_recall_pct": round(held_out_critical_recall * 100, 2),
            "passage_precision_pct": round(held_out_precision * 100, 2),
            "passage_recall_pct": round(held_out_recall * 100, 2),
            "critical_gate_passed": held_out_critical_recall == 1.0,
        },
        "per_category": per_category_stats,
    }

    report["all_release_gates_passed"] = all(
        m["passed"] for m in report["overall_metrics"].values()
    ) and report["held_out_metrics"]["critical_gate_passed"]

    return report


if __name__ == "__main__":
    result = run_benchmark_evaluation()
    print(json.dumps(result, indent=2))
