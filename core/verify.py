"""
Deterministic verification of extracted rows (no LLM here).

A row is rejected if:
- the quote is not found in the chunk text (normalized for whitespace,
  hyphenation like "lino- lenic", and case);
- the compound name is empty or a generic/non-specific term
  ("volatiles", "aldehydes" alone, etc.);
- the lever or food is out of scope per the blocklist (insect, animal-origin
  ingredient, animal feed).

Optionally resolves the compound to a PubChem CID (cached, throttled). If
unavailable, pubchem_cid = None and resolved = False instead of failing.

Rejected rows are logged to data/rejected.csv with the reason.
"""

import csv
import os
import re
import time

import requests

from core import config

GENERIC_COMPOUND_TERMS = {
    "volatiles", "volatile compounds", "aldehydes", "ketones", "alcohols",
    "esters", "furans", "compounds", "aroma compounds", "flavor compounds",
    "off-flavors", "off-flavours", "vocs", "odorants", "unknown",
}

MAX_QUOTE_WORDS = 25

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"
PUBCHEM_THROTTLE_SECONDS = 0.3

_last_pubchem_call = 0.0


def _normalize_text(text):
    """Lowercase, collapse whitespace, and join hyphenated line-break words like 'lino- lenic' -> 'linolenic'."""
    if not text:
        return ""
    text = text.lower()
    # join hyphen followed by whitespace then a letter (line-wrap hyphenation)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _quote_found_in_chunk(quote, chunk_text):
    norm_quote = _normalize_text(quote)
    norm_chunk = _normalize_text(chunk_text)
    if not norm_quote:
        return False
    return norm_quote in norm_chunk


def _quote_within_word_limit(quote):
    if not quote:
        return False
    return len(quote.split()) <= MAX_QUOTE_WORDS


def _compound_is_valid(compound):
    if not compound or not compound.strip():
        return False
    norm = _normalize_text(compound)
    # strip angle-bracket / placeholder wrappers like "<UNKNOWN>" before comparing
    stripped = norm.strip("<>").strip()
    if stripped in GENERIC_COMPOUND_TERMS:
        return False
    return norm not in GENERIC_COMPOUND_TERMS


def _contains_blocklisted_keyword(text):
    """Word-boundary match against the blocklist (avoids false hits like 'lard' inside 'Maillard')."""
    if not text:
        return None
    norm = _normalize_text(text)
    for kw in config.BLOCKLIST_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, norm):
            return kw
    return None


def _out_of_scope_reason(row):
    for field in ("food", "lever", "compound"):
        hit = _contains_blocklisted_keyword(row.get(field, ""))
        if hit:
            return f"out_of_scope: '{hit}' found in field '{field}'"
    return None


def pubchem_lookup(compound_name):
    """
    Resolve a compound name to a PubChem CID via PUG REST. Cached on disk,
    throttled to 0.3s between calls. Returns (cid_or_None, resolved_bool).
    If the VM has no internet or the lookup fails, returns (None, False).
    """
    global _last_pubchem_call

    cache_dir = os.path.join(config.CACHE_DIR, "pubchem")
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", compound_name.strip().lower())
    cache_path = os.path.join(cache_dir, f"{safe_name}.txt")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            content = f.read().strip()
        if content == "NONE":
            return None, False
        try:
            return int(content), True
        except ValueError:
            return None, False

    elapsed = time.time() - _last_pubchem_call
    if elapsed < PUBCHEM_THROTTLE_SECONDS:
        time.sleep(PUBCHEM_THROTTLE_SECONDS - elapsed)
    _last_pubchem_call = time.time()

    try:
        url = PUBCHEM_URL.format(name=requests.utils.quote(compound_name))
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            with open(cache_path, "w") as f:
                f.write("NONE")
            return None, False
        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        if cids:
            cid = cids[0]
            with open(cache_path, "w") as f:
                f.write(str(cid))
            return cid, True
        with open(cache_path, "w") as f:
            f.write("NONE")
        return None, False
    except Exception:
        # No internet or any other failure: do not raise, mark unresolved.
        return None, False


def verify_rows(rows, chunk_lookup, resolve_pubchem=True):
    """
    rows: list of raw extracted row dicts (must include chunk_id, compound,
          quote, food, lever, confidence, etc.)
    chunk_lookup: dict chunk_id -> chunk dict (with "text")

    Returns (accepted_rows, rejected_rows). Each rejected row dict has a
    "reason" key appended.
    """
    accepted = []
    rejected = []

    for row in rows:
        chunk_id = row.get("chunk_id")
        chunk = chunk_lookup.get(chunk_id)
        quote = row.get("quote", "")
        compound = row.get("compound", "")

        if chunk is None:
            rejected.append({**row, "reason": f"unknown chunk_id: {chunk_id}"})
            continue

        if not _compound_is_valid(compound):
            rejected.append({**row, "reason": "compound empty or generic"})
            continue

        if not _quote_within_word_limit(quote):
            rejected.append({**row, "reason": "quote exceeds 25 words"})
            continue

        if not _quote_found_in_chunk(quote, chunk["text"]):
            rejected.append({**row, "reason": "quote not found verbatim in chunk text"})
            continue

        scope_reason = _out_of_scope_reason(row)
        if scope_reason:
            rejected.append({**row, "reason": scope_reason})
            continue

        role = row.get("role")
        if role not in {"meat_marker", "off_note", "precursor", "masker", "removal"}:
            rejected.append({**row, "reason": f"invalid role: {role}"})
            continue

        verified_row = dict(row)
        if resolve_pubchem:
            cid, resolved = pubchem_lookup(compound)
            verified_row["pubchem_cid"] = cid
            verified_row["resolved"] = resolved
        else:
            verified_row["pubchem_cid"] = None
            verified_row["resolved"] = False

        accepted.append(verified_row)

    return accepted, rejected


def log_rejected(rejected_rows, path=None):
    """Append rejected rows (with reason) to data/rejected.csv."""
    path = path or config.REJECTED_CSV
    os.makedirs(os.path.dirname(path), exist_ok=True)

    fieldnames = [
        "food", "preparation", "compound", "descriptor", "role", "lever",
        "concentration", "threshold", "quote", "chunk_id", "file", "page",
        "confidence", "reason",
    ]

    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in rejected_rows:
            writer.writerow(row)
