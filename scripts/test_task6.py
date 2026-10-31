"""Task 6 test: explain.py for pea -> beef burger. Prints the explanation and whether citations were pruned."""

import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import facts, gap, rank, explain, config


def load_papers_by_title():
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

    result = gap.analyze_gap(protein, meat_target, cooking, facts_rows=rows)
    ranked, unmapped = rank.rank_levers(
        rows, result["missing_notes"], result["off_notes"], papers_by_title=papers_by_title
    )

    print(f"missing_notes sections: {len(result['missing_notes'])}")
    print(f"off_notes sections: {len(result['off_notes'])}")
    print(f"ranked levers: {len(ranked)}")
    print("=" * 70)

    explanation = explain.generate_explanation(
        protein, meat_target, cooking, result["missing_notes"], result["off_notes"], ranked
    )

    print("EXPLANATION:")
    print(explanation["text"])
    print()
    print(f"word_count: {explanation['word_count']} (limit {explain.MAX_WORDS})")
    print(f"citations_pruned: {explanation['citations_pruned']}")
    print(f"has_evidence: {explanation['has_evidence']}")

    print()
    print("=" * 70)
    print("Citation tags found in final text:")
    brackets = explain.BRACKET_PATTERN.findall(explanation["text"])
    for b in brackets:
        print(f"  [{b}]")

    print()
    print("Valid citation set (file, page) available to the model:")
    valid = explain._collect_valid_citations(result["missing_notes"], result["off_notes"], ranked)
    for file, page in sorted(valid):
        print(f"  ({file}, {page})")
