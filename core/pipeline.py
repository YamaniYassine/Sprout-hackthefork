"""
core/pipeline.py

Top-level orchestration: given a scenario (protein, meat_target, cooking),
either load a precomputed result from data/scenarios/<id>.json (fast demo,
no Bedrock calls) or run the full live pipeline:

    retrieve -> extract -> verify -> facts (append) -> gap -> rank -> explain

Returns a single dict the UI can render directly.
"""

import csv
import json
import os

from core import bedrock, config, extract, explain, facts as facts_module, gap, rank, retrieve, verify


def scenario_id(protein, meat_target, cooking):
    """Build the data/scenarios/<id>.json file name for a scenario."""
    safe_meat = meat_target.replace(" ", "_")
    return f"{protein}__{safe_meat}__{cooking}"


def scenario_path(protein, meat_target, cooking):
    return os.path.join(config.SCENARIOS_DIR, f"{scenario_id(protein, meat_target, cooking)}.json")


def load_papers_by_title():
    if not os.path.exists(config.PAPERS_CSV):
        return {}
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        return {row["_document_title"]: row for row in reader}


def _serialize_result(protein, meat_target, cooking, result, ranked, unmapped, explanation, rejection_stats):
    """Build the JSON-serializable dict saved to data/scenarios/<id>.json and returned to the UI."""
    return {
        "scenario": {"protein": protein, "meat_target": meat_target, "cooking": cooking},
        "missing_notes": result["missing_notes"],
        "off_notes": result["off_notes"],
        "ranked_levers": ranked,
        "unmapped_levers": unmapped,
        "explanation": explanation,
        "rejection_stats": rejection_stats,
    }


def run_live(protein, meat_target, cooking, min_grade=None, exclude_e_numbers=False, top_n_chunks=None):
    """
    Run the full live pipeline for a scenario: retrieve -> extract -> verify ->
    append to facts.csv -> gap -> rank -> explain.

    top_n_chunks: optionally cap how many retrieved chunks go through extraction
        (keeps demo runs fast/cheap; None = use all deduplicated chunks).

    Returns the same shaped dict as run_from_cache_or_live().
    """
    chunks = retrieve.retrieve_for_scenario(protein, meat_target, cooking)
    if top_n_chunks is not None:
        chunks = chunks[:top_n_chunks]

    raw_rows = extract.extract_rows(chunks)
    chunk_lookup = {c["chunk_id"]: c for c in chunks}
    accepted, rejected = verify.verify_rows(raw_rows, chunk_lookup, resolve_pubchem=True)

    verify.log_rejected(rejected)
    facts_module.append_facts(accepted)

    rejection_stats = {
        "raw_rows": len(raw_rows),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "rejection_rate": round(len(rejected) / len(raw_rows), 3) if raw_rows else 0.0,
    }

    all_facts = facts_module.load_facts()
    papers_by_title = load_papers_by_title()

    gap_result = gap.analyze_gap(
        protein, meat_target, cooking,
        facts_rows=all_facts, min_grade=min_grade, papers_by_title=papers_by_title,
    )
    ranked, unmapped = rank.rank_levers(
        all_facts, gap_result["missing_notes"], gap_result["off_notes"],
        papers_by_title=papers_by_title, exclude_e_numbers=exclude_e_numbers,
    )
    explanation = explain.generate_explanation(
        protein, meat_target, cooking, gap_result["missing_notes"], gap_result["off_notes"], ranked,
    )

    return _serialize_result(protein, meat_target, cooking, gap_result, ranked, unmapped, explanation, rejection_stats)


def run(protein, meat_target, cooking, min_grade=None, exclude_e_numbers=False, force_live=False, top_n_chunks=None):
    """
    Main entry point used by the UI.

    - If a precomputed scenario file exists in data/scenarios/ and force_live
      is False, load and return it instantly (no Bedrock calls).
    - Otherwise run the live pipeline.

    Note: min_grade / exclude_e_numbers are UI-side filters applied via
    run_live or applied to a precomputed result's ranked list on read; the
    precomputed JSON stores the unfiltered gap/rank output computed at
    build_scenarios.py time with default toggles, so toggling filters in the
    UI after loading a precomputed scenario will only be exact if the demo
    scenario was built with those same toggles. For a demo, force_live=True
    (via the "Run live" button) always reflects current toggles exactly.
    """
    path = scenario_path(protein, meat_target, cooking)

    if not force_live and os.path.exists(path):
        with open(path, "r") as f:
            result = json.load(f)
        result["loaded_from_cache_file"] = True
        return result

    result = run_live(
        protein, meat_target, cooking,
        min_grade=min_grade, exclude_e_numbers=exclude_e_numbers, top_n_chunks=top_n_chunks,
    )
    result["loaded_from_cache_file"] = False
    return result
