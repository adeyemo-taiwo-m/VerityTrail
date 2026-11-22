"""Core data models matching the Supabase Postgres contract (docs/CONTRACT.md)."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import uuid

# Namespace UUID for deterministic alert IDs (INV7)
VERITYTRAIL_UUID_NAMESPACE = uuid.UUID("7f9c2d10-8a4e-4b3b-9c2a-1e5d8f3a7b90")

VALID_CATEGORIES = (
    "deadlines_timelines",
    "eligibility",
    "required_documents",
    "polling_unit_accreditation",
    "cvr_transfer",
    "uncategorized",
)

VALID_FLAGS = (
    "date_change",
    "number_change",
    "modal_flip",
    "negation_flip",
)

VALID_EXTRACTION_STATUSES = (
    "pending",
    "extracting",
    "complete",
    "incomplete",
    "failed",
    "rejected",
)

VALID_AI_STATUSES = (
    "not_run",
    "disabled",
    "ok",
    "unavailable",
    "rejected_validation",
    "capped",
)


def deterministic_alert_id(run_id: str, change_key: str, passage_span_id: str) -> str:
    """Generate deterministic UUIDv5 for an alert so retries never duplicate alerts (INV7)."""
    name = f"{run_id}:{change_key}:{passage_span_id}"
    return str(uuid.uuid5(VERITYTRAIL_UUID_NAMESPACE, name))


@dataclass
class PageRecord:
    version_id: str
    page: int
    status: str  # 'ok' | 'blank' | 'unreadable'
    reason: Optional[str] = None
    char_count: int = 0
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpanRecord:
    id: str
    workspace_id: str
    version_id: str
    seq: int
    page: int
    section: Optional[str]
    section_path: Optional[str]
    start_offset: int
    end_offset: int
    raw_text: str
    is_heading: bool = False
    is_boilerplate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    version_id: str
    workspace_id: str
    extraction_status: str  # 'complete' | 'incomplete' | 'failed' | 'rejected'
    extraction_message: Optional[str]
    extractor_version: str
    page_count: Optional[int]
    full_text: Optional[str]
    pages: List[PageRecord] = field(default_factory=list)
    spans: List[SpanRecord] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def verify_inv2(self) -> bool:
        """INV2: full_text[start_offset:end_offset] == raw_text for every span."""
        if self.full_text is None:
            return len(self.spans) == 0
        for s in self.spans:
            if s.start_offset < 0 or s.end_offset <= s.start_offset:
                return False
            if self.full_text[s.start_offset : s.end_offset] != s.raw_text:
                return False
        return True


@dataclass
class ChangeRecord:
    id: str
    workspace_id: str
    run_id: str
    change_key: str
    type: str  # 'insertion' | 'deletion' | 'replacement'
    moved: bool
    old_span_id: Optional[str]
    new_span_id: Optional[str]
    old_excerpt: Optional[str]
    new_excerpt: Optional[str]
    token_ops: List[Dict[str, Any]] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    primary_category: str = "uncategorized"
    matched_rules: List[Dict[str, Any]] = field(default_factory=list)
    base_priority: str = "normal"  # 'high' | 'normal'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertRecord:
    id: str
    workspace_id: str
    run_id: str
    change_id: str
    material_version_id: str
    passage_span_id: str
    score: float
    confidence_band: str  # 'strong' | 'likely' | 'uncertain'
    match_reasons: List[Dict[str, Any]] = field(default_factory=list)
    priority: str = "normal"  # 'high' | 'normal'
    ai_status: str = "not_run"
    ai_summary: Optional[str] = None
    ai_rationale: Optional[str] = None
    ai_uncertainty: Optional[str] = None
    cited_span_ids: List[str] = field(default_factory=list)

    def to_insert_dict(self) -> Dict[str, Any]:
        """Convert to dict for DB insert/upsert, strictly omitting review_* fields (INV4)."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "run_id": self.run_id,
            "change_id": self.change_id,
            "material_version_id": self.material_version_id,
            "passage_span_id": self.passage_span_id,
            "score": round(float(self.score), 4),
            "confidence_band": self.confidence_band,
            "match_reasons": self.match_reasons,
            "priority": self.priority,
            "ai_status": self.ai_status,
            "ai_summary": self.ai_summary,
            "ai_rationale": self.ai_rationale,
            "ai_uncertainty": self.ai_uncertainty,
            "cited_span_ids": self.cited_span_ids,
        }
