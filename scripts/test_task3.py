"""Task 3 test: extract.py + verify.py on pea -> beef burger chunks. Prints accepted and rejected rows."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import retrieve, extract, verify

if __name__ == "__main__":
    protein = "pea"
    meat_target = "beef burger"
    cooking = "grilled"

    chunks = retrieve.retrieve_for_scenario(protein, meat_target, cooking)
    print(f"Retrieved {len(chunks)} deduplicated chunks for {protein} -> {meat_target}")

    # Keep the test fast/cheap: extract over the top N highest-scoring chunks.
    top_chunks = chunks[:18]
    print(f"Running extraction on top {len(top_chunks)} chunks (batches of {extract.CHUNKS_PER_BATCH})")
    print("-" * 70)

    raw_rows = extract.extract_rows(top_chunks)
    print(f"Raw extracted rows: {len(raw_rows)}")

    chunk_lookup = {c["chunk_id"]: c for c in top_chunks}
    accepted, rejected = verify.verify_rows(raw_rows, chunk_lookup, resolve_pubchem=True)

    print(f"Accepted: {len(accepted)}   Rejected: {len(rejected)}")
    print("=" * 70)
    print("ACCEPTED ROWS")
    print("=" * 70)
    for i, row in enumerate(accepted, 1):
        print(f"{i:2d}. compound={row.get('compound')!r}  descriptor={row.get('descriptor')!r}  role={row.get('role')}")
        print(f"    food={row.get('food')!r}  lever={row.get('lever')!r}  confidence={row.get('confidence')}")
        print(f"    file={row.get('file')}  page={row.get('page')}  pubchem_cid={row.get('pubchem_cid')} resolved={row.get('resolved')}")
        print(f"    quote: {row.get('quote')!r}")
        print()

    print("=" * 70)
    print("REJECTED ROWS")
    print("=" * 70)
    for i, row in enumerate(rejected, 1):
        print(f"{i:2d}. compound={row.get('compound')!r}  reason={row.get('reason')}")
        print(f"    quote: {row.get('quote')!r}")
        print()

    verify.log_rejected(rejected)
    print(f"Logged {len(rejected)} rejected rows to data/rejected.csv")
