"""Export the 10-pair / 30-material Nigerian Electoral Benchmark as real on-disk PDFs, UTF-8 text files, and double-blind labeling worksheets for AY and Taiwo (PRD Section 9)."""

from __future__ import annotations
import csv
import json
import os
from typing import Any, Dict, List

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

from worker.extractor import compute_sha256
from worker.fixtures.nigerian_benchmark import get_benchmark_dataset


def render_pages_to_pdf(pages: List[str], out_path: str, title: str = "") -> str:
    """Create a real multi-page text-based PDF file on disk using PyMuPDF and return its SHA-256."""
    doc = fitz.open()
    for p_idx, page_text in enumerate(pages, start=1):
        page = doc.new_page(width=595, height=842)  # A4
        y = 54
        if title:
            page.insert_text((54, y), f"{title} (Page {p_idx})", fontsize=9)
            y += 24
        for block in page_text.split("\n\n"):
            lines = block.strip().split("\n")
            for ln in lines:
                # Wrap long lines to ~85 characters for clean A4 layout
                words = ln.split()
                cur = []
                cur_len = 0
                for w in words:
                    if cur_len + len(w) + 1 > 82 and cur:
                        page.insert_text((54, y), " ".join(cur), fontsize=11)
                        y += 16
                        cur = [w]
                        cur_len = len(w)
                    else:
                        cur.append(w)
                        cur_len += len(w) + 1
                if cur:
                    page.insert_text((54, y), " ".join(cur), fontsize=11)
                    y += 16
            y += 10
    pdf_bytes = doc.tobytes()
    doc.close()
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    return compute_sha256(pdf_bytes)


