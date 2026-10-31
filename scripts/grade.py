"""
scripts/grade.py

For each PDF listed in data/papers.csv, send the first 2 pages of extracted
text (from data/text/<document_title>/page_1.txt, page_2.txt) to Haiku with
a 4-criterion rubric, each scored 0-1:

  - analytical_method: uses GC-MS, GC-O, or formal sensory panel methods
  - quantification: reports actual concentrations/amounts, not just mentions
  - sample_relevance: sample is pea/soy/faba protein or beef/chicken (cooked)
  - sensory_validation: includes a human sensory evaluation/panel

grade = sum of the 4 criteria, clipped to 0-3 (so a perfect 4/4 paper still
reports as 3, per the brief's 0-3 scale).

Writes grade and grade_reason back into data/papers.csv (origin: model-extracted,
since Haiku reads the paper and the reasoning is a short justification, not a
verbatim quote requirement here -- this is a paper-level judgment call, not a
per-compound fact row).
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bedrock, config

TOOL_NAME = "record_grade"

_TOOL_SPEC = {
    "toolSpec": {
        "name": TOOL_NAME,
        "description": "Record a 0-3 grade for this paper based on a 4-criterion rubric.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "analytical_method": {"type": "integer", "enum": [0, 1], "description": "1 if the paper uses GC-MS, GC-O, or a formal sensory panel method; else 0"},
                    "quantification": {"type": "integer", "enum": [0, 1], "description": "1 if the paper reports actual concentrations/amounts, not just qualitative mentions; else 0"},
                    "sample_relevance": {"type": "integer", "enum": [0, 1], "description": "1 if the sample studied is pea/soy/faba protein or beef/chicken (cooked); else 0"},
                    "sensory_validation": {"type": "integer", "enum": [0, 1], "description": "1 if the paper includes a human sensory evaluation/panel; else 0"},
                    "reason": {"type": "string", "description": "one short sentence justifying the four scores"},
                },
                "required": ["analytical_method", "quantification", "sample_relevance", "sensory_validation", "reason"],
            }
        },
    }
}

_SYSTEM_PROMPT = """You are grading scientific papers for an evidence-based plant-based flavor R&D tool. \
You will be given the first ~2 pages of a paper (title, abstract, introduction). Score it on 4 criteria \
using ONLY the given text. Use the record_grade tool to return your answer."""


def _read_first_pages_text(document_title, num_pages=2):
    out_dir = os.path.join(config.TEXT_DIR, document_title)
    text = ""
    for i in range(1, num_pages + 1):
        page_path = os.path.join(out_dir, f"page_{i}.txt")
        if os.path.exists(page_path):
            with open(page_path, "r") as f:
                text += f.read() + "\n"
    return text.strip()


def grade_paper(document_title):
    """Returns (grade int 0-3, grade_reason str). Returns (None, reason) if no text available."""
    text = _read_first_pages_text(document_title)
    if not text:
        return None, "no extracted text available for this paper"

    messages = [{"role": "user", "content": [{"text": text}]}]
    tool_config = {
        "tools": [_TOOL_SPEC],
        "toolChoice": {"tool": {"name": TOOL_NAME}},
    }
    response = bedrock.converse(
        model_id=config.HAIKU_MODEL_ID,
        messages=messages,
        system=[{"text": _SYSTEM_PROMPT}],
        tool_config=tool_config,
        max_tokens=512,
        temperature=0.0,
    )

    output_message = response.get("output", {}).get("message", {})
    for block in output_message.get("content", []):
        tool_use = block.get("toolUse")
        if tool_use and tool_use.get("name") == TOOL_NAME:
            result = tool_use.get("input", {})
            raw_sum = (
                result.get("analytical_method", 0)
                + result.get("quantification", 0)
                + result.get("sample_relevance", 0)
                + result.get("sensory_validation", 0)
            )
            grade = min(raw_sum, 3)
            reason = result.get("reason", "")
            return grade, reason

    return None, "model did not return a grade"


def grade_all_papers():
    """Read papers.csv, grade each paper, write grade/grade_reason back. Returns the updated rows."""
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    for row in rows:
        document_title = row["_document_title"]
        grade, reason = grade_paper(document_title)
        row["grade"] = grade if grade is not None else ""
        row["grade_reason"] = reason
        print(f"{document_title}: grade={grade}  reason={reason}")

    with open(config.PAPERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def print_coverage_table(rows):
    from scripts.catalog import PROTEIN_KEYWORDS, MEAT_KEYWORDS

    proteins = list(PROTEIN_KEYWORDS.keys())
    meats = list(MEAT_KEYWORDS.keys())

    print()
    print("Protein x meat coverage, restricted to papers with grade >= 2:")
    header = "protein".ljust(10) + "".join(m.ljust(10) for m in meats)
    print(header)
    for p in proteins:
        counts = []
        for m in meats:
            count = sum(
                1 for r in rows
                if p in r["protein_tags"].split(",")
                and m in r["meat_tags"].split(",")
                and r["grade"] != "" and int(r["grade"]) >= 2
            )
            counts.append(count)
        print(p.ljust(10) + "".join(str(c).ljust(10) for c in counts))

    graded = [r for r in rows if r["grade"] != ""]
    print()
    print(f"Graded {len(graded)}/{len(rows)} papers.")
    if graded:
        avg = sum(int(r["grade"]) for r in graded) / len(graded)
        print(f"Average grade: {avg:.2f}")
        for g in (0, 1, 2, 3):
            count = sum(1 for r in graded if int(r["grade"]) == g)
            print(f"  grade {g}: {count} paper(s)")


if __name__ == "__main__":
    rows = grade_all_papers()
    print_coverage_table(rows)
