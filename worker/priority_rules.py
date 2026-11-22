"""Transparent Nigerian electoral priority categorization rule engine (Milestone I2 / FR06)."""

from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any, Dict, List, Pattern, Tuple

from worker.models import ChangeRecord


@dataclass(frozen=True)
class PriorityRule:
    rule_id: str
    category: str
    pattern: Pattern[str]
    weight: int = 1


# Transparent regex rule definitions covering the 5 Nigerian electoral categories (FR06)
PRIORITY_RULES: Tuple[PriorityRule, ...] = (
    # 1. Deadlines & Timelines (deadlines_timelines)
    PriorityRule(
        "DL-01",
        "deadlines_timelines",
        re.compile(
            r"\b(?:deadline|deadlines|timeline|timelines|closing\s+date|commence|commencement|"
            r"expire|expires|expiration|extension|extended|postponed|rescheduled)\b",
            re.IGNORECASE,
        ),
        weight=3,
    ),
    PriorityRule(
        "DL-02",
        "deadlines_timelines",
        re.compile(
            r"\b(?:until|before|not\s+later\s+than|no\s+later\s+than|on\s+or\s+before)\s+"
            r"(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+|[A-Za-z]+\s+\d{1,2}|\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2})",
            re.IGNORECASE,
        ),
        weight=4,
    ),
    PriorityRule(
        "DL-03",
        "deadlines_timelines",
        re.compile(
            r"\b(?:within\s+\d+\s+(?:days|hours|weeks|months)|"
            r"\d+\s+(?:days|hours|weeks)\s+(?:prior\s+to|before|after|of\s+notification)|"
            r"between\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\s+and\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))",
            re.IGNORECASE,
        ),
        weight=4,
    ),
    # 2. Eligibility Criteria (eligibility)
    PriorityRule(
        "EL-01",
        "eligibility",
        re.compile(
            r"\b(?:at\s+least\s+\d+\s+years\s+old|18\s+years|eighteen\s+years|"
            r"citizen\s+of\s+nigeria|nigerian\s+citizen|citizenship|"
            r"eligible\s+to\s+vote|qualified\s+to\s+vote|qualified\s+to\s+register|"
            r"disqualified|ineligible|legal\s+capacity|ordinarily\s+resident|"
            r"internally\s+displaced\s+person|idp\s+voter|first-time\s+voter)\b",
            re.IGNORECASE,
        ),
        weight=3,
    ),
    # 3. Required Documents (required_documents)
    PriorityRule(
        "RD-01",
        "required_documents",
        re.compile(
            r"\b(?:permanent\s+voter'?s?\s+card|pvc|temporary\s+voter'?s?\s+card|tvc|"
            r"valid\s+form\s+of\s+identification|national\s+identification\s+number|nin|"
            r"voter'?s?\s+slip|registration\s+slip|affidavit|birth\s+certificate|"
            r"passport|driver'?s?\s+licen[cs]e|form\s+ec\s*[0-9a-z]+|incident\s+form)\b",
            re.IGNORECASE,
        ),
        weight=3,
    ),
    # 4. Polling Unit & Accreditation Procedures (polling_unit_accreditation)
    PriorityRule(
        "PU-01",
        "polling_unit_accreditation",
        re.compile(
            r"\b(?:accreditation|accredited|bvas|bimodal\s+voter\s+accreditation|"
            r"polling\s+unit|polling\s+station|presiding\s+officer|fingerprint|"
            r"biometric|facial\s+authentication|facial\s+recognition|ballot\s+paper|"
            r"ballot\s+box|cubicle|thumbprint|collation|irev|assistive\s+voting|braille\s+ballot)\b",
            re.IGNORECASE,
        ),
        weight=2,
    ),
    # 5. CVR / Transfer Rules (cvr_transfer)
    PriorityRule(
        "CV-01",
        "cvr_transfer",
        re.compile(
            r"\b(?:continuous\s+voter\s+registration|cvr|transfer\s+of\s+registration|"
            r"voter\s+transfer|relocation\s+of\s+polling|registration\s+centre|"
            r"registration\s+center|register\s+to\s+vote|claims\s+and\s+objections|"
            r"preliminary\s+register|update\s+voter\s+record|replacement\s+of\s+lost\s+pvc)\b",
            re.IGNORECASE,
        ),
        weight=2,
    ),
)


def classify_change_priority(change: ChangeRecord) -> ChangeRecord:
    """
    Evaluate transparent Nigerian electoral rules against a ChangeRecord,
    populating categories, primary_category, matched_rules, and base_priority.
    """
    matched_rules: List[Dict[str, Any]] = []
    category_scores: Dict[str, int] = {}
    first_seen_order: Dict[str, int] = {}
    order_counter = 0

    def record_cat(cat: str, weight: int) -> None:
        nonlocal order_counter
        category_scores[cat] = category_scores.get(cat, 0) + weight
        if cat not in first_seen_order:
            first_seen_order[cat] = order_counter
            order_counter += 1

    # Auto-categorize date_change as deadlines_timelines (Section 11)
    if "date_change" in change.flags:
        record_cat("deadlines_timelines", 5)

    # Focus rule matching on changed token slices first, plus full span context
    changed_text_lower = " ".join(
        f"{op['old']['text']} {op['new']['text']}" for op in change.token_ops
    ).lower()

    sides: List[Tuple[str, str]] = []
    if change.old_excerpt:
        sides.append(("old", change.old_excerpt))
    if change.new_excerpt:
        sides.append(("new", change.new_excerpt))

    seen_rule_side = set()
    for rule in PRIORITY_RULES:
        for side_name, text in sides:
            for m in rule.pattern.finditer(text):
                matched_str = m.group(0)
                key = (rule.rule_id, side_name, m.start(), m.end())
                if key in seen_rule_side:
                    continue
                seen_rule_side.add(key)

                # Boost weight if the matched phrase overlaps the changed token_ops
                in_diff_bonus = 2 if (changed_text_lower and matched_str.lower() in changed_text_lower) else 0
                record_cat(rule.category, rule.weight + in_diff_bonus)

                matched_rules.append(
                    {
                        "rule_id": rule.rule_id,
                        "category": rule.category,
                        "matched_text": matched_str,
                        "side": side_name,
                        "start": m.start(),
                        "end": m.end(),
                    }
                )
                break  # Record first match per (rule, side) to keep matched_rules concise

    if category_scores:
        ordered_cats = sorted(
            category_scores.keys(),
            key=lambda c: (-category_scores[c], first_seen_order[c]),
        )
        change.categories = ordered_cats
        change.primary_category = ordered_cats[0]
        change.base_priority = "high"
    else:
        change.categories = []
        change.primary_category = "uncategorized"
        # High-stakes token flags (modal_flip, negation_flip, number_change) still elevate priority if substantive
        if any(f in change.flags for f in ("date_change", "number_change", "modal_flip", "negation_flip")):
            change.base_priority = "high"
        else:
            change.base_priority = "normal"

    change.matched_rules = matched_rules
    return change
