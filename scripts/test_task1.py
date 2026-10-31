"""Task 1 test: one retrieve call, print 10 results (file, page, score)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bedrock

if __name__ == "__main__":
    query = "key odorants of cooked beef burger meaty aroma compounds"
    results = bedrock.retrieve(query)
    print(f"Query: {query}")
    print(f"Number of results: {len(results)}")
    print("-" * 70)
    for i, r in enumerate(results, 1):
        md = r.get("metadata", {})
        file = md.get("_document_title")
        page = md.get("_excerpt_page_number")
        score = r.get("score")
        print(f"{i:2d}. file={file}  page={page}  score={score:.4f}")
