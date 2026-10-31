"""
scripts/catalog.py

Downloads the PDFs from the knowledge base's S3 data source (foodie-kb),
extracts per-page text with pypdf into data/text/<pdf_name>/page_<n>.txt,
and builds data/papers.csv with one row per paper:

    _document_title, s3_key, num_pages, size_bytes, text_extracted,
    grade, grade_reason, protein_tags, meat_tags

_document_title matches the metadata key used by the Bedrock KB retrieve
results, so papers.csv can be joined on it. grade/grade_reason are left
empty here; scripts/grade.py fills them in.

PDFs are never committed to git (see .gitignore); this script re-downloads
them on demand into data/pdfs/.
"""

import csv
import logging
import os
import sys

import boto3
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config

# pypdf logs a "fontTools is required..." warning per malformed font per page on
# some PDFs. It is harmless (text extraction still works); silence it so the
# catalog/coverage output stays readable.
logging.getLogger("pypdf").setLevel(logging.ERROR)

PROTEIN_KEYWORDS = {
    "pea": ["pea protein", "pisum sativum", " pea "],
    "soy": ["soy protein", "soybean", "glycine max", " soy "],
    "faba": ["faba bean", "fava bean", "vicia faba"],
}

MEAT_KEYWORDS = {
    "beef": ["beef", "bovine"],
    "chicken": ["chicken", "poultry"],
}

# Looser, generic "mentions meat flavor at all" tag (not beef/chicken-specific),
# used only to report corpus coverage honestly, not for filtering.
GENERIC_MEAT_KEYWORDS = ["meat", "meaty", "cooked meat", "meat analog", "meat analogue"]


def download_pdfs():
    """Download every object in the foodie-kb bucket to data/pdfs/. Returns list of (s3_key, local_path)."""
    os.makedirs(config.PDFS_DIR, exist_ok=True)
    s3 = boto3.client("s3", region_name=config.AWS_REGION)

    paginator = s3.get_paginator("list_objects_v2")
    downloaded = []
    for page in paginator.paginate(Bucket=config.KB_S3_BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue
            local_path = os.path.join(config.PDFS_DIR, os.path.basename(key))
            if not os.path.exists(local_path):
                s3.download_file(config.KB_S3_BUCKET, key, local_path)
            downloaded.append((key, local_path, obj["Size"]))
    return downloaded


def extract_text(local_path, document_title):
    """
    Extract per-page text from a PDF into data/text/<document_title>/page_<n>.txt.
    Returns (num_pages, text_extracted_bool).
    """
    out_dir = os.path.join(config.TEXT_DIR, document_title)
    os.makedirs(out_dir, exist_ok=True)

    try:
        reader = PdfReader(local_path)
    except Exception as e:
        print(f"  WARNING: could not open {document_title}: {e}")
        return 0, False

    num_pages = len(reader.pages)
    any_text = False
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            any_text = True
        page_path = os.path.join(out_dir, f"page_{i + 1}.txt")
        with open(page_path, "w") as f:
            f.write(text)

    return num_pages, any_text


def guess_tags(document_title, keywords_by_tag):
    """Scan the first 2 pages of extracted text for keyword hits, return a comma-joined tag string."""
    out_dir = os.path.join(config.TEXT_DIR, document_title)
    text = ""
    for i in (1, 2):
        page_path = os.path.join(out_dir, f"page_{i}.txt")
        if os.path.exists(page_path):
            with open(page_path, "r") as f:
                text += f.read().lower()

    hits = []
    for tag, keywords in keywords_by_tag.items():
        if any(kw.lower() in text for kw in keywords):
            hits.append(tag)
    return ",".join(hits)


def _mentions_generic_meat(document_title):
    out_dir = os.path.join(config.TEXT_DIR, document_title)
    text = ""
    for i in (1, 2):
        page_path = os.path.join(out_dir, f"page_{i}.txt")
        if os.path.exists(page_path):
            with open(page_path, "r") as f:
                text += f.read().lower()
    return any(kw in text for kw in GENERIC_MEAT_KEYWORDS)


def build_papers_csv(entries):
    """entries: list of (s3_key, local_path, size_bytes, document_title, num_pages, text_extracted)."""
    os.makedirs(config.DATA_DIR, exist_ok=True)

    fieldnames = [
        "_document_title", "s3_key", "num_pages", "size_bytes",
        "text_extracted", "protein_tags", "meat_tags", "mentions_meat_generic",
        "grade", "grade_reason",
    ]

    rows = []
    for s3_key, local_path, size_bytes, document_title, num_pages, text_extracted in entries:
        protein_tags = guess_tags(document_title, PROTEIN_KEYWORDS)
        meat_tags = guess_tags(document_title, MEAT_KEYWORDS)
        rows.append({
            "_document_title": document_title,
            "s3_key": s3_key,
            "num_pages": num_pages,
            "size_bytes": size_bytes,
            "text_extracted": text_extracted,
            "protein_tags": protein_tags,
            "meat_tags": meat_tags,
            "mentions_meat_generic": _mentions_generic_meat(document_title),
            "grade": "",
            "grade_reason": "",
        })

    rows.sort(key=lambda r: r["_document_title"])

    with open(config.PAPERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def print_coverage_table(rows):
    """Print a protein x meat coverage table: how many papers mention each combination."""
    proteins = list(PROTEIN_KEYWORDS.keys())
    meats = list(MEAT_KEYWORDS.keys())

    print()
    print("Protein x meat coverage (number of papers mentioning both tags):")
    header = "protein".ljust(10) + "".join(m.ljust(10) for m in meats)
    print(header)
    for p in proteins:
        counts = []
        for m in meats:
            count = sum(
                1 for r in rows
                if p in r["protein_tags"].split(",") and m in r["meat_tags"].split(",")
            )
            counts.append(count)
        print(p.ljust(10) + "".join(str(c).ljust(10) for c in counts))

    print()
    print("Papers with no protein tag detected:", sum(1 for r in rows if not r["protein_tags"]))
    print("Papers with no specific meat (beef/chicken) tag detected:", sum(1 for r in rows if not r["meat_tags"]))
    print("...of those, papers that at least mention meat/meaty generically:",
          sum(1 for r in rows if not r["meat_tags"] and r["mentions_meat_generic"]))


def main():
    print("Downloading PDFs from s3://%s ..." % config.KB_S3_BUCKET)
    downloaded = download_pdfs()
    print(f"Downloaded/verified {len(downloaded)} PDFs.")

    entries = []
    for s3_key, local_path, size_bytes in downloaded:
        document_title = os.path.basename(local_path)
        print(f"Extracting text: {document_title}")
        num_pages, text_extracted = extract_text(local_path, document_title)
        entries.append((s3_key, local_path, size_bytes, document_title, num_pages, text_extracted))

    rows = build_papers_csv(entries)
    print(f"\nWrote {config.PAPERS_CSV} with {len(rows)} rows.")
    print_coverage_table(rows)


if __name__ == "__main__":
    main()
