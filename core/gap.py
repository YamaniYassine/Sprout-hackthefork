"""
core/gap.py - deterministic gap analysis (NO LLM).

Reads verified facts from data/facts.csv and computes, for a given scenario
(protein, meat_target, cooking):

- meat profile: verified rows with role == "meat_marker" whose food/preparation
  text is plausibly about the meat target (and cooking state, when stated).
- plant profile: verified rows with role == "off_note" whose food text is
  plausibly about the protein (pea/soy/faba) or its analogues.
- missing notes: meat-marker descriptors absent from the plant profile's
  descriptors, grouped by descriptor, each with the number of distinct
  supporting papers (file).
- off-notes: plant off-note compounds grouped by descriptor, each with the
  number of distinct supporting papers.

Matching food text to a scenario is necessarily approximate (facts.csv has
free-text "food" values like "extruded product", "cooked meat", "texturized
soy protein"), so we use keyword matching rather than exact equality.
"""

from collections import defaultdict

from core import facts as facts_module

# Keywords that indicate a row's "food" text is about the given meat target.
MEAT_TARGET_KEYWORDS = {
    "beef burger": ["beef", "burger", "cooked meat", "meat", "bovine"],
    "chicken": ["chicken", "poultry"],
}

# Keywords that indicate a row's "food" text is about the given plant protein
# (or a product made from it: extruded/texturized analogues count).
PROTEIN_KEYWORDS = {
    "pea": ["pea"],
    "soy": ["soy", "soybean"],
    "faba": ["faba", "fava"],
}

# Rows whose food mentions one of these are analogue/process products and
# should count toward the protein's profile even if the protein name itself
# isn't repeated (e.g. "extruded product", "texturized soy protein").
ANALOGUE_KEYWORDS = ["extruded", "texturized", "textured", "analogue", "analog"]


def _food_matches_any(food_text, keywords):
    if not food_text:
        return False
    food_lower = food_text.lower()
    return any(kw in food_lower for kw in keywords)


def _row_matches_meat_target(row, meat_target):
    keywords = MEAT_TARGET_KEYWORDS.get(meat_target, [meat_target.lower()])
    food = row.get("food", "")
    prep = row.get("preparation", "")
    combined = f"{food} {prep}"
    return _food_matches_any(combined, keywords)


def _row_matches_protein(row, protein):
    keywords = PROTEIN_KEYWORDS.get(protein, [protein.lower()])
    food = row.get("food", "")
    if _food_matches_any(food, keywords):
        return True
    # Also count analogue/process-derived rows (e.g. "extruded product",
    # "texturized soy protein") since these are the plant base being evaluated.
    if _food_matches_any(food, ANALOGUE_KEYWORDS):
        return True
    return False


def _distinct_papers(rows):
    return {r.get("file") for r in rows if r.get("file")}


def build_meat_profile(rows, meat_target, cooking=None):
    """
    Return the list of verified rows with role == meat_marker that are relevant
    to the meat target.

    The extraction step already labels a row role="meat_marker" only when the
    source text ties the compound to cooked-meat aroma/taste, so that label is
    the primary signal. The "food" field is often the matrix the marker was
    measured in (e.g. "extruded product", "texturized soy protein") rather than
    a literal mention of the meat target, so it is used only as an extra signal:
    rows naming the meat target explicitly are kept; rows naming a different,
    unrelated specific meat (e.g. "chicken" when the target is "beef burger")
    are excluded; rows with a generic/analogue food (not naming any specific
    meat) are kept since the role label already establishes relevance.
    """
    other_meat_keywords = [
        kw for target, kws in MEAT_TARGET_KEYWORDS.items() if target != meat_target for kw in kws
    ]

    def _is_relevant(row):
        if row.get("role") != "meat_marker":
            return False
        food = f"{row.get('food', '')} {row.get('preparation', '')}".lower()
        if _food_matches_any(food, other_meat_keywords):
            # explicitly names a different meat target: exclude
            return False
        return True

    return [r for r in rows if _is_relevant(r)]


def build_plant_profile(rows, protein):
    """Return the list of verified rows with role == off_note matching the protein."""
    profile = [r for r in rows if r.get("role") == "off_note" and _row_matches_protein(r, protein)]
    return profile


def _group_by_descriptor(rows):
    """Group rows by descriptor (lowercased). Returns dict descriptor -> list of rows."""
    groups = defaultdict(list)
    for r in rows:
        descriptor = (r.get("descriptor") or "").strip().lower()
        if descriptor:
            groups[descriptor].append(r)
    return groups


def compute_missing_notes(meat_profile, plant_profile):
    """
    Missing notes = meat-marker descriptors absent from the plant profile's
    descriptors, grouped by descriptor, each with the number of distinct
    supporting papers and the compounds/rows behind it.
    """
    meat_groups = _group_by_descriptor(meat_profile)
    plant_descriptors = set(_group_by_descriptor(plant_profile).keys())

    missing = []
    for descriptor, rows in meat_groups.items():
        if descriptor in plant_descriptors:
            continue
        papers = _distinct_papers(rows)
        compounds = sorted({r.get("compound") for r in rows if r.get("compound")})
        missing.append({
            "descriptor": descriptor,
            "n_papers": len(papers),
            "papers": sorted(papers),
            "compounds": compounds,
            "rows": rows,
        })

    missing.sort(key=lambda m: m["n_papers"], reverse=True)
    return missing


def compute_off_notes(plant_profile):
    """Off-notes = plant off-note compounds grouped by descriptor, with supporting paper counts."""
    groups = _group_by_descriptor(plant_profile)

    off_notes = []
    for descriptor, rows in groups.items():
        papers = _distinct_papers(rows)
        compounds = sorted({r.get("compound") for r in rows if r.get("compound")})
        off_notes.append({
            "descriptor": descriptor,
            "n_papers": len(papers),
            "papers": sorted(papers),
            "compounds": compounds,
            "rows": rows,
        })

    off_notes.sort(key=lambda o: o["n_papers"], reverse=True)
    return off_notes


def analyze_gap(protein, meat_target, cooking=None, facts_rows=None, min_grade=None, papers_by_title=None):
    """
    Top-level deterministic gap analysis for a scenario.

    facts_rows: optionally pass in pre-loaded rows (e.g. from a live pipeline
        run); otherwise loads from data/facts.csv.
    min_grade: optionally filter out rows whose paper grade is below this
        threshold (requires papers_by_title: dict file -> paper row with "grade").

    Returns {"meat_profile": [...], "plant_profile": [...], "missing_notes": [...], "off_notes": [...]}.
    """
    rows = facts_rows if facts_rows is not None else facts_module.load_facts()

    if min_grade is not None and papers_by_title is not None:
        def _passes_grade(row):
            paper = papers_by_title.get(row.get("file"))
            if paper is None or paper.get("grade") in (None, ""):
                return False
            try:
                return int(float(paper["grade"])) >= min_grade
            except (TypeError, ValueError):
                return False

        rows = [r for r in rows if _passes_grade(r)]

    meat_profile = build_meat_profile(rows, meat_target, cooking)
    plant_profile = build_plant_profile(rows, protein)
    missing_notes = compute_missing_notes(meat_profile, plant_profile)
    off_notes = compute_off_notes(plant_profile)

    return {
        "meat_profile": meat_profile,
        "plant_profile": plant_profile,
        "missing_notes": missing_notes,
        "off_notes": off_notes,
    }
