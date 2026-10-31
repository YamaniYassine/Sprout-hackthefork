"""Test for 7a: core/present.py on soy -> chicken. Prints top 10 off-notes, ranked levers, unmapped count."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import facts, pipeline, present


def load_papers_by_title():
    import csv
    from core import config
    if not os.path.exists(config.PAPERS_CSV):
        return {}
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        return {row["_document_title"]: row for row in reader}


if __name__ == "__main__":
    protein = "soy"
    meat_target = "chicken"

    all_facts = facts.load_facts()
    papers_by_title = load_papers_by_title()

    pipeline_result = pipeline.run(protein, meat_target, force_live=False)

    result = present.present(
        protein, meat_target, pipeline_result, all_facts, papers_by_title, source="live",
    )

    print("=" * 70)
    print(f"SCENARIO: {protein} -> {meat_target}")
    print("=" * 70)
    print("KPIs:", result["kpis"])
    print()

    print("TOP 10 OFF-NOTES (by evidence_score):")
    print("-" * 70)
    for m in result["off_notes"][:10]:
        print(f"  {m['molecule']:<40} family={m['family']:<18} score={m['evidence_score']:<7} "
              f"papers={m['n_papers']} oav={m['oav']} scope={m['scope']} cid={m['pubchem_cid']}")

    print()
    print(f"Total off-note molecules: {len(result['off_notes'])}")
    print(f"Compound classes (excluded from molecule list): {result['compound_classes']}")

    print()
    print("MISSING NOTES (meat markers absent from plant profile, precursors excluded):")
    print("-" * 70)
    for m in result["missing_notes"]:
        print(f"  {m['molecule']:<40} family={m['family']:<18} score={m['evidence_score']:<7} papers={m['n_papers']}")

    print()
    print("FAMILY PROFILE (for radar chart):")
    print("-" * 70)
    for f in result["family_profile"]:
        print(f"  {f['side']:<16} {f['family']:<18} score={f['evidence_score']}")

    print()
    print("=" * 70)
    print(f"RANKED LEVERS ({len(result['levers'])}):")
    print("=" * 70)
    for lever in result["levers"]:
        print(f"  #{lever['rank']} {lever['name']}  kind={lever['kind']}  score={lever['score']}  "
              f"papers={lever['n_papers']}  cost={lever['cost_tier']}  clean_label={lever['clean_label']}")
        print(f"      removes_or_masks: {lever['removes_or_masks']}")
        print(f"      adds: {lever['adds']}")
        print(f"      stated_dose: {lever['stated_dose']}")

    print()
    print(f"Unmapped lever mentions: {result['unmapped_lever_mentions']}")

    print()
    print("EXPLANATION:")
    print(result["explanation"]["text"])
    print("citations_valid:", result["explanation"]["citations_valid"])

    print()
    print("FORMULAS:", result["formulas"])
    print()
    print("LIMITS:")
    for l in result["limits"]:
        print(f"  - {l}")

    print()
    print(f"Evidence store size: {len(result['evidence'])}")
    sample_id = next(iter(result["evidence"]), None)
    if sample_id:
        print("Sample evidence record:", result["evidence"][sample_id])
