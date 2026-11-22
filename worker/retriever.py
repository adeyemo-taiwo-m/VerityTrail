"""Snapshot passage retrieval, Nigerian electoral synonym expansion, multilingual concept bridge, and deterministic alert generation (Milestone I3 / FR07, FR13, INV7)."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from worker.extractor import detect_nigerian_language
from worker.models import AlertRecord, ChangeRecord, SpanRecord, deterministic_alert_id

STOPWORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can", "do",
    "for", "from", "has", "have", "he", "her", "his", "how", "if", "in", "into",
    "is", "it", "its", "may", "more", "must", "new", "no", "not", "now", "of",
    "on", "one", "only", "or", "other", "our", "out", "over", "shall", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "those", "through", "to", "under",
    "until", "up", "upon", "use", "used", "using", "very", "was", "we", "were",
    "what", "when", "where", "which", "while", "who", "whom", "will", "with",
    "within", "would", "you", "your",
    "citizen", "citizens", "election", "elections", "eligible", "nigeria",
    "nigerian", "official", "person", "people", "public", "registered",
    "section", "state", "vote", "voter", "voters", "voting",
}

BROAD_ELECTORAL_TERMS: Set[str] = {
    "accredited", "accreditation", "applicant", "applicants", "application",
    "applications", "bvas", "card", "centre", "centres", "center", "centers",
    "collation", "collection", "commission", "day", "days", "device", "form",
    "headquarters", "hours", "inec", "local", "observer", "observers",
    "office", "officer", "officers", "permanent", "poll", "polling",
    "presiding", "pvc", "register", "registration", "result", "results",
    "sheet", "unit", "units", "ward",
}

GENERIC_DIFF_TOKENS: Set[str] = STOPWORDS | {
    "days", "day", "hours", "hour", "months", "month", "years", "year",
}

# Equivalent duration/quantity phrases in Nigerian civic guides
VALUE_EQUIVALENCES: Dict[str, Tuple[str, ...]] = {
    "30 days": ("one month", "1 month", "thirty days", "kwana 30", "ọjọ́ 30", "ụbọchị 30"),
    "14 days": ("two weeks", "2 weeks", "fourteen days", "kwana 14", "ọjọ́ 14", "ụbọchị 14"),
    "7 days": ("one week", "1 week", "seven days", "kwana 7", "ọjọ́ 7", "ụbọchị 7"),
    "21 days": ("three weeks", "3 weeks", "twenty-one days"),
    "60 days": ("two months", "2 months", "sixty days"),
    "90 days": ("three months", "3 months", "ninety days"),
    "12 months": ("one year", "1 year", "twelve months"),
    "2:00 pm": ("2 pm", "14:00", "agogo meji", "karfe 2"),
}

# Multi-word phrase -> canonical stems (English paraphrases + Yoruba/Igbo/Hausa/Pidgin bridge for FR13)
CONCEPT_SYNONYM_PHRASES: Tuple[Tuple[re.Pattern[str], Tuple[str, ...]], ...] = (
    (re.compile(r"\b(?:permanent\s+voter'?s?\s+card|voter'?s?\s+card|pvc|katin\s+za[ɓb]e|k[áa]d[ìi]\s+[ìi]d[ìi]b[òo]|kaad[ịi]\s+nt[ụu]li\s+aka)\b", re.IGNORECASE), ("pvc", "card")),
    (re.compile(r"\b(?:thumbprint|fingerprint|biometric\s+print)\b", re.IGNORECASE), ("fingerprint", "biometric")),
    (re.compile(r"\b(?:pick\s+up|go\s+collect|gba\s+k[áa]d[ìi]|kar[ɓb]i\s+katin|nata\s+kaad[ịi])\b", re.IGNORECASE), ("collect", "notif")),
    (re.compile(r"\b(?:rijista|[ìi]for[úu]k[ọo]s[íi]l[ẹè]|ndebanye\s+aha)\b", re.IGNORECASE), ("registr", "centre")),
    (re.compile(r"\b(?:internally\s+displaced|displaced\s+persons|idp|sansanin\s+gudun\s+hijira)\b", re.IGNORECASE), ("displac", "idp", "camp")),
    (re.compile(r"\b(?:bvas\s+machine|accreditation\s+machine|bimodal\s+device)\b", re.IGNORECASE), ("bvas", "accredit")),
    (re.compile(r"\b(?:one\s+month|1\s+month)\b", re.IGNORECASE), ("30", "day")),
    (re.compile(r"\b(?:two\s+weeks|2\s+weeks)\b", re.IGNORECASE), ("14", "day")),
    (re.compile(r"\b(?:one\s+week|1\s+week)\b", re.IGNORECASE), ("7", "day")),
)


def _normalize_stem(word: str) -> str:
    """Light suffix and synonym normalization so electoral word forms align."""
    w = word.lower().strip("'")
    if w in ("register", "registered", "registering", "registration", "registrants", "rijista"):
        return "registr"
    if w in ("collect", "collected", "collecting", "collection"):
        return "collect"
    if w in ("accredit", "accredited", "accreditation"):
        return "accredit"
    if w in ("reside", "residing", "resident", "residency"):
        return "residen"
    if w in ("relocate", "relocated", "relocation"):
        return "relocat"
    if w in ("assist", "assisted", "assisting", "assistance"):
        return "assist"
    if w in ("replace", "replaced", "replacing", "replacement"):
        return "replac"
    if w in ("split", "splitting"):
        return "split"
    if w in ("thumbprint", "thumbprints", "fingerprint", "fingerprints"):
        return "fingerprint"
    if w in ("notification", "notified", "notify"):
        return "notif"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _extract_content_terms(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w.strip("'") for w in words if len(w.strip("'")) >= 3 and w.strip("'") not in STOPWORDS]


def _extract_expanded_stems(text: str) -> Set[str]:
    """Extract normalized word stems plus canonical concept synonyms (paraphrase & multilingual bridge)."""
    stems = {_normalize_stem(t) for t in _extract_content_terms(text)}
    for pat, canonical_stems in CONCEPT_SYNONYM_PHRASES:
        if pat.search(text):
            stems.update(canonical_stems)
    return stems


def _extract_specific_topic_stems(text: str) -> Set[str]:
    """Extract distinctive topic stems (excluding generic/broad electoral boilerplate)."""
    stems = _extract_expanded_stems(text)
    broad_stems = {_normalize_stem(b) for b in BROAD_ELECTORAL_TERMS}
    return {s for s in stems if s not in broad_stems and not s.isdigit()}


def _find_exact_substring_ci(haystack: str, needle: str) -> Optional[Tuple[int, int, str]]:
    """Case-insensitive substring search returning (start, end, exact_slice_in_haystack)."""
    needle_clean = needle.strip()
    if len(needle_clean) < 2:
        return None
    pattern = re.compile(r"(?<!\w)" + re.escape(needle_clean) + r"(?!\w)", re.IGNORECASE)
    m = pattern.search(haystack)
    if m:
        return (m.start(), m.end(), haystack[m.start() : m.end()])
    return None


def _find_best_phrase_overlap(reference_text: str, passage_text: str) -> Optional[Tuple[int, int, str, int]]:
    """
    Find the longest contiguous phrase (2 to 8 words) from reference_text
    that appears in passage_text and contains at least one non-stopword content term.
    Returns (start, end, matched_slice, content_word_count).
    """
    ref_tokens = re.findall(r"[A-Za-z0-9']+", reference_text)
    if len(ref_tokens) < 2:
        return None

    best: Optional[Tuple[int, int, str, int]] = None
    max_n = min(8, len(ref_tokens))
    for n in range(max_n, 1, -1):
        for i in range(len(ref_tokens) - n + 1):
            window = ref_tokens[i : i + n]
            content_count = sum(1 for w in window if w.lower().strip("'") not in STOPWORDS and len(w) >= 3)
            if content_count == 0:
                continue
            phrase_regex = r"\b" + r"[\s,;:']+?".join(re.escape(w) for w in window) + r"\b"
            m = re.search(phrase_regex, passage_text, re.IGNORECASE)
            if m:
                cand = (m.start(), m.end(), passage_text[m.start() : m.end()], content_count)
                if best is None or (content_count, m.end() - m.start()) > (best[3], best[1] - best[0]):
                    best = cand
        if best is not None and best[3] >= 2:
            break
    return best


def _extract_old_value_candidates(change: ChangeRecord) -> List[str]:
    """
    Extract specific old value strings from token_ops (and surrounding unit words like '30 days').
    """
    candidates: List[str] = []
    old_text = change.old_excerpt or ""
    for op in change.token_ops:
        old_info = op.get("old") or {}
        val = (old_info.get("text") or "").strip()
        if not val:
            continue
        start = int(old_info.get("start", 0))
        end = int(old_info.get("end", 0))

        if re.fullmatch(r"\d+(?:,\d{3})*", val) and end < len(old_text):
            after_match = re.match(
                r"^\s+(days|hours|weeks|months|years|voters|percent|%|km|metres|meters)\b",
                old_text[end:],
                re.IGNORECASE,
            )
            if after_match:
                expanded = old_text[start : end + after_match.end()].strip()
                candidates.append(expanded)
        candidates.append(val)
    return candidates


def match_change_to_passage(
    change: ChangeRecord,
    passage_span: SpanRecord,
) -> Optional[Tuple[float, str, List[Dict[str, Any]]]]:
    """
    Evaluate whether passage_span is potentially affected by change.
    Supports exact repetition, lexical overlap, Nigerian electoral paraphrase synonyms,
    and light multilingual matching (FR13).
    """
    if passage_span.is_heading or passage_span.is_boilerplate:
        return None

    p_text = passage_span.raw_text
    if not p_text or len(p_text.strip()) < 10:
        return None

    old_text = change.old_excerpt or ""
    new_text = change.new_excerpt or ""

    old_stems = _extract_expanded_stems(old_text)
    new_stems = _extract_expanded_stems(new_text)
    change_stems = old_stems | new_stems
    passage_stems = _extract_expanded_stems(p_text)

    if not change_stems or not passage_stems:
        return None

    shared_old_stems = old_stems & passage_stems

    change_specific_stems = _extract_specific_topic_stems(f"{old_text} {new_text}")
    old_specific_stems = _extract_specific_topic_stems(old_text)
    passage_specific_stems = _extract_specific_topic_stems(p_text)
    shared_specific_stems = change_specific_stems & passage_specific_stems

    diff_old_text = " ".join((op.get("old") or {}).get("text", "") for op in change.token_ops)
    diff_old_stems = _extract_expanded_stems(diff_old_text)

    # Detect if the passage is in Yoruba, Igbo, Hausa, or Pidgin (FR13)
    p_lang, _, _ = detect_nigerian_language(p_text)
    is_multilingual_passage = p_lang != "en"

    # Topic alignment check
    non_num_old_specific = {s for s in old_specific_stems if not s.isdigit()}
    if not is_multilingual_passage:
        if non_num_old_specific and not (non_num_old_specific & passage_specific_stems) and len(shared_old_stems) < 3:
            return None

    is_pure_inline_addition = (
        change.type == "replacement"
        and bool(change.token_ops)
        and all(not (op.get("old") or {}).get("text", "").strip() for op in change.token_ops)
    )
    if is_pure_inline_addition and not is_multilingual_passage:
        overlap_ratio = len(shared_old_stems) / max(1, len(old_stems))
        if overlap_ratio < 0.60:
            return None
    elif change.type == "replacement" and diff_old_stems and not is_multilingual_passage:
        has_diff_old_stem = bool(diff_old_stems & passage_stems)
        overlap_ratio = len(shared_old_stems) / max(1, len(old_stems))
        if not has_diff_old_stem and overlap_ratio < 0.65:
            return None

    reasons: List[Dict[str, Any]] = []
    score = 0.0

    # 1. Check `repeats_old_value` (exact value OR canonical duration/value alias like "one month" == "30 days")
    old_val_candidates = _extract_old_value_candidates(change)
    repeated_old_val = False
    for cand in old_val_candidates:
        if cand.lower() in GENERIC_DIFF_TOKENS:
            continue
        if re.fullmatch(r"\d+", cand) and len(shared_old_stems) < 3 and not is_multilingual_passage:
            continue

        hit = _find_exact_substring_ci(p_text, cand)
        reason_type = "repeats_old_value"
        if hit is None and cand.lower() in VALUE_EQUIVALENCES:
            for alias in VALUE_EQUIVALENCES[cand.lower()]:
                hit = _find_exact_substring_ci(p_text, alias)
                if hit is not None:
                    reason_type = "semantic"
                    break

        if hit is not None:
            cand_stems = _extract_expanded_stems(cand)
            context_stems = (old_stems - cand_stems) & passage_stems
            if len(context_stems) >= 1:
                s_idx, e_idx, exact_str = hit
                reasons.append(
                    {
                        "type": reason_type,
                        "text": exact_str,
                        "passage_start": s_idx,
                        "passage_end": e_idx,
                    }
                )
                score += 0.65 + (0.05 * len(context_stems))
                repeated_old_val = True
                break

    # 2. Check `old_wording_overlap`: phrase overlap with old_excerpt
    if old_text and not repeated_old_val:
        phrase_hit = _find_best_phrase_overlap(old_text, p_text)
        if phrase_hit is not None:
            s_idx, e_idx, exact_str, content_cnt = phrase_hit
            overlap_ratio = len(shared_old_stems) / max(1, len(old_stems))
            if (content_cnt >= 3 and overlap_ratio >= 0.40) or (content_cnt >= 2 and overlap_ratio >= 0.55):
                reasons.append(
                    {
                        "type": "old_wording_overlap",
                        "text": exact_str,
                        "passage_start": s_idx,
                        "passage_end": e_idx,
                    }
                )
                score += min(0.76, 0.25 + 0.12 * content_cnt + 0.30 * overlap_ratio)

    # 3. Check `semantic` paraphrase overlap when canonical synonyms match strongly even without contiguous phrase
    if old_text and not reasons and len(shared_old_stems) >= 4:
        overlap_ratio = len(shared_old_stems) / max(1, len(old_stems))
        if overlap_ratio >= 0.60 and bool(diff_old_stems & passage_stems):
            for pat, _ in CONCEPT_SYNONYM_PHRASES:
                m = pat.search(p_text)
                if m:
                    reasons.append(
                        {
                            "type": "semantic",
                            "text": p_text[m.start() : m.end()],
                            "passage_start": m.start(),
                            "passage_end": m.end(),
                        }
                    )
                    score += 0.58
                    break

    # 4. Check `topic_related` for insertions (only when >= 3 specific topic stems match)
    if change.type == "insertion" and len(shared_specific_stems) >= 3:
        phrase_hit = _find_best_phrase_overlap(new_text, p_text)
        if phrase_hit:
            s_idx, e_idx, exact_str, _ = phrase_hit
            reasons.append(
                {
                    "type": "topic_related",
                    "text": exact_str,
                    "passage_start": s_idx,
                    "passage_end": e_idx,
                }
            )
            score += 0.55

    if not reasons or score < 0.45:
        return None

    final_score = min(0.98, round(score, 4))

    if repeated_old_val or final_score >= 0.80:
        confidence_band = "strong"
    elif final_score >= 0.55 and change.type != "deletion":
        confidence_band = "likely"
    else:
        confidence_band = "uncertain"

    validated_reasons: List[Dict[str, Any]] = []
    for r in reasons:
        ps = int(r["passage_start"])
        pe = int(r["passage_end"])
        if 0 <= ps < pe <= len(p_text) and p_text[ps:pe] == r["text"]:
            validated_reasons.append(r)

    if not validated_reasons:
        return None

    return (final_score, confidence_band, validated_reasons)


def retrieve_affected_passages(
    *,
    workspace_id: str,
    run_id: str,
    changes: List[ChangeRecord],
    included_material_spans: Dict[str, List[SpanRecord]],
    max_alerts_per_change: int = 10,
) -> Tuple[List[AlertRecord], Dict[str, int]]:
    """
    Search all included material versions in the snapshot for passages affected by each change.
    Returns (alerts_list, candidates_per_change_map).
    """
    all_alerts: List[AlertRecord] = []
    candidates_per_change: Dict[str, int] = {}

    for change in changes:
        change_alerts: List[AlertRecord] = []
        for mat_version_id, spans in included_material_spans.items():
            for p_span in spans:
                match = match_change_to_passage(change, p_span)
                if match is None:
                    continue
                score, confidence_band, match_reasons = match
                alert_id = deterministic_alert_id(run_id, change.change_key, p_span.id)
                change_alerts.append(
                    AlertRecord(
                        id=alert_id,
                        workspace_id=workspace_id,
                        run_id=run_id,
                        change_id=change.id,
                        material_version_id=mat_version_id,
                        passage_span_id=p_span.id,
                        score=score,
                        confidence_band=confidence_band,
                        match_reasons=match_reasons,
                        priority=change.base_priority,
                    )
                )

        change_alerts.sort(key=lambda a: (-a.score, a.id))
        if len(change_alerts) > max_alerts_per_change:
            change_alerts = change_alerts[:max_alerts_per_change]

        candidates_per_change[change.id] = len(change_alerts)
        all_alerts.extend(change_alerts)

    return (all_alerts, candidates_per_change)
