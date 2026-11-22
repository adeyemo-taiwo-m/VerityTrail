"""Page-aware text extractor, sub-clause segmenter, multilingual detector, and immutable span indexer (Milestone I1 / FR02, FR03, FR13, INV2)."""

from __future__ import annotations
import hashlib
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None  # type: ignore

from worker import EXTRACTOR_VERSION
from worker.models import ExtractionResult, PageRecord, SpanRecord

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PAGES = 20

# Regex for detecting section headings in official Nigerian electoral notices
HEADING_RE = re.compile(
    r"^(?:"
    r"(?:SECTION|PART|CHAPTER|CLAUSE|ARTICLE|SCHEDULE|ITEM)\s+[0-9IVXLC]+[A-Z]?(?:\s*[:.\-–—]\s*.*)?|"
    r"\d+(?:\.\d+){0,2}\s*[:.\-–—)]?\s+[A-Z][^\n]{2,90}|"
    r"[A-Z][A-Z0-9\s,&/\-–—()]{4,80}"
    r")$"
)

# Regex for single-newline sub-clause or bullet lines inside PDF pages: e.g. "(a) ...", "(i) ...", "1.1 ...", "• ..."
SUBCLAUSE_START_RE = re.compile(
    r"^(?:"
    r"\([a-z]{1,3}\)\s+|"
    r"\([0-9]{1,2}\)\s+|"
    r"\([ivxlc]{1,5}\)\s+|"
    r"\d+\.\d+(?:\.\d+)?\s+|"
    r"[•●▪▸\-–]\s+"
    r")",
    re.IGNORECASE,
)

BOILERPLATE_RE = re.compile(
    r"^(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\s*/\s*\d+|-\s*\d+\s*-)$",
    re.IGNORECASE,
)

ACTIVE_PDF_TOKENS = (b"/JS", b"/JavaScript", b"/Launch", b"/RichMedia", b"/AA")

# Nigerian language lexical & orthographic markers (FR13 Stretch: Yoruba, Igbo, Hausa, Nigerian Pidgin)
NIGERIAN_LANGUAGE_MARKERS: Dict[str, Tuple[str, Set[str], Pattern[str]]] = {
    "yo": (
        "Yoruba",
        {
            "awon", "àwọn", "idibo", "ìdìbò", "kadi", "kádì", "orile", "orílẹ̀",
            "iforukosile", "ìforúkọsílẹ̀", "ojo", "ọjọ́", "gbogbo", "lati", "làti",
            "fun", "fún", "ni", "ní", "si", "sí", "ti", "tí", "ki", "kí", "omo", "ọmọ",
        },
        re.compile(r"[ẹọṣẸỌṢ]"),
    ),
    "ig": (
        "Igbo",
        {
            "ntuli", "ntụli", "aka", "ubochi", "ụbọchị", "ndi", "ndị", "nke",
            "maka", "akwukwo", "akwụkwọ", "kaadi", "kaadị", "ndebanye", "aha",
            "obodo", "onye", "kwesiri", "kwesịrị", "tupu", "ime",
        },
        re.compile(r"[ịụṅỊỤṄ]"),
    ),
    "ha": (
        "Hausa",
        {
            "zabe", "zaɓe", "kuri'a", "kuria", "rijista", "katin", "jama'a",
            "ranar", "dole", "cikin", "wanda", "kafin", "domin", "masu",
            "kowane", "shekara", "hukumar", "rumfar", "yankin",
        },
        re.compile(r"[ɓɗƙƁƊƘ]"),
    ),
    "pcm": (
        "Nigerian Pidgin",
        {
            "una", "wetin", "dey", "dem", "fit", "pipo", "pikin", "abi",
            "sef", "wahala", "sabi", "komot", " sharp", "biko",
        },
        re.compile(r"\b(?:make\s+una|no\s+be|go\s+fit|dem\s+go|for\s+inside)\b", re.IGNORECASE),
    ),
}


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def detect_nigerian_language(text: str) -> Tuple[str, str, float]:
    """
    Detect whether extracted text is written in Yoruba ('yo'), Igbo ('ig'),
    Hausa ('ha'), Nigerian Pidgin ('pcm'), or English ('en') (FR13 Stretch).
    Returns (lang_code, lang_name, confidence).
    """
    if not text or len(text.strip()) < 15:
        return ("en", "English", 1.0)

    words = re.findall(r"[a-zA-ZàáèéìíòóùúẹọṣịụṅɓɗƙÀÁÈÉÌÍÒÓÙÚẸỌṢỊỤṄƁƊƘ']+", text.lower())
    if not words:
        return ("en", "English", 1.0)

    best_lang = "en"
    best_name = "English"
    best_score = 0.0

    for code, (name, vocab, char_pat) in NIGERIAN_LANGUAGE_MARKERS.items():
        vocab_hits = sum(1 for w in words if w.strip("'") in vocab)
        char_hits = len(char_pat.findall(text))
        score = (vocab_hits + 0.75 * char_hits) / max(1, len(words))
        if (vocab_hits >= 2 or char_hits >= 2) and score > best_score and score >= 0.06:
            best_lang = code
            best_name = name
            best_score = min(0.99, round(score * 3.0, 2))

    if best_lang == "en":
        return ("en", "English", 0.95)
    return (best_lang, best_name, best_score)


