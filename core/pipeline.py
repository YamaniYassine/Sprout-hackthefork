"""
core/pipeline.py

Top-level orchestration: given a scenario (protein, meat_target), either
load a precomputed result from data/scenarios/<id>.json (fast demo, no
Bedrock calls) or run the full live pipeline:

    retrieve -> extract -> verify -> facts (append) -> gap -> rank -> explain

v2: no cooking-state input. The analysis pools cooked-meat evidence across
all cooking methods found in the corpus (see core/retrieve.py).

Returns a single dict the UI can render directly.
"""

import csv
import json
import os

from core import bedrock, config, extract, explain, facts as facts_module, gap, rank, retrieve, verify


def scenario_id(protein, meat_target):
    """Build the data/scenarios/<id>.json file name for a scenario."""
    safe_meat = meat_target.replace(" ", "_")
    return f"{protein}__{safe_meat}"


def scenario_path(protein, meat_target):
    return os.path.join(config.SCENARIOS_DIR, f"{scenario_id(protein, meat_target)}.json")


def load_papers_by_title():
    if not os.path.exists(config.PAPERS_CSV):
        return {}
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        return {row["_document_title"]: row for row in reader}


def _serialize_result(protein, meat_target, result, ranked, unmapped, explanation, rejection_stats):
    """Build the JSON-serializable dict saved to data/scenarios/<id>.json and returned to the UI."""
    return {
        "scenario": {"protein": protein, "meat_target": meat_target},
        "missing_notes": result["missing_notes"],
        "off_notes": result["off_notes"],
        "ranked_levers": ranked,
        "unmapped_levers": unmapped,
        "explanation": explanation,
        "rejection_stats": rejection_stats,
    }


def run_live(protein, meat_target, min_grade=None, exclude_e_numbers=False, top_n_chunks=None):
    """
    Run the full live pipeline for a scenario: retrieve -> extract -> verify ->
    append to facts.csv -> gap -> rank -> explain.

    top_n_chunks: optionally cap how many retrieved chunks go through extraction
        (keeps demo runs fast/cheap; None = use all deduplicated chunks).

    Returns the same shaped dict as run().
    """
    chunks = retrieve.retrieve_for_scenario(protein, meat_target)
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
        protein, meat_target,
        facts_rows=all_facts, min_grade=min_grade, papers_by_title=papers_by_title,
    )
    ranked, unmapped = rank.rank_levers(
        all_facts, gap_result["missing_notes"], gap_result["off_notes"],
        papers_by_title=papers_by_title, exclude_e_numbers=exclude_e_numbers,
    )
    explanation = explain.generate_explanation(
        protein, meat_target, gap_result["missing_notes"], gap_result["off_notes"], ranked,
    )

    return _serialize_result(protein, meat_target, gap_result, ranked, unmapped, explanation, rejection_stats)


def save_scenario(protein, meat_target, result):
    """
    Persist a run_live() result dict to data/scenarios/<id>.json. The
    "loaded_from_cache_file" marker key (if present) is stripped before
    saving, since that key is set by run() on read, not meant to be stored.
    """
    os.makedirs(config.SCENARIOS_DIR, exist_ok=True)
    to_save = {k: v for k, v in result.items() if k != "loaded_from_cache_file"}
    path = scenario_path(protein, meat_target)
    with open(path, "w") as f:
        json.dump(to_save, f, indent=2)
    return path


def run(protein, meat_target, min_grade=None, exclude_e_numbers=False, force_live=False,
        top_n_chunks=None, persist=False):
    """
    Main entry point used by the UI/API.

    - If a precomputed scenario file exists in data/scenarios/ and force_live
      is False, load and return it instantly (no Bedrock calls).
    - Otherwise run the live pipeline.
    - If persist=True and the live pipeline ran, save the result to
      data/scenarios/<id>.json so the next GET loads it instantly.
    """
    path = scenario_path(protein, meat_target)

    if not force_live and os.path.exists(path):
        with open(path, "r") as f:
            result = json.load(f)
        result["loaded_from_cache_file"] = True
        return result

    result = run_live(
        protein, meat_target,
        min_grade=min_grade, exclude_e_numbers=exclude_e_numbers, top_n_chunks=top_n_chunks,
    )
    result["loaded_from_cache_file"] = False

    if persist:
        save_scenario(protein, meat_target, result)

    return result
