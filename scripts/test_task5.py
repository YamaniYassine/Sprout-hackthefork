"""Task 5 test: gap.py + rank.py + lever_catalog.csv for pea -> beef burger. No Bedrock calls (deterministic)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import facts, gap, rank


def load_papers_by_title():
    import csv
    from core import config
    if not os.path.exists(config.PAPERS_CSV):
        return {}
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        return {row["_document_title"]: row for row in reader}


if __name__ == "__main__":
    protein = "pea"
    meat_target = "beef burger"
    cooking = "grilled"

    rows = facts.load_facts()
    papers_by_title = load_papers_by_title()
    print(f"Loaded {len(rows)} verified facts from data/facts.csv")
    print(f"Loaded {len(papers_by_title)} papers from data/papers.csv")
    print("=" * 70)

    result = gap.analyze_gap(protein, meat_target, cooking, facts_rows=rows)
    meat_profile = result["meat_profile"]
    plant_profile = result["plant_profile"]
    missing_notes = result["missing_notes"]
    off_notes = result["off_notes"]

    print(f"Meat profile rows (meat_marker matching '{meat_target}'): {len(meat_profile)}")
    print(f"Plant profile rows (off_note matching '{protein}'): {len(plant_profile)}")
    print()

    print("MISSING MEAT-LIKE NOTES (meat markers absent from plant profile)")
    print("-" * 70)
    if not missing_notes:
        print("  No evidence found in the corpus for this section.")
    for m in missing_notes:
        print(f"  descriptor={m['descriptor']!r}  n_papers={m['n_papers']}  compounds={m['compounds']}")
        print(f"    papers: {m['papers']}")
    print()

    print("OFF-NOTES OF THE PLANT PROTEIN")
    print("-" * 70)
    if not off_notes:
        print("  No evidence found in the corpus for this section.")
    for o in off_notes:
        print(f"  descriptor={o['descriptor']!r}  n_papers={o['n_papers']}  compounds={o['compounds']}")
        print(f"    papers: {o['papers']}")
    print()

    print("=" * 70)
    print("RANKED PLANT-ONLY LEVERS")
    print("=" * 70)
    ranked, unmapped = rank.rank_levers(rows, missing_notes, off_notes, papers_by_title=papers_by_title)

    print(f"{'rank':<5}{'lever':<35}{'type':<10}{'score':<8}{'papers':<8}{'cost':<8}{'clean':<7}{'conf':<6}")
    for i, lever in enumerate(ranked, 1):
        print(f"{i:<5}{lever['lever']:<35}{lever['type']:<10}{lever['score']:<8}{lever['n_papers']:<8}"
              f"{lever['cost_tier']:<8}{lever['clean_label']:<7}{lever['mean_confidence']:<6}")
        print(f"      targeted gaps: {lever['targeted_gap_descriptors']}")

    print()
    print(f"Unmapped lever mentions ({len(unmapped)}), shown but not ranked:")
    for u in unmapped:
        print(f"  - {u!r}")