def is_heading_block(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > 120 or "\n" in stripped:
        return False
    if stripped.endswith(".") and not re.match(r"^\d+\.\s+[A-Z][^.]+$", stripped):
        return False
    return bool(HEADING_RE.match(stripped))


def is_boilerplate_block(text: str) -> bool:
    stripped = text.strip()
    return bool(BOILERPLATE_RE.match(stripped))


def _sanitize_bmp(text: str) -> str:
    """Replace any non-BMP supplementary characters so JS UTF-16 and Python/Postgres offsets match."""
    out = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _split_page_into_blocks(page_text: str) -> List[str]:
    """
    Split a page's raw text into clean paragraph, heading, and sub-clause blocks.
    Preserves individual numbered/lettered sub-clauses (e.g. '(a)', '(b)', '(i)', '1.1', '•')
    even when separated by single newlines in PDF extraction.
    """
    normalized = page_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = re.split(r"\n\s*\n+", normalized)
    blocks: List[str] = []

    for b in raw_blocks:
        lines = [ln.strip() for ln in b.split("\n") if ln.strip()]
        if not lines:
            continue

        current_accum: List[str] = []
        for idx, line in enumerate(lines):
            if idx == 0 and len(lines) > 1 and is_heading_block(line):
                blocks.append(line)
                continue

            if current_accum and (is_heading_block(line) or SUBCLAUSE_START_RE.match(line)):
                joined = " ".join(current_accum).strip()
                if joined:
                    blocks.append(joined)
                current_accum = [line]
            else:
                current_accum.append(line)

        if current_accum:
            joined = " ".join(current_accum).strip()
            if joined:
                blocks.append(joined)

    return blocks


def _has_active_pdf_content(file_bytes: bytes) -> bool:
    """Detect embedded JavaScript or Launch actions in a PDF."""
    for token in ACTIVE_PDF_TOKENS:
        pattern = re.compile(re.escape(token) + rb"(?=[\s/<>(\[\]])")
        if pattern.search(file_bytes):
            return True
    return False


def _extract_raw_pages_from_pdf(
    file_bytes: bytes,
) -> Tuple[Optional[List[Tuple[str, str, Optional[str]]]], Optional[str], Optional[str]]:
    """
    Return (pages_list, error_status, error_message).
    Each entry in pages_list is (page_text, page_status, page_reason).
    """
    if _has_active_pdf_content(file_bytes):
        return (
            None,
            "rejected",
            "Document contains active scripts or embedded actions which are not permitted.",
        )

    if fitz is None:
        return (
            None,
            "failed",
            "PDF parser is unavailable on this worker.",
        )

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return (
            None,
            "rejected",
            "File could not be parsed as a valid PDF. Upload a valid text-based PDF or UTF-8 text file.",
        )

    try:
        if doc.is_encrypted or doc.needs_pass:
            return (
                None,
                "rejected",
                "Encrypted or password-protected PDFs are not supported. Upload an unencrypted text-based PDF.",
            )

        page_count = len(doc)
        if page_count == 0:
            return (
                None,
                "rejected",
                "Document has no pages.",
            )
        if page_count > MAX_PAGES:
            return (
                None,
                "rejected",
                f"Document has {page_count} pages, exceeding the {MAX_PAGES}-page limit.",
            )

        extracted_pages: List[Tuple[str, str, Optional[str]]] = []
        for idx in range(page_count):
            page = doc[idx]
            raw_text = _sanitize_bmp(page.get_text("text") or "").strip()
            if raw_text:
                extracted_pages.append((raw_text, "ok", None))
            else:
                images = page.get_images()
                drawings = page.get_drawings()
                if images or len(drawings) >= 1:
                    extracted_pages.append(
                        (
                            "",
                            "unreadable",
                            "Page contains no extractable text (likely scanned).",
                        )
                    )
                else:
                    extracted_pages.append(("", "blank", "Blank page"))

        return (extracted_pages, None, None)
    finally:
        doc.close()


def _extract_raw_pages_from_utf8(
    file_bytes: bytes,
) -> Tuple[Optional[List[Tuple[str, str, Optional[str]]]], Optional[str], Optional[str]]:
    """Extract pages from strict UTF-8 plain text (form-feed '\\f' separates pages)."""
    if b"\x00" in file_bytes:
        return (
            None,
            "rejected",
            "Only text-based PDF and UTF-8 text files are supported (binary bytes detected).",
        )
    try:
        text = file_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return (
            None,
            "rejected",
            "Only text-based PDF and UTF-8 text files are supported (invalid UTF-8 encoding).",
        )

    text = _sanitize_bmp(text)
    raw_pages = text.split("\f")
    if len(raw_pages) > MAX_PAGES:
        return (
            None,
            "rejected",
            f"Document has {len(raw_pages)} pages, exceeding the {MAX_PAGES}-page limit.",
        )

    extracted_pages: List[Tuple[str, str, Optional[str]]] = []
    for p_text in raw_pages:
        stripped = p_text.strip()
        if stripped == "[UNREADABLE_SCANNED_PAGE]" or stripped == "[demo scanned page: no extractable text]":
            extracted_pages.append(
                ("", "unreadable", "Page contains no extractable text (likely scanned).")
            )
        elif not stripped:
            extracted_pages.append(("", "blank", "Blank page"))
        else:
            extracted_pages.append((stripped, "ok", None))

    return (extracted_pages, None, None)


def ingest_document_bytes(
    *,
    version_id: str,
    workspace_id: str,
    file_bytes: bytes,
    expected_sha256: Optional[str] = None,
    max_file_bytes: int = MAX_FILE_BYTES,
) -> ExtractionResult:
    """
    Validate, extract page-aware text, detect Nigerian languages (FR13),
    and construct immutable spans satisfying INV2.
    """
    # 1. File size validation
    if len(file_bytes) > max_file_bytes:
        return ExtractionResult(
            version_id=version_id,
            workspace_id=workspace_id,
            extraction_status="rejected",
            extraction_message="This file is larger than 10 MB. Compress it or split it.",
            extractor_version=EXTRACTOR_VERSION,
            page_count=None,
            full_text=None,
        )

    if len(file_bytes) == 0:
        return ExtractionResult(
            version_id=version_id,
            workspace_id=workspace_id,
            extraction_status="rejected",
            extraction_message="Uploaded file is empty.",
            extractor_version=EXTRACTOR_VERSION,
            page_count=0,
            full_text=None,
        )

    # 2. SHA-256 integrity check (Section 5.1)
    actual_sha256 = compute_sha256(file_bytes)
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        return ExtractionResult(
            version_id=version_id,
            workspace_id=workspace_id,
            extraction_status="rejected",
            extraction_message="HASH_MISMATCH",
            extractor_version=EXTRACTOR_VERSION,
            page_count=None,
            full_text=None,
        )

    # 3. Format dispatch (PDF vs UTF-8 text)
    if file_bytes.startswith(b"%PDF-"):
        raw_pages, err_status, err_msg = _extract_raw_pages_from_pdf(file_bytes)
    else:
        raw_pages, err_status, err_msg = _extract_raw_pages_from_utf8(file_bytes)

    if err_status is not None or raw_pages is None:
        return ExtractionResult(
            version_id=version_id,
            workspace_id=workspace_id,
            extraction_status=err_status or "rejected",
            extraction_message=err_msg,
            extractor_version=EXTRACTOR_VERSION,
            page_count=None,
            full_text=None,
        )

    # 4. Build full_text, PageRecord list, and SpanRecord list satisfying INV2
    full_parts: List[str] = []
    current_len = 0
    seq = 0
    current_section: Optional[str] = None
    spans: List[SpanRecord] = []
    pages: List[PageRecord] = []
    unreadable_pages: List[int] = []
    blank_pages: List[int] = []
    ok_pages_count = 0

    for idx, (page_text, page_status, page_reason) in enumerate(raw_pages):
        page_num = idx + 1
        if idx > 0:
            sep = "\n\f\n"
            full_parts.append(sep)
            current_len += len(sep)

        page_start = current_len
        blocks = _split_page_into_blocks(page_text) if page_status == "ok" else []

        if page_status == "ok" and not blocks:
            page_status = "blank"
            page_reason = "Blank page"

        for b_idx, block_text in enumerate(blocks):
            if b_idx > 0:
                b_sep = "\n\n"
                full_parts.append(b_sep)
                current_len += len(b_sep)

            span_start = current_len
            full_parts.append(block_text)
            current_len += len(block_text)
            span_end = current_len

            heading_flag = is_heading_block(block_text)
            boilerplate_flag = is_boilerplate_block(block_text)
            if heading_flag and not boilerplate_flag:
                current_section = block_text

            span_id = str(
                uuid.uuid5(
                    uuid.UUID("7f9c2d10-8a4e-4b3b-9c2a-1e5d8f3a7b90"),
                    f"span:{version_id}:{seq}",
                )
            )
            spans.append(
                SpanRecord(
                    id=span_id,
                    workspace_id=workspace_id,
                    version_id=version_id,
                    seq=seq,
                    page=page_num,
                    section=current_section,
                    section_path=current_section,
                    start_offset=span_start,
                    end_offset=span_end,
                    raw_text=block_text,
                    is_heading=heading_flag,
                    is_boilerplate=boilerplate_flag,
                )
            )
            seq += 1

        page_end = current_len
        char_count = page_end - page_start

        if page_status == "unreadable":
            unreadable_pages.append(page_num)
        elif page_status == "blank":
            blank_pages.append(page_num)
        else:
            ok_pages_count += 1

        pages.append(
            PageRecord(
                version_id=version_id,
                page=page_num,
                status=page_status,
                reason=page_reason,
                char_count=char_count,
                start_offset=page_start,
                end_offset=page_end,
            )
        )

    full_text = "".join(full_parts)

    # 5. Determine overall extraction_status, warnings, and multilingual detection (FR13)
    warnings: List[Dict[str, Any]] = []
    if blank_pages:
        warnings.append(
            {
                "code": "BLANK_PAGES",
                "message": f"Blank pages detected: {', '.join(str(p) for p in blank_pages)}",
                "pages": blank_pages,
            }
        )

    lang_code, lang_name, lang_conf = detect_nigerian_language(full_text)
    if lang_code != "en":
        warnings.append(
            {
                "code": "MULTILINGUAL_MATERIAL_DETECTED",
                "language": lang_code,
                "language_name": lang_name,
                "confidence": lang_conf,
                "message": (
                    f"Detected {lang_name} ({lang_code}) content. "
                    "Changes in English official documents may affect this language version and require bilingual review."
                ),
            }
        )

    if unreadable_pages:
        extraction_status = "incomplete"
        if len(unreadable_pages) == 1:
            extraction_message = (
                f"Page {unreadable_pages[0]} contains no extractable text (likely scanned). "
                "Upload a text-based PDF."
            )
        else:
            pages_list = ", ".join(str(p) for p in unreadable_pages)
            extraction_message = (
                f"Pages {pages_list} contain no extractable text (likely scanned). "
                "Upload a text-based PDF."
            )
    elif ok_pages_count == 0 or len(spans) == 0:
        extraction_status = "incomplete"
        extraction_message = (
            "Document contains no extractable text. Upload a text-based PDF or UTF-8 text file."
        )
        for p in pages:
            p.status = "unreadable"
            p.reason = "No extractable text"
    else:
        extraction_status = "complete"
        extraction_message = None

    result = ExtractionResult(
        version_id=version_id,
        workspace_id=workspace_id,
        extraction_status=extraction_status,
        extraction_message=extraction_message,
        extractor_version=EXTRACTOR_VERSION,
        page_count=len(pages),
        full_text=full_text,
        pages=pages,
        spans=spans,
        warnings=warnings,
    )

    if not result.verify_inv2():
        raise RuntimeError("INV2 violation: span offsets do not match full_text slice")

    return result
