"""Deterministic section alignment, token-level diff, and high-stakes flag detector (Milestone I2 / FR05)."""

from __future__ import annotations
import difflib
import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from worker.models import ChangeRecord, SpanRecord, VERITYTRAIL_UUID_NAMESPACE

MONTHS_PATTERN = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
)

DATE_REGEX = re.compile(
    rf"\b(?:"
    rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS_PATTERN}(?:\s*,?\s*\d{{4}})?|"
    rf"{MONTHS_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{4}})?|"
    rf"\d{{4}}-\d{{2}}-\d{{2}}|"
    rf"\d{{1,2}}/\d{{1,2}}/\d{{2,4}}|"
    rf"\d{{1,2}}:\d{{2}}\s*(?:am|pm|a\.m\.|p\.m\.|hours|hrs|wat)?|"
    rf"\d{{1,2}}\s*(?:am|pm|a\.m\.|p\.m\.)"
    rf")\b",
    re.IGNORECASE,
)

NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "fourteen", "fifteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "ninety", "hundred", "thousand",
}

NUMBER_REGEX = re.compile(
    r"\b(?:\d+(?:,\d{3})*(?:\.\d+)?|"
    + "|".join(NUMBER_WORDS)
    + r")\b",
    re.IGNORECASE,
)

PERMISSIVE_MODALS = {"may", "can", "could", "optional", "optionally", "permitted", "encouraged"}
OBLIGATORY_MODALS = {"must", "shall", "required", "mandatory", "compulsory", "obligated", "only"}

NEGATION_TERMS = {
    "not", "no", "never", "neither", "nor", "none", "without",
    "prohibited", "banned", "forbid", "forbidden", "disallowed", "invalid", "ineligible",
}

WORD_TOKEN_RE = re.compile(r"\S+")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_section_title(section: Optional[str]) -> str:
    """
    Strip leading section/clause numbering (e.g. '4. Accreditation' -> 'accreditation',
    'SECTION II: PVC Collection' -> 'pvc collection') so simple section renumbering
    does not trigger a false `moved=True` flag.
    """
    if not section:
        return ""
    s = normalize_whitespace(section)
    s = re.sub(
        r"^(?:(?:SECTION|PART|CHAPTER|CLAUSE|ARTICLE|SCHEDULE|ITEM)\s+[0-9IVXLC]+[A-Z]?\s*[:.\-–—)]?\s*|"
        r"\d+(?:\.\d+){0,2}\s*[:.\-–—)]?\s*)",
        "",
        s,
        flags=re.IGNORECASE,
    )
    return s.strip().lower()


def _tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    """Return list of (token_str, start_offset, end_offset) in text."""
    return [(m.group(0), m.start(), m.end()) for m in WORD_TOKEN_RE.finditer(text)]


def _strip_Edges(token: str) -> str:
    return token.strip(".,;:!?\"'()[]{}").lower()


