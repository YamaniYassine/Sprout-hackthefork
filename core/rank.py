"""
core/rank.py - deterministic lever ranking (NO LLM).

Maps free-text "lever" values from verified facts to data/lever_catalog.csv
entries by keyword, then scores each mapped lever:

    evidence = sum over distinct supporting papers (grade_weight x mean confidence)
        grade_weight = grade / GRADE_WEIGHT_DIVISOR, or DEFAULT_GRADE_WEIGHT if ungraded

    score = evidence * (1 + GAP_COVERAGE_WEIGHT * n_targeted_gaps)
            - COST_PENALTY_WEIGHT * cost_penalty
            - CLEAN_LABEL_PENALTY_WEIGHT * clean_label_penalty

cost_penalty: low=0, medium=0.5, high=1 (config.COST_TIER_PENALTY)
clean_label_penalty: 0, 0.5, 1 (config.CLEAN_LABEL_PENALTY)

Levers mentioned in facts but not matched to any catalog entry are reported
separately as "unmapped" and excluded from the ranked table.
"""

import csv
import os
from collections import defaultdict

from core import config

# Keyword lists used to map free-text lever mentions to catalog entries.
# Keys must match the "lever" column in data/lever_catalog.csv exactly.
LEVER_KEYWORD_MAP = {
    "yeast extract": ["yeast extract"],
    "xylose + cysteine Maillard reaction": [
        "xylose", "cysteine", "maillard", "d-lc", "d-lm", "methionine",
    ],
    "lactic acid bacteria fermentation": [
        "lactic acid bacteria", "l. plantarum", "lactobacillus", "fermentation", "fermented",
    ],
    "beta-cyclodextrin": ["cyclodextrin", "cgt", "cgtase"],
    "steam stripping / deodorization": ["steam stripping", "deodorization", "deodorisation"],
    "supercritical CO2 extraction": ["supercritical co2", "supercritical carbon dioxide", "scco2"],
    "ethanol washing": ["ethanol wash", "ethanol extraction"],
    "lipoxygenase-null soy varieties": ["lipoxygenase-null", "lox-null", "lipoxygenase null"],
    "mushroom extract": ["mushroom extract", "mushroom"],
    "onion/garlic powder": ["onion", "garlic"],
    "smoked paprika": ["smoked paprika", "paprika", "smoke"],
    "plant oils (sunflower/coconut)": ["sunflower oil", "coconut oil", "plant oil", "oleogel"],
}


def load_lever_catalog(path=None):
    """Returns dict lever_name -> catalog row dict."""
    path = path or config.LEVER_CATALOG_CSV
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return {row["lever"]: row for row in rows}


def match_lever_to_catalog(lever_text):
    """
    Map a free-text lever mention (from facts.csv) to a catalog lever name by
    keyword. Returns the catalog lever name, or None if unmapped.
    """
    if not lever_text or not lever_text.strip():
        return None
    text_lower = lever_text.lower()
    for catalog_name, keywords in LEVER_KEYWORD_MAP.items():
        if any(kw in text_lower for kw in keywords):
            return catalog_name
    return None


def _grade_weight(file_name, papers_by_title):
    if papers_by_title is None:
        return config.DEFAULT_GRADE_WEIGHT
    paper = papers_by_title.get(file_name)
    if paper is None or paper.get("grade") in (None, ""):
        return config.DEFAULT_GRADE_WEIGHT
    try:
        grade = float(paper["grade"])
    except (TypeError, ValueError):
        return config.DEFAULT_GRADE_WEIGHT
    return grade / config.GRADE_WEIGHT_DIVISOR


def _rows_targeting_gap_descriptor(rows, gap_descriptors):
    """Return the subset of gap_descriptors that at least one of these rows' descriptor matches."""
    row_descriptors = {(r.get("descriptor") or "").strip().lower() for r in rows}
    return row_descriptors & gap_descriptors