def render_scanned_unreadable_pdf(out_path: str) -> str:
    """Create a simulated scanned PDF with vector graphics and zero extractable text for AC03 testing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    shape = page.new_shape()
    for i in range(12):
        shape.draw_rect(fitz.Rect(54, 70 + i * 28, 520, 86 + i * 28))
    shape.finish(color=(0.2, 0.2, 0.2), fill=(0.85, 0.85, 0.85))
    shape.commit()
    pdf_bytes = doc.tobytes()
    doc.close()
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    return compute_sha256(pdf_bytes)


def export_all_benchmark_files(base_dir: Optional[str] = None) -> Dict[str, Any]:
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), "fixtures", "generated_files")

    sources_dir = os.path.join(base_dir, "sources")
    materials_dir = os.path.join(base_dir, "materials")
    edge_cases_dir = os.path.join(base_dir, "edge_cases")
    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(materials_dir, exist_ok=True)
    os.makedirs(edge_cases_dir, exist_ok=True)

    pairs, materials = get_benchmark_dataset()
    manifest: Dict[str, Any] = {
        "benchmark_version": "1.0.0",
        "source_pairs": [],
        "materials": [],
        "edge_cases": [],
    }

    blind_worksheet_rows: List[Dict[str, Any]] = []
    ground_truth_records: List[Dict[str, Any]] = []

    for pair in pairs:
        v1_pdf = os.path.join(sources_dir, f"{pair.pair_id}_v1.pdf")
        v2_pdf = os.path.join(sources_dir, f"{pair.pair_id}_v2.pdf")
        v1_txt = os.path.join(sources_dir, f"{pair.pair_id}_v1.txt")
        v2_txt = os.path.join(sources_dir, f"{pair.pair_id}_v2.txt")

        v1_sha_pdf = render_pages_to_pdf(pair.v1_pages, v1_pdf, title=f"{pair.title} - v1")
        v2_sha_pdf = render_pages_to_pdf(pair.v2_pages, v2_pdf, title=f"{pair.title} - v2")

        with open(v1_txt, "w", encoding="utf-8") as f:
            f.write("\f".join(pair.v1_pages))
        with open(v2_txt, "w", encoding="utf-8") as f:
            f.write("\f".join(pair.v2_pages))

        manifest["source_pairs"].append(
            {
                "pair_id": pair.pair_id,
                "title": pair.title,
                "issuer": pair.issuer,
                "jurisdiction": pair.jurisdiction,
                "election_context": pair.election_context,
                "split": pair.split,
                "v1_pdf": f"sources/{pair.pair_id}_v1.pdf",
                "v1_pdf_sha256": v1_sha_pdf,
                "v2_pdf": f"sources/{pair.pair_id}_v2.pdf",
                "v2_pdf_sha256": v2_sha_pdf,
                "v1_txt": f"sources/{pair.pair_id}_v1.txt",
                "v2_txt": f"sources/{pair.pair_id}_v2.txt",
            }
        )

        # Build blind labeling worksheet entries for AY & Taiwo (no system answers shown!)
        blind_worksheet_rows.append(
            {
                "pair_id": pair.pair_id,
                "document_title": pair.title,
                "split": pair.split,
                "v1_text": "\n---\n".join(pair.v1_pages),
                "v2_text": "\n---\n".join(pair.v2_pages),
                "annotator_id": "",  # 'AY' or 'Taiwo'
                "labelled_changes_count": "",
                "labelled_change_categories": "",
                "affected_material_ids": "",
                "annotator_notes": "",
            }
        )

        ground_truth_records.append(
            {
                "pair_id": pair.pair_id,
                "title": pair.title,
                "split": pair.split,
                "expected_changes": [
                    {
                        "expected_type": ec.expected_type,
                        "old_substring": ec.old_substring,
                        "new_substring": ec.new_substring,
                        "expected_category": ec.expected_category,
                        "is_critical_date_or_eligibility": ec.is_critical_date_or_eligibility,
                        "affected_material_ids": ec.affected_material_ids,
                    }
                    for ec in pair.expected_changes
                ],
            }
        )

    for mat in materials:
        m_pdf = os.path.join(materials_dir, f"{mat.material_id}.pdf")
        m_txt = os.path.join(materials_dir, f"{mat.material_id}.txt")
        m_sha = render_pages_to_pdf(mat.pages, m_pdf, title=mat.title)
        with open(m_txt, "w", encoding="utf-8") as f:
            f.write("\f".join(mat.pages))

        manifest["materials"].append(
            {
                "material_id": mat.material_id,
                "title": mat.title,
                "owner": mat.owner,
                "language": mat.language,
                "pdf": f"materials/{mat.material_id}.pdf",
                "pdf_sha256": m_sha,
                "txt": f"materials/{mat.material_id}.txt",
            }
        )

    # Edge-case fixture: scanned unreadable PDF for AC03
    scanned_path = os.path.join(edge_cases_dir, "scanned_unreadable_poster.pdf")
    scanned_sha = render_scanned_unreadable_pdf(scanned_path)
    manifest["edge_cases"].append(
        {
            "id": "EDGE-SCANNED-01",
            "description": "Scanned poster PDF with vector graphics and zero extractable text (tests AC03 incomplete blocking)",
            "pdf": "edge_cases/scanned_unreadable_poster.pdf",
            "pdf_sha256": scanned_sha,
        }
    )

    with open(os.path.join(base_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with open(os.path.join(base_dir, "blind_labeling_worksheet.json"), "w", encoding="utf-8") as f:
        json.dump(blind_worksheet_rows, f, indent=2)

    csv_path = os.path.join(base_dir, "blind_labeling_worksheet.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pair_id",
                "document_title",
                "split",
                "v1_text",
                "v2_text",
                "annotator_id",
                "labelled_changes_count",
                "labelled_change_categories",
                "affected_material_ids",
                "annotator_notes",
            ],
        )
        writer.writeheader()
        writer.writerows(blind_worksheet_rows)

    with open(os.path.join(base_dir, "ground_truth_reference.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth_records, f, indent=2)

    return {
        "output_dir": base_dir,
        "source_pdfs_generated": len(pairs) * 2,
        "material_pdfs_generated": len(materials),
        "edge_case_pdfs_generated": 1,
    }


if __name__ == "__main__":
    summary = export_all_benchmark_files()
    print(json.dumps(summary, indent=2))