def compute_token_ops(old_text: str, new_text: str) -> List[Dict[str, Any]]:
    """
    Compute token-level operations with exact 0-based character offsets
    into old_text and new_text (Section 5.4).
    """
    old_tokens = _tokenize_with_offsets(old_text)
    new_tokens = _tokenize_with_offsets(new_text)

    old_norm = [t[0] for t in old_tokens]
    new_norm = [t[0] for t in new_tokens]

    matcher = difflib.SequenceMatcher(a=old_norm, b=new_norm, autojunk=False)
    ops: List[Dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "replace":
            o_start = old_tokens[i1][1]
            o_end = old_tokens[i2 - 1][2]
            n_start = new_tokens[j1][1]
            n_end = new_tokens[j2 - 1][2]

            # Trim trailing common punctuation (e.g. period at end of sentence)
            while o_end > o_start and n_end > n_start and old_text[o_end - 1] == new_text[n_end - 1] and old_text[o_end - 1] in ".,;:!?)":
                o_end -= 1
                n_end -= 1

            # Trim leading common punctuation
            while o_start < o_end and n_start < n_end and old_text[o_start] == new_text[n_start] and old_text[o_start] in "(\"'":
                o_start += 1
                n_start += 1

            if o_start < o_end or n_start < n_end:
                op_kind = "replace"
                if o_start == o_end:
                    op_kind = "insert"
                elif n_start == n_end:
                    op_kind = "delete"
                ops.append(
                    {
                        "op": op_kind,
                        "old": {
                            "text": old_text[o_start:o_end],
                            "start": o_start,
                            "end": o_end,
                        },
                        "new": {
                            "text": new_text[n_start:n_end],
                            "start": n_start,
                            "end": n_end,
                        },
                    }
                )
        elif tag == "delete":
            o_start = old_tokens[i1][1]
            o_end = old_tokens[i2 - 1][2]
            n_pos = new_tokens[j1][1] if j1 < len(new_tokens) else len(new_text)
            ops.append(
                {
                    "op": "delete",
                    "old": {
                        "text": old_text[o_start:o_end],
                        "start": o_start,
                        "end": o_end,
                    },
                    "new": {
                        "text": "",
                        "start": n_pos,
                        "end": n_pos,
                    },
                }
            )
        elif tag == "insert":
            n_start = new_tokens[j1][1]
            n_end = new_tokens[j2 - 1][2]
            o_pos = old_tokens[i1][1] if i1 < len(old_tokens) else len(old_text)
            ops.append(
                {
                    "op": "insert",
                    "old": {
                        "text": "",
                        "start": o_pos,
                        "end": o_pos,
                    },
                    "new": {
                        "text": new_text[n_start:n_end],
                        "start": n_start,
                        "end": n_end,
                    },
                }
            )

    return ops


def detect_change_flags(
    old_text: Optional[str],
    new_text: Optional[str],
    token_ops: List[Dict[str, Any]],
) -> List[str]:
    """
    Detect high-stakes token flags:
    - date_change
    - number_change
    - modal_flip
    - negation_flip
    """
    flags: List[str] = []

    if old_text and new_text and token_ops:
        changed_old_chunks = " ".join(op["old"]["text"] for op in token_ops if op["old"]["text"])
        changed_new_chunks = " ".join(op["new"]["text"] for op in token_ops if op["new"]["text"])
        combined_changed = f"{changed_old_chunks} || {changed_new_chunks}"

        old_dates = [m.group(0).lower() for m in DATE_REGEX.finditer(old_text)]
        new_dates = [m.group(0).lower() for m in DATE_REGEX.finditer(new_text)]
        if old_dates != new_dates or DATE_REGEX.search(combined_changed):
            flags.append("date_change")

        # Remove matched date substrings before checking standalone number changes
        old_no_dates = DATE_REGEX.sub(" ", old_text)
        new_no_dates = DATE_REGEX.sub(" ", new_text)
        old_nums = [m.group(0).lower() for m in NUMBER_REGEX.finditer(old_no_dates)]
        new_nums = [m.group(0).lower() for m in NUMBER_REGEX.finditer(new_no_dates)]
        if old_nums != new_nums:
            flags.append("number_change")

        old_words = {_strip_Edges(w) for w in changed_old_chunks.split() if _strip_Edges(w)}
        new_words = {_strip_Edges(w) for w in changed_new_chunks.split() if _strip_Edges(w)}

        # Check modal flip (permissive <-> obligatory, or modal added/removed in diff)
        old_has_perm = bool(old_words & PERMISSIVE_MODALS)
        old_has_oblig = bool(old_words & OBLIGATORY_MODALS)
        new_has_perm = bool(new_words & PERMISSIVE_MODALS)
        new_has_oblig = bool(new_words & OBLIGATORY_MODALS)
        if (old_has_perm and new_has_oblig) or (old_has_oblig and new_has_perm) or (
            (old_has_oblig ^ new_has_oblig) and (old_words or new_words)
        ):
            flags.append("modal_flip")

        # Check negation flip
        old_neg = len([w for w in changed_old_chunks.split() if _strip_Edges(w) in NEGATION_TERMS])
        new_neg = len([w for w in changed_new_chunks.split() if _strip_Edges(w) in NEGATION_TERMS])
        if old_neg != new_neg:
            flags.append("negation_flip")

    return flags


def _span_similarity(old_span: SpanRecord, new_span: SpanRecord) -> float:
    """Compute similarity between two spans considering text overlap and section context."""
    if old_span.is_heading != new_span.is_heading:
        return 0.0

    old_norm = normalize_whitespace(old_span.raw_text).lower()
    new_norm = normalize_whitespace(new_span.raw_text).lower()
    if old_norm == new_norm:
        return 1.0

    old_words = set(re.findall(r"[a-z0-9]+", old_norm))
    new_words = set(re.findall(r"[a-z0-9]+", new_norm))
    if not old_words or not new_words:
        return 0.0

    jaccard = len(old_words & new_words) / len(old_words | new_words)
    seq_ratio = difflib.SequenceMatcher(a=old_norm, b=new_norm, autojunk=False).ratio()

    section_bonus = 0.08 if (
        old_span.section
        and new_span.section
        and normalize_section_title(old_span.section) == normalize_section_title(new_span.section)
    ) else 0.0

    return min(0.99, (0.45 * jaccard) + (0.55 * seq_ratio) + section_bonus)


def diff_version_spans(
    *,
    workspace_id: str,
    run_id: str,
    old_spans: List[SpanRecord],
    new_spans: List[SpanRecord],
) -> List[ChangeRecord]:
    """
    Deterministically align sections and paragraphs between old_spans and new_spans,
    producing ChangeRecord items (insertion, deletion, replacement) with exact token_ops and flags.
    Pure headings without substantive body meaning or boilerplate spans are filtered properly.
    """
    old_filtered = [s for s in old_spans if not s.is_boilerplate]
    new_filtered = [s for s in new_spans if not s.is_boilerplate]

    matched_old: Set[int] = set()
    matched_new: Set[int] = set()

    # Pass 1: Exact normalized matches (suppresses whitespace-only differences, FR05)
    new_by_norm: Dict[str, List[int]] = {}
    for j, ns in enumerate(new_filtered):
        norm = normalize_whitespace(ns.raw_text)
        new_by_norm.setdefault(norm, []).append(j)

    for i, os in enumerate(old_filtered):
        norm = normalize_whitespace(os.raw_text)
        candidates = new_by_norm.get(norm, [])
        for j in candidates:
            if j not in matched_new:
                matched_old.add(i)
                matched_new.add(j)
                break

    # Pass 2: Pair modified spans (replacements) above similarity threshold
    candidate_pairs: List[Tuple[float, int, int]] = []
    for i, os in enumerate(old_filtered):
        if i in matched_old or os.is_heading:
            continue
        for j, ns in enumerate(new_filtered):
            if j in matched_new or ns.is_heading:
                continue
            sim = _span_similarity(os, ns)
            if sim >= 0.38:
                candidate_pairs.append((sim, i, j))

    # Greedy best-first pairing (deterministic tie-breaking by i, j)
    candidate_pairs.sort(key=lambda x: (-x[0], x[1], x[2]))
    replacements: List[Tuple[int, int]] = []
    for sim, i, j in candidate_pairs:
        if i not in matched_old and j not in matched_new:
            matched_old.add(i)
            matched_new.add(j)
            replacements.append((i, j))

    # Also check if any headings were edited in place (e.g. numbered heading title changed)
    for i, os in enumerate(old_filtered):
        if i in matched_old or not os.is_heading:
            continue
        for j, ns in enumerate(new_filtered):
            if j in matched_new or not ns.is_heading:
                continue
            if _span_similarity(os, ns) >= 0.55:
                matched_old.add(i)
                matched_new.add(j)
                # Heading-only renames that match aren't substantive rule changes unless body changed
                break

    # Collect raw change events ordered by document progression
    raw_events: List[Tuple[Tuple[int, int], str, Optional[SpanRecord], Optional[SpanRecord], bool]] = []

    for i, j in replacements:
        os = old_filtered[i]
        ns = new_filtered[j]
        old_sec = normalize_section_title(os.section)
        new_sec = normalize_section_title(ns.section)
        moved = bool(old_sec and new_sec and old_sec != new_sec and abs(i - j) >= 2)
        raw_events.append(((ns.seq, os.seq), "replacement", os, ns, moved))

    for i, os in enumerate(old_filtered):
        if i not in matched_old and not os.is_heading:
            raw_events.append(((os.seq, os.seq), "deletion", os, None, False))

    for j, ns in enumerate(new_filtered):
        if j not in matched_new and not ns.is_heading:
            raw_events.append(((ns.seq, ns.seq), "insertion", None, ns, False))

    raw_events.sort(key=lambda e: e[0])

    changes: List[ChangeRecord] = []
    for idx, (_, change_type, os, ns, moved) in enumerate(raw_events, start=1):
        change_key = f"chg-{idx:04d}"
        change_id = str(
            uuid.uuid5(VERITYTRAIL_UUID_NAMESPACE, f"change:{run_id}:{change_key}")
        )

        old_excerpt = os.raw_text if os is not None else None
        new_excerpt = ns.raw_text if ns is not None else None

        if change_type == "replacement" and old_excerpt is not None and new_excerpt is not None:
            token_ops = compute_token_ops(old_excerpt, new_excerpt)
            flags = detect_change_flags(old_excerpt, new_excerpt, token_ops)
        else:
            token_ops = []
            flags = []

        changes.append(
            ChangeRecord(
                id=change_id,
                workspace_id=workspace_id,
                run_id=run_id,
                change_key=change_key,
                type=change_type,
                moved=moved,
                old_span_id=os.id if os is not None else None,
                new_span_id=ns.id if ns is not None else None,
                old_excerpt=old_excerpt,
                new_excerpt=new_excerpt,
                token_ops=token_ops,
                flags=flags,
            )
        )

    return changes
