"""
core/explain.py

Sonnet writes a short (<=150 words) explanation of the gap/lever analysis for
a scenario, using ONLY the verified fact rows (and their source chunks) as
input. Every claim must carry an inline citation tag "[file p.N]".

After generation, every "[file p.N]" tag is checked against the known set of
(file, page) pairs from the verified rows actually given to the model. Any
tag that doesn't match a real (file, page) pair is stripped and the answer is
flagged as "citations_pruned = True" so the UI can show a warning.

If there are no verified rows for a section (missing notes / off-notes /
levers), the explanation says so explicitly rather than inventing content.

The call is cached (via core.bedrock.converse), so re-running on the same
scenario/rows never repeats the Bedrock call.
"""

import re

from core import bedrock, config

MAX_WORDS = 150

# Matches a single "file p.N" citation. Also used to split multi-citation
# brackets like "[fileA p.1; fileB p.2]" that the model sometimes produces
# despite being told not to -- each inner "file p.N" is extracted separately.
CITATION_PATTERN = re.compile(r"([^\[\];]+?)\s+p\.\s*(\d+(?:\.\d+)?)")
BRACKET_PATTERN = re.compile(r"\[([^\[\]]+)\]")

_SYSTEM_PROMPT = f"""You write short, evidence-based explanations for a food R&D tool. You will be \
given verified fact rows (compound, descriptor, role, lever, food, confidence) each tagged with the \
exact file name and page number it came from, for a plant-protein-to-meat-target flavor gap analysis.

Rules:
- Use ONLY the given rows. Never use outside knowledge about flavor chemistry.
- Write at most {MAX_WORDS} words, one short paragraph.
- Cover, if the data allows: (1) the key missing meat-like notes, (2) the plant protein's main \
off-notes, (3) the top ranked lever(s) that could address them.
- Every factual claim must end with an inline citation tag in the exact format "[file p.N]" where \
file and N come from the row you are citing. Use the file name exactly as given.
- Each citation tag must contain exactly ONE file and ONE page. If a claim is supported by two \
sources, write two separate adjacent tags like "[fileA p.N][fileB p.M]". Never combine two sources \
inside one bracket (do NOT write "[fileA p.N; fileB p.M]").
- If a section has no supporting rows, say plainly that no evidence was found in the corpus for that \
part, and do not cite anything for it.
- Do not invent compounds, descriptors, levers, file names, or page numbers not present in the given rows.
- This is a literature-based prediction, not a tasted or proven result. You do not need to say this \
disclaimer yourself, the UI shows it separately.
- Output plain text only, no markdown headers."""


def _format_row_for_prompt(row):
    return (
        f"- compound={row.get('compound')}, descriptor={row.get('descriptor')}, role={row.get('role')}, "
        f"lever={row.get('lever') or 'none'}, food={row.get('food')}, confidence={row.get('confidence')}, "
        f"source=[{row.get('file')} p.{row.get('page')}]"
    )


def _build_user_prompt(protein, meat_target, missing_notes, off_notes, ranked_levers):
    parts = [f"Scenario: protein={protein}, meat_target={meat_target} (cooked meat, all cooking methods pooled)", ""]

    parts.append("MISSING MEAT-LIKE NOTES (meat markers absent from the plant profile):")
    if not missing_notes:
        parts.append("(none found)")
    else:
        for m in missing_notes:
            for row in m["rows"]:
                parts.append(_format_row_for_prompt(row))

    parts.append("")
    parts.append("OFF-NOTES OF THE PLANT PROTEIN:")
    if not off_notes:
        parts.append("(none found)")
    else:
        for o in off_notes:
            for row in o["rows"]:
                parts.append(_format_row_for_prompt(row))

    parts.append("")
    parts.append("TOP RANKED LEVERS:")
    if not ranked_levers:
        parts.append("(none found)")
    else:
        for lever in ranked_levers[:3]:
            parts.append(f"Lever: {lever['lever']} (score={lever['score']}, n_papers={lever['n_papers']})")
            for row in lever["matched_facts"][:5]:
                parts.append(_format_row_for_prompt(row))

    return "\n".join(parts)


