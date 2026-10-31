"""Task 2 test: retrieve.py for scenario pea -> beef burger. Prints the deduplicated chunk list."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import retrieve

if __name__ == "__main__":
    protein = "pea"
    meat_target = "beef burger"
    cooking = "grilled"

    queries = retrieve.build_queries(protein, meat_target, cooking)
    print(f"Scenario: {protein} -> {meat_target} ({cooking})")
    print(f"Number of queries: {len(queries)}")
    for q in queries:
        print(f"  - {q}")
    print("-" * 70)

    chunks = retrieve.retrieve_for_scenario(protein, meat_target, cooking)
    print(f"Deduplicated chunks: {len(chunks)}")
    print("-" * 70)
    for i, c in enumerate(chunks, 1):
        print(f"{i:2d}. chunk_id={c['chunk_id']}")
        print(f"    file={c['file']}  page={c['page']}  score={c['score']:.4f}")
        print(f"    matched by {len(c['queries'])} query(ies): {c['queries']}")
        print(f"    text[:120]: {c['text'][:120]!r}")
