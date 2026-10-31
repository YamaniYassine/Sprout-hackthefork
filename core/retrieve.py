"""
Build templated queries for a scenario (protein, meat target), run them
against the knowledge base, and return a deduplicated list of chunks.

v2: no cooking-state input. Queries use "cooked {meat_target}" so the
analysis pools evidence across all cooking methods found in the corpus
(grilled, pan-fried, etc.) rather than filtering to one method.

Each chunk in the returned list looks like:
{
    "chunk_id": str,
    "text": str,
    "file": str,
    "page": float or None,
    "score": float,
    "queries": [str, ...],   # all queries that retrieved this chunk
}
"""

from core import bedrock


def build_queries(protein, meat_target):
    """Return ~6-8 templated queries for this scenario."""
    return [
        f"key odorants of cooked {meat_target} meaty aroma compounds",
        f"{meat_target} meaty aroma compounds sulfur Maillard",
        f"{protein} protein off-flavor volatile compounds beany green",
        f"removal or masking of {protein} protein off-flavors",
        f"flavor precursors meat analogue {protein} Maillard cysteine xylose yeast extract",
        f"{protein} meat analogue compared with {meat_target} aroma GC-MS",
        f"{protein} protein bitter astringent off-note compounds",
        f"plant-based {meat_target} analogue key aroma compounds sensory",
    ]


def _chunk_from_result(result, query_text):
    content = result.get("content", {})
    metadata = result.get("metadata", {})
    chunk_id = metadata.get("_chunk_id")
    return {
        "chunk_id": chunk_id,
        "text": content.get("text", ""),
        "file": metadata.get("_document_title"),
        "page": metadata.get("_excerpt_page_number"),
        "score": result.get("score"),
        "queries": [query_text],
    }


def retrieve_for_scenario(protein, meat_target):
    """
    Run all templated queries for the scenario against the KB and return a
    deduplicated list of chunks (deduplicated by _chunk_id). If the same
    chunk is retrieved by multiple queries, its "queries" list accumulates
    all of them and the highest score is kept.
    """
    queries = build_queries(protein, meat_target)
    chunks_by_id = {}

    for query_text in queries:
        results = bedrock.retrieve(query_text)
        for result in results:
            chunk = _chunk_from_result(result, query_text)
            chunk_id = chunk["chunk_id"]
            if chunk_id is None:
                continue
            if chunk_id not in chunks_by_id:
                chunks_by_id[chunk_id] = chunk
            else:
                existing = chunks_by_id[chunk_id]
                if query_text not in existing["queries"]:
                    existing["queries"].append(query_text)
                if chunk["score"] is not None and (existing["score"] is None or chunk["score"] > existing["score"]):
                    existing["score"] = chunk["score"]

    deduped = list(chunks_by_id.values())
    deduped.sort(key=lambda c: (c["score"] if c["score"] is not None else 0.0), reverse=True)
    return deduped