def _collect_valid_citations(missing_notes, off_notes, ranked_levers):
    """Build the set of (file, page) pairs that are legitimately citable for this scenario."""
    valid = set()

    def _add_rows(rows):
        for r in rows:
            file = r.get("file")
            page = r.get("page")
            if file is None or page is None:
                continue
            valid.add((str(file).strip(), str(float(page))))

    for m in missing_notes:
        _add_rows(m["rows"])
    for o in off_notes:
        _add_rows(o["rows"])
    for lever in ranked_levers:
        _add_rows(lever["matched_facts"])

    return valid


def _parse_citation(piece):
    """Parse a single 'file p.N' piece. Returns (file, page_key) or None if malformed."""
    match = CITATION_PATTERN.fullmatch(piece.strip())
    if not match:
        return None
    file = match.group(1).strip()
    page_str = match.group(2)
    try:
        page_key = str(float(page_str))
    except ValueError:
        page_key = page_str
    return file, page_key


def _prune_invalid_citations(text, valid_citations):
    """
    For every [...] bracket, split on ';' (in case the model combined multiple
    citations in one bracket despite being told not to), keep only the pieces
    that parse as a single "file p.N" citation AND match valid_citations,
    and rebuild the bracket(s). A bracket that ends up empty is removed
    entirely. Returns (pruned_text, any_pruned_bool).
    """
    any_pruned = False

    def _replace_bracket(match):
        nonlocal any_pruned
        inner = match.group(1)
        pieces = [p.strip() for p in inner.split(";") if p.strip()]
        kept_tags = []
        for piece in pieces:
            parsed = _parse_citation(piece)
            if parsed is not None and parsed in valid_citations:
                kept_tags.append(f"[{piece}]")
            else:
                any_pruned = True
        return "".join(kept_tags)

    pruned_text = BRACKET_PATTERN.sub(_replace_bracket, text)
    # collapse any double spaces left behind by removed tags
    pruned_text = re.sub(r"\s{2,}", " ", pruned_text).strip()
    # clean up stray space before a leftover/adjacent citation bracket
    pruned_text = re.sub(r"\s+\]", "]", pruned_text)
    return pruned_text, any_pruned


def generate_explanation(protein, meat_target, missing_notes, off_notes, ranked_levers):
    """
    Returns a dict:
        {
            "text": str,                 # final explanation, with invalid citations removed
            "citations_pruned": bool,     # True if any tag had to be removed
            "word_count": int,
            "has_evidence": bool,         # False if all three sections were empty
        }
    """
    has_evidence = bool(missing_notes) or bool(off_notes) or bool(ranked_levers)

    if not has_evidence:
        return {
            "text": "No evidence found in the corpus for this scenario.",
            "citations_pruned": False,
            "word_count": 8,
            "has_evidence": False,
        }

    user_prompt = _build_user_prompt(protein, meat_target, missing_notes, off_notes, ranked_levers)
    messages = [{"role": "user", "content": [{"text": user_prompt}]}]

    response = bedrock.converse(
        model_id=config.SONNET_MODEL_ID,
        messages=messages,
        system=[{"text": _SYSTEM_PROMPT}],
        max_tokens=600,
        temperature=0.0,
    )

    output_message = response.get("output", {}).get("message", {})
    raw_text = ""
    for block in output_message.get("content", []):
        if "text" in block:
            raw_text += block["text"]

    valid_citations = _collect_valid_citations(missing_notes, off_notes, ranked_levers)
    pruned_text, any_pruned = _prune_invalid_citations(raw_text, valid_citations)

    word_count = len(pruned_text.split())

    return {
        "text": pruned_text,
        "citations_pruned": any_pruned,
        "word_count": word_count,
        "has_evidence": True,
    }
