"""
Extract structured fact rows from retrieved chunks using Claude Haiku via
Bedrock Converse with forced tool use (JSON schema). The model may only use
the given chunk text, never outside knowledge. One row per compound mention.

Row fields (see project brief 4.2):
food, preparation, compound, descriptor, role, lever, concentration,
threshold, quote, chunk_id, file, page, confidence
"""

import json

from core import bedrock, config

TOOL_NAME = "record_fact_rows"

VALID_ROLES = {"meat_marker", "off_note", "precursor", "masker", "removal"}

# Batch several chunks per Converse call to save requests (rate limit ~1 req/s).
CHUNKS_PER_BATCH = 6

_TOOL_SPEC = {
    "toolSpec": {
        "name": TOOL_NAME,
        "description": "Record one row per flavor/aroma compound mention found in the given text chunks.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "food": {"type": "string", "description": "e.g. beef burger, chicken, pea protein"},
                                "preparation": {"type": "string", "description": "e.g. grilled, cooked, raw, or empty string if not stated"},
                                "compound": {"type": "string", "description": "specific chemical name, e.g. 2-methyl-3-furanthiol, hexanal"},
                                "descriptor": {"type": "string", "description": "sensory descriptor, e.g. meaty, roasted, sulfurous, fatty, beany, green, grassy, bitter, astringent"},
                                "role": {"type": "string", "enum": sorted(VALID_ROLES)},
                                "lever": {"type": "string", "description": "ingredient or process mentioned that adds/removes/masks this note, or empty string if none"},
                                "concentration": {"type": "string", "description": "concentration value as stated in text, or empty string if not stated"},
                                "threshold": {"type": "string", "description": "odor/taste threshold as stated in text, or empty string if not stated"},
                                "quote": {"type": "string", "description": "exact substring copied verbatim from the chunk text, max 25 words, supporting this row"},
                                "chunk_id": {"type": "string", "description": "the chunk_id this row was extracted from"},
                                "confidence": {"type": "number", "description": "0 to 1, how confident the extraction is"},
                            },
                            "required": ["food", "compound", "descriptor", "role", "quote", "chunk_id", "confidence"],
                        },
                    }
                },
                "required": ["rows"],
            }
        },
    }
}

_SYSTEM_PROMPT = """You are a careful food-science data extractor. You read short excerpts from \
scientific papers about meat aroma/taste chemistry and plant protein off-flavors.

Rules:
- Only use information present in the given text chunks. Never use outside knowledge.
- Extract one row per distinct compound mention that is relevant to: meat-like aroma/taste markers, \
plant protein off-notes (beany, green, grassy, bitter, astringent), flavor precursors, or \
masking/removal methods.
- "quote" must be an exact substring copied from the chunk text (you may normalize whitespace), \
at most 25 words, that supports the row.
- If a chunk has nothing relevant, simply contribute no rows for it.
- Do not invent compound names, descriptors, or quotes that are not in the text.
- "role" must be one of: meat_marker (characteristic of the cooked meat target), off_note (undesirable \
note of the plant protein), precursor (flavor precursor for Maillard/meaty flavor), masker (something that \
masks an off-note), removal (a process that removes an off-note).
- Use the record_fact_rows tool to return your answer. If no chunk has anything relevant, call the tool \
with an empty rows list."""


def _build_user_text(chunks):
    parts = []
    for c in chunks:
        parts.append(
            f"chunk_id: {c['chunk_id']}\n"
            f"file: {c['file']}\n"
            f"page: {c['page']}\n"
            f"text: {c['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _chunk_batches(chunks, batch_size):
    for i in range(0, len(chunks), batch_size):
        yield chunks[i:i + batch_size]


def _extract_batch(chunks):
    """Run one Converse call (Haiku, forced tool use) over a batch of chunks. Returns raw rows (list of dicts)."""
    user_text = _build_user_text(chunks)
    messages = [
        {"role": "user", "content": [{"text": user_text}]}
    ]
    tool_config = {
        "tools": [_TOOL_SPEC],
        "toolChoice": {"tool": {"name": TOOL_NAME}},
    }
    response = bedrock.converse(
        model_id=config.HAIKU_MODEL_ID,
        messages=messages,
        system=[{"text": _SYSTEM_PROMPT}],
        tool_config=tool_config,
        max_tokens=4096,
        temperature=0.0,
    )

    output_message = response.get("output", {}).get("message", {})
    for block in output_message.get("content", []):
        tool_use = block.get("toolUse")
        if tool_use and tool_use.get("name") == TOOL_NAME:
            return tool_use.get("input", {}).get("rows", [])
    return []


def _chunk_lookup(chunks):
    return {c["chunk_id"]: c for c in chunks}


def extract_rows(chunks):
    """
    Run extraction over all chunks in batches of CHUNKS_PER_BATCH.
    Returns a flat list of raw extracted rows, each augmented with file/page
    looked up from the source chunk (in case the model omits them).
    """
    lookup = _chunk_lookup(chunks)
    all_rows = []

    for batch in _chunk_batches(chunks, CHUNKS_PER_BATCH):
        raw_rows = _extract_batch(batch)
        for row in raw_rows:
            chunk_id = row.get("chunk_id")
            source_chunk = lookup.get(chunk_id)
            if source_chunk:
                row["file"] = source_chunk["file"]
                row["page"] = source_chunk["page"]
            else:
                row.setdefault("file", None)
                row.setdefault("page", None)
            all_rows.append(row)

    return all_rows