def rank_levers(facts_rows, missing_notes, off_notes, papers_by_title=None,
                 exclude_e_numbers=False, lever_catalog=None):
    """
    facts_rows: verified fact rows (role in {precursor, masker, removal} typically
                carry a lever, but any row with a non-empty "lever" field is considered).
    missing_notes: output of gap.compute_missing_notes (list of {"descriptor": ...})
    off_notes: output of gap.compute_off_notes (list of {"descriptor": ...})
    exclude_e_numbers: if True, drop catalog levers with clean_label == 2.

    Returns (ranked, unmapped):
        ranked: list of dicts, sorted by score desc, each with:
            lever, type, plant_only, cost_tier, clean_label, score, evidence,
            n_papers, n_targeted_gaps, mean_confidence, matched_facts, origin
        unmapped: list of distinct free-text lever strings with no catalog match
    """
    catalog = lever_catalog or load_lever_catalog()

    gap_descriptors = {m["descriptor"] for m in missing_notes} | {o["descriptor"] for o in off_notes}

    # Group facts rows by matched catalog lever name.
    rows_by_catalog_lever = defaultdict(list)
    unmapped_set = set()

    for row in facts_rows:
        lever_text = row.get("lever", "")
        if not lever_text or not lever_text.strip():
            continue
        catalog_name = match_lever_to_catalog(lever_text)
        if catalog_name is None:
            unmapped_set.add(lever_text.strip())
            continue
        rows_by_catalog_lever[catalog_name].append(row)

    ranked = []
    for catalog_name, rows in rows_by_catalog_lever.items():
        catalog_entry = catalog.get(catalog_name)
        if catalog_entry is None:
            # lever is in the keyword map but someone edited the catalog csv
            # and removed the row: treat as unmapped rather than crash.
            for row in rows:
                unmapped_set.add(row.get("lever", "").strip())
            continue

        clean_label = int(catalog_entry["clean_label"])
        if exclude_e_numbers and clean_label == 2:
            continue

        # evidence = sum over distinct supporting papers (grade_weight * mean confidence of that paper's rows)
        rows_by_paper = defaultdict(list)
        for row in rows:
            rows_by_paper[row.get("file")].append(row)

        evidence = 0.0
        for file_name, paper_rows in rows_by_paper.items():
            confidences = [float(r.get("confidence", 0) or 0) for r in paper_rows]
            mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            grade_weight = _grade_weight(file_name, papers_by_title)
            evidence += grade_weight * mean_confidence

        n_papers = len(rows_by_paper)
        targeted = _rows_targeting_gap_descriptor(rows, gap_descriptors)
        n_targeted_gaps = len(targeted)

        cost_tier = catalog_entry["cost_tier"]
        cost_penalty = config.COST_TIER_PENALTY.get(cost_tier, 0.0)
        clean_label_penalty = config.CLEAN_LABEL_PENALTY.get(clean_label, 0.0)

        score = (
            evidence * (1 + config.GAP_COVERAGE_WEIGHT * n_targeted_gaps)
            - config.COST_PENALTY_WEIGHT * cost_penalty
            - config.CLEAN_LABEL_PENALTY_WEIGHT * clean_label_penalty
        )

        all_confidences = [float(r.get("confidence", 0) or 0) for r in rows]
        mean_confidence_overall = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        ranked.append({
            "lever": catalog_name,
            "type": catalog_entry["type"],
            "plant_only": catalog_entry["plant_only"] == "True",
            "cost_tier": cost_tier,
            "clean_label": clean_label,
            "score": round(score, 3),
            "evidence": round(evidence, 3),
            "n_papers": n_papers,
            "n_targeted_gaps": n_targeted_gaps,
            "targeted_gap_descriptors": sorted(targeted),
            "mean_confidence": round(mean_confidence_overall, 3),
            "matched_facts": rows,
            "notes": catalog_entry.get("notes", ""),
            "origin_catalog_fields": config.ORIGIN_ASSUMED,  # cost_tier/clean_label are assumed
        })

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked, sorted(unmapped_set)
