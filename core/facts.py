"""
core/facts.py

Append verified fact rows (from extract.py + verify.py) to data/facts.csv,
the single growing table that gap.py and rank.py read from. Every row here
has origin = "model-extracted" (Haiku read it from a paper chunk, and
verify.py confirmed the quote exists verbatim in that chunk).

Rows are deduplicated on (file, page, compound, descriptor, role, quote) so
re-running the pipeline on overlapping chunks does not create duplicate facts.
"""

import csv
import os

from core import config

FIELDNAMES = [
    "food", "preparation", "compound", "descriptor", "role", "lever",
    "concentration", "threshold", "quote", "chunk_id", "file", "page",
    "confidence", "pubchem_cid", "resolved", "origin",
]


def _normalize_page(page):
    """Normalize a page value to a consistent type for dedup comparison (CSV round-trips give strings, fresh rows may give floats)."""
    if page is None or page == "":
        return None
    try:
        return float(page)
    except (TypeError, ValueError):
        return str(page)


def _dedup_key(row):
    return (
        row.get("file"),
        _normalize_page(row.get("page")),
        (row.get("compound") or "").strip().lower(),
        (row.get("descriptor") or "").strip().lower(),
        row.get("role"),
        (row.get("quote") or "").strip().lower(),
    )


def _read_existing(path):
    if not os.path.exists(path):
        return [], set()
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    keys = {_dedup_key(r) for r in rows}
    return rows, keys


def append_facts(accepted_rows, path=None):
    """
    Append accepted rows to data/facts.csv, skipping any row whose dedup key
    already exists in the file. Returns the number of rows actually appended.
    """
    path = path or config.FACTS_CSV
    os.makedirs(os.path.dirname(path), exist_ok=True)

    _, existing_keys = _read_existing(path)

    new_rows = []
    for row in accepted_rows:
        row = dict(row)
        row["origin"] = config.ORIGIN_MODEL_EXTRACTED
        key = _dedup_key(row)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        new_rows.append(row)

    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)

    return len(new_rows)


def load_facts(path=None):
    """Load all facts from data/facts.csv as a list of dicts. Returns [] if the file doesn't exist."""
    path = path or config.FACTS_CSV
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)
