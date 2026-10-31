"""
core/present.py (v2)

Deterministic presentation layer (NO LLM) that turns raw pipeline output
(gap.analyze_gap + rank.rank_levers + explain.generate_explanation) into the
clean API response shape consumed by the React frontend (see web/src/types.ts
for the TypeScript mirror of this shape).

Responsibilities, in order (see FlavorGap v2 brief section 2):
1. Map free-text descriptors to a fixed family vocabulary (data/descriptor_map.csv).
2. Exclude generic class terms from molecule lists (data/generic_terms.txt),
   reporting them separately as "compound_classes".
3. Normalize molecule names and merge synonyms (data/synonyms.csv + PubChem CID).
4. Move precursor-role rows out of "missing meat notes" into the levers side.
5. Filter off-notes to rows whose food matches the selected protein (keep
   "general plant protein" rows, flagged scope="general").
6. Attach stated dosages found in quotes to their lever.
7. Compute OAV when both concentration and threshold are clean, same-unit
   sourced numbers; otherwise null.
8. Render pages as integers ("p.9", not "p.9.0").

Every evidence item gets a stable id so the API can serve full records via
GET /api/evidence/{id} without re-sending everything inline.
"""

import csv
import os
import re
from collections import defaultdict

from core import config

# --- Mapping file loaders -------------------------------------------------


def _load_descriptor_map(path=None):
    """Returns list of (keyword_lowercase, family), longest keyword first for greedy matching."""
    path = path or config.DESCRIPTOR_MAP_CSV
    pairs = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = row["raw_descriptor_keyword"].strip().lower()
            family = row["family"].strip()
            if kw:
                pairs.append((kw, family))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def _load_generic_terms(path=None):
    path = path or config.GENERIC_TERMS_TXT
    terms = set()
    with open(path, "r") as f:
        for line in f:
            line = line.strip().lower()
            if line:
                terms.add(line)
    return terms


def _load_synonyms(path=None):
    """Returns dict variant_lowercase -> canonical_lowercase."""
    path = path or config.SYNONYMS_CSV
    mapping = {}
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            variant = row["variant"].strip().lower()
            canonical = row["canonical"].strip().lower()
            if variant:
                mapping[variant] = canonical
    return mapping


# --- Descriptor family mapping --------------------------------------------

OFF_NOTE_FAMILIES = [
    "beany", "green/grassy", "fatty/rancid", "mushroom/earthy", "sulfurous",
    "bitter/astringent", "other off-note",
]
MEAT_FAMILIES = ["meaty", "roasted", "fatty/fried", "sweet/caramel", "other meat note"]


def map_descriptor_to_family(descriptor, descriptor_map, is_meat_side):
    """
    Map a free-text descriptor to a fixed family. Tries each descriptor_map
    keyword as a substring match (longest keywords first, so more specific
    phrases win over generic ones). Falls back to "other off-note" /
    "other meat note" if nothing matches.
    """
    text = (descriptor or "").strip().lower()
    fallback = "other meat note" if is_meat_side else "other off-note"
    if not text:
        return fallback
    for keyword, family in descriptor_map:
        if keyword in text:
            # don't let an off-note keyword win on the meat side or vice versa
            if is_meat_side and family not in MEAT_FAMILIES:
                continue
            if not is_meat_side and family not in OFF_NOTE_FAMILIES:
                continue
            return family
    return fallback


# --- Molecule name normalization + synonym merge --------------------------


def normalize_molecule_name(name):
    """Lowercase, strip, collapse internal whitespace/commas for matching."""
    if not name:
        return ""
    text = name.strip().lower()
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def canonical_molecule_name(name, synonyms):
    """Normalize, then apply the synonyms table. Returns the canonical lowercase name."""
    norm = normalize_molecule_name(name)
    return synonyms.get(norm, norm)


def is_generic_term(name, generic_terms):
    norm = normalize_molecule_name(name)
    return norm in generic_terms


# --- Dosage extraction ------------------------------------------------------

DOSAGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*g\s*/\s*kg|\d+\s*:\s*\d+(?:\.\d+)?\s*ratio|\d+\s*:\s*\d+)",
    re.IGNORECASE,
)


def extract_stated_dose(quote):
    """Return the first dosage/ratio substring found in a quote, or None."""
    if not quote:
        return None
    match = DOSAGE_PATTERN.search(quote)
    return match.group(0).strip() if match else None


# --- OAV computation --------------------------------------------------------

_NUMBER_UNIT_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z/%µμ]+)\s*$")


def _parse_clean_number_with_unit(text):
    """
    Parse text as EXACTLY one number followed by one unit, nothing else
    (no ranges, no 'trace levels', no parentheticals). Returns (value, unit)
    or None if the text isn't a single clean number+unit.
    """
    if not text:
        return None
    match = _NUMBER_UNIT_PATTERN.match(text.strip())
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).strip().lower()
    return value, unit


def compute_oav(concentration_text, threshold_text):
    """
    Compute concentration / threshold only when both are clean, single
    number+unit values in the SAME unit. Never invent or guess thresholds.
    Returns the OAV float, or None.

    Rejects concentration_text == threshold_text (same raw string, even
    before parsing): this pattern has been observed to come from extraction
    errors (the model copying one value into both fields, e.g. when a quote
    states a threshold but no concentration), not a genuine OAV=1 finding.
    A real OAV of exactly 1.0 from two independently reported numbers is
    possible but rare; this guard trades a small amount of recall for
    ruling out the specific, confirmed failure mode seen in this corpus.
    """
    if concentration_text is not None and threshold_text is not None:
        if concentration_text.strip().lower() == threshold_text.strip().lower() and concentration_text.strip():
            return None

    conc = _parse_clean_number_with_unit(concentration_text)
    thresh = _parse_clean_number_with_unit(threshold_text)
    if conc is None or thresh is None:
        return None
    conc_value, conc_unit = conc
    thresh_value, thresh_unit = thresh
    if conc_unit != thresh_unit or thresh_value == 0:
        return None
    return round(conc_value / thresh_value, 3)


# --- Pages as integers -------------------------------------------------------


def format_page(page):
    """Render a page value as an integer string ('9'), not '9.0'. Returns None if unparseable."""
    if page is None or page == "":
        return None
    try:
        return int(float(page))
    except (TypeError, ValueError):
        return None


# --- Protein / food scope -----------------------------------------------------

PROTEIN_SYNONYMS = {
    "pea": ["pea", "pisum"],
    "soy": ["soy", "soybean", "glycine max", "textured soy protein", "texturized soy", "tvp"],
    "faba": ["faba", "fava", "vicia faba"],
}

GENERAL_PROTEIN_KEYWORDS = ["plant protein", "plant-based protein", "alternative protein"]

# Known Maillard/meaty-flavor precursor substances (brief section 2.4) that
# must never appear as "missing meat notes" even if a row was mislabeled
# role=meat_marker by extraction. Glutamic acid is deliberately NOT in this
# set: in the extracted data it is reported as a taste-active end product
# of the Maillard reaction (contributing umami/meatiness directly), not as
# a reaction input, so it correctly stays a missing-note candidate when
# tagged role=meat_marker.
KNOWN_PRECURSOR_SUBSTANCES = {
    "cysteine", "methionine", "xylose", "glucose", "ribose", "thiamine",
}


def food_scope(food_text, protein):
    """
    Returns "protein-specific" if food_text matches the protein's synonyms,
    "general" if it's a generic "plant protein" mention, or None if it
    matches neither (caller should exclude the row).
    """
    text = (food_text or "").strip().lower()
    if not text:
        return None
    keywords = PROTEIN_SYNONYMS.get(protein, [protein])
    if any(kw in text for kw in keywords):
        return "protein-specific"
    if any(kw in text for kw in GENERAL_PROTEIN_KEYWORDS):
        return "general"
    return None


# --- Evidence record building -------------------------------------------------


def _evidence_id(row):
    """Stable id for an evidence row, derived from its content (deterministic across runs)."""
    import hashlib
    key = f"{row.get('file')}|{row.get('page')}|{row.get('compound')}|{row.get('quote')}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def build_evidence_record(row, papers_by_title):
    page = format_page(row.get("page"))
    file = row.get("file")
    paper = papers_by_title.get(file) if papers_by_title else None
    paper_grade = None
    if paper and paper.get("grade") not in (None, ""):
        try:
            paper_grade = int(float(paper["grade"]))
        except (TypeError, ValueError):
            paper_grade = None
    return {
        "id": _evidence_id(row),
        "quote": row.get("quote", ""),
        "file": file,
        "page": page,
        "origin": row.get("origin", config.ORIGIN_MODEL_EXTRACTED),
        "confidence": float(row.get("confidence", 0) or 0),
        "paper_grade": paper_grade,
    }


def _grade_weight(file_name, papers_by_title):
    paper = papers_by_title.get(file_name) if papers_by_title else None
    if paper is None or paper.get("grade") in (None, ""):
        return config.DEFAULT_GRADE_WEIGHT
    try:
        grade = float(paper["grade"])
    except (TypeError, ValueError):
        return config.DEFAULT_GRADE_WEIGHT
    return grade / config.GRADE_WEIGHT_DIVISOR


def _evidence_score(rows_for_molecule, papers_by_title):
    """evidence_score = sum over distinct papers (grade_weight * mean confidence)."""
    rows_by_paper = defaultdict(list)
    for r in rows_for_molecule:
        rows_by_paper[r.get("file")].append(r)

    score = 0.0
    for file_name, paper_rows in rows_by_paper.items():
        confidences = [float(r.get("confidence", 0) or 0) for r in paper_rows]
        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        score += _grade_weight(file_name, papers_by_title) * mean_confidence

    return round(score, 3), len(rows_by_paper)


# --- Main molecule-grouping logic --------------------------------------------


def _group_molecules(rows, descriptor_map, synonyms, generic_terms, is_meat_side, papers_by_title,
                      evidence_store, protein=None):
    """
    Shared logic for both off-notes and missing-notes: group rows by
    canonical molecule name, split out generic class terms, map descriptors
    to families, compute evidence_score/n_papers/oav, and collect evidence ids.

    Returns (molecule_list, compound_classes_set).
    """
    molecule_rows = defaultdict(list)
    classes_seen = set()

    for row in rows:
        compound = row.get("compound", "")
        if not compound or not compound.strip():
            continue

        if is_generic_term(compound, generic_terms):
            classes_seen.add(normalize_molecule_name(compound))
            continue

        canonical = canonical_molecule_name(compound, synonyms)
        if not canonical:
            continue

        molecule_rows[canonical].append(row)

    molecules = []
    for canonical_name, group_rows in molecule_rows.items():
        # Use the first row's original-case compound name for display, but
        # the family is derived from the descriptor of each row (usually
        # consistent within a group; take the most common one).
        family_counts = defaultdict(int)
        for r in group_rows:
            family = map_descriptor_to_family(r.get("descriptor", ""), descriptor_map, is_meat_side)
            family_counts[family] += 1
        family = max(family_counts.items(), key=lambda kv: kv[1])[0]

        evidence_score, n_papers = _evidence_score(group_rows, papers_by_title)

        evidence_ids = []
        seen_evidence_ids = set()
        for r in group_rows:
            record = build_evidence_record(r, papers_by_title)
            evidence_store[record["id"]] = record
            if record["id"] not in seen_evidence_ids:
                seen_evidence_ids.add(record["id"])
                evidence_ids.append(record["id"])

        pubchem_cid = None
        for r in group_rows:
            cid = r.get("pubchem_cid")
            if cid not in (None, "", "None"):
                try:
                    pubchem_cid = int(float(cid))
                    break
                except (TypeError, ValueError):
                    continue

        oav = None
        for r in group_rows:
            computed = compute_oav(r.get("concentration"), r.get("threshold"))
            if computed is not None:
                oav = computed
                break

        display_name = group_rows[0].get("compound", canonical_name).strip()

        entry = {
            "molecule": display_name,
            "pubchem_cid": pubchem_cid,
            "family": family,
            "evidence_score": evidence_score,
            "n_papers": n_papers,
            "evidence_ids": evidence_ids,
        }
        if is_meat_side:
            molecules.append(entry)
        else:
            scopes = {food_scope(r.get("food", ""), protein) for r in group_rows}
            scope = "protein-specific" if "protein-specific" in scopes else "general"
            entry["oav"] = oav
            entry["scope"] = scope
            molecules.append(entry)

    molecules.sort(key=lambda m: m["evidence_score"], reverse=True)
    return molecules, classes_seen


def build_off_notes_and_missing_notes(protein, meat_target, facts_rows, papers_by_title, evidence_store):
    """
    Build the off_notes and missing_notes lists per the v2 schema.

    - Precursor-role rows (role == "precursor") are excluded from
      missing_notes entirely (they move to the levers side, see
      build_levers()).
    - Off-note rows are filtered to the selected protein's scope
      (protein-specific or general); rows matching neither are dropped.
    - Generic class terms are split out into compound_classes.
    """
    descriptor_map = _load_descriptor_map()
    synonyms = _load_synonyms()
    generic_terms = _load_generic_terms()

    # --- off-notes: role=off_note, scoped to the protein ---
    off_note_rows = []
    for r in facts_rows:
        if r.get("role") != "off_note":
            continue
        scope = food_scope(r.get("food", ""), protein)
        if scope is None:
            continue
        off_note_rows.append(r)

    off_notes, off_note_classes = _group_molecules(
        off_note_rows, descriptor_map, synonyms, generic_terms,
        is_meat_side=False, papers_by_title=papers_by_title,
        evidence_store=evidence_store, protein=protein,
    )

    # --- missing notes: role=meat_marker, excluding anything also a precursor role ---
    # (gap.py's existing meat-target relevance filter is reused: exclude rows
    # explicitly naming a different specific meat target.)
    from core import gap as gap_module

    other_meat_keywords = [
        kw for target, kws in gap_module.MEAT_TARGET_KEYWORDS.items() if target != meat_target for kw in kws
    ]

    def _is_relevant_meat_marker(row):
        if row.get("role") != "meat_marker":
            return False
        compound_norm = normalize_molecule_name(row.get("compound", ""))
        if compound_norm in KNOWN_PRECURSOR_SUBSTANCES:
            # Precursor substances (brief 2.4) must never appear as missing
            # meat notes, even if a row was mislabeled role=meat_marker.
            return False
        food = f"{row.get('food', '')} {row.get('preparation', '')}".lower()
        if any(kw in food for kw in other_meat_keywords):
            return False
        return True

    meat_marker_rows = [r for r in facts_rows if _is_relevant_meat_marker(r)]

    missing_notes_molecules, meat_classes = _group_molecules(
        meat_marker_rows, descriptor_map, synonyms, generic_terms,
        is_meat_side=True, papers_by_title=papers_by_title,
        evidence_store=evidence_store,
    )

    # Missing = meat molecules whose canonical name does not already appear
    # as an off-note molecule for this protein (i.e. the plant base already
    # has it, so it's not "missing").
    off_note_canonical_names = {canonical_molecule_name(m["molecule"], synonyms) for m in off_notes}
    missing_notes = [
        m for m in missing_notes_molecules
        if canonical_molecule_name(m["molecule"], synonyms) not in off_note_canonical_names
    ]
    # missing_notes schema has no "scope"/"oav" keys
    for m in missing_notes:
        m.pop("scope", None)
        m.pop("oav", None)

    compound_classes = sorted(off_note_classes | meat_classes)

    return off_notes, missing_notes, compound_classes, meat_marker_rows


# --- Levers ------------------------------------------------------------------


def build_levers(ranked_levers_raw, unmapped_count, evidence_store, papers_by_title,
                  off_note_molecules, missing_note_molecules):
    """
    Convert core.rank's raw ranked lever dicts (which carry "matched_facts")
    into the v2 Lever schema: adds "removes_or_masks", "adds", "stated_dose",
    and flattened evidence_ids, with pages as integers.

    "removes_or_masks" / "adds" are restricted to molecule names that
    actually appear in the already-cleaned off_notes / missing_notes lists
    (i.e. specific molecules only, generic class terms excluded, synonyms
    already merged to their canonical display name).
    """
    synonyms = _load_synonyms()
    off_note_names = {canonical_molecule_name(m["molecule"], synonyms) for m in off_note_molecules}
    missing_note_names = {canonical_molecule_name(m["molecule"], synonyms) for m in missing_note_molecules}

    levers = []
    for rank_idx, raw in enumerate(ranked_levers_raw, 1):
        matched_rows = raw.get("matched_facts", [])

        removes_or_masks = set()
        adds = set()
        stated_dose = None
        evidence_ids = []
        seen_evidence_ids = set()

        for row in matched_rows:
            record = build_evidence_record(row, papers_by_title)
            evidence_store[record["id"]] = record
            if record["id"] not in seen_evidence_ids:
                seen_evidence_ids.add(record["id"])
                evidence_ids.append(record["id"])

            compound = canonical_molecule_name(row.get("compound", ""), synonyms)
            role = row.get("role")
            if role in ("off_note",) and compound in off_note_names:
                removes_or_masks.add(row.get("compound").strip())
            elif role in ("meat_marker", "precursor") and compound in missing_note_names:
                adds.add(row.get("compound").strip())
            elif role == "masker" and compound in off_note_names:
                removes_or_masks.add(row.get("compound").strip())

            if stated_dose is None:
                dose_text = extract_stated_dose(row.get("quote", ""))
                if dose_text:
                    stated_dose = {"text": dose_text, "evidence_id": record["id"]}

        kind = raw["type"]
        if kind not in ("ingredient", "process", "sourcing"):
            kind = "process"
        # A lever whose matched rows are mostly role=precursor is tagged "precursor" kind.
        precursor_rows = [r for r in matched_rows if r.get("role") == "precursor"]
        if precursor_rows and len(precursor_rows) >= len(matched_rows) / 2:
            kind = "precursor"

        levers.append({
            "rank": rank_idx,
            "name": raw["lever"],
            "kind": kind,
            "score": raw["score"],
            "n_papers": raw["n_papers"],
            "cost_tier": raw["cost_tier"],
            "clean_label": raw["clean_label"],
            "cost_origin": config.ORIGIN_ASSUMED,
            "removes_or_masks": sorted(removes_or_masks),
            "adds": sorted(adds),
            "stated_dose": stated_dose,
            "evidence_ids": evidence_ids,
            "co2_impact": predict_co2_impact(kind, raw["cost_tier"]),
        })

    return levers


# --- Family profile (for the radar chart) ------------------------------------


def build_family_profile(off_notes, missing_notes):
    """
    family_profile: one row per (family, side), evidence_score summed across
    molecules in that family on that side.
    """
    plant_scores = defaultdict(float)
    for m in off_notes:
        plant_scores[m["family"]] += m["evidence_score"]

    meat_scores = defaultdict(float)
    for m in missing_notes:
        meat_scores[m["family"]] += m["evidence_score"]

    profile = []
    for family in OFF_NOTE_FAMILIES:
        if plant_scores.get(family):
            profile.append({"family": family, "side": "plant off-note", "evidence_score": round(plant_scores[family], 3)})
    for family in MEAT_FAMILIES:
        if meat_scores.get(family):
            profile.append({"family": family, "side": "meat target", "evidence_score": round(meat_scores[family], 3)})

    return profile


# --- Formulas + limits --------------------------------------------------------


# --- CO2 impact (predicted, not sourced from the literature) ---------------
#
# The corpus has no per-lever carbon-footprint data (papers only mention
# global animal-vs-plant agriculture statistics, not lever-specific
# figures), so this is NOT extracted from papers. It is a simple, team-made
# heuristic for illustration purposes only, labeled origin="predicted" (not
# "assumed", which is reserved for the cost_tier/clean_label catalog
# columns) so the UI and the pitch can caveat it clearly as a prediction,
# not a sourced fact.
#
# Heuristic: a lever's relative CO2 footprint is driven mostly by whether it
# is a sourcing/breeding change (lowest: happens once upstream, no added
# processing), a simple ingredient/precursor addition (low-medium: some
# extra agriculture/transport), or a process step (medium-high: added
# energy use in manufacturing) -- scaled further by its assumed cost tier,
# used here as a rough proxy for resource/energy intensity.
_CO2_BASE_BY_KIND = {
    "sourcing": 10,
    "precursor": 25,
    "ingredient": 35,
    "process": 55,
}
_CO2_MULTIPLIER_BY_COST_TIER = {"low": 1.0, "medium": 1.4, "high": 1.9}


def predict_co2_impact(kind, cost_tier):
    """
    Returns {"score": int 0-100, "rationale": str, "origin": "predicted"}.
    Higher score = higher relative predicted CO2 footprint. This is a
    team heuristic for the pitch, not a literature-sourced number.
    """
    base = _CO2_BASE_BY_KIND.get(kind, 35)
    multiplier = _CO2_MULTIPLIER_BY_COST_TIER.get(cost_tier, 1.0)
    score = min(100, round(base * multiplier))

    kind_phrase = {
        "sourcing": "a one-time upstream sourcing/breeding change",
        "precursor": "a simple precursor addition",
        "ingredient": "an added ingredient",
        "process": "an added processing step",
    }.get(kind, "this lever")

    band = "low" if score < 35 else "medium" if score < 75 else "high"
    rationale = (
        f"Predicted: {kind_phrase} with {cost_tier} assumed cost tier "
        f"is estimated as {band} relative footprint."
    )

    return {"score": score, "rationale": rationale, "origin": config.ORIGIN_PREDICTED}


def build_formulas():
    return {
        "evidence_score": "evidence_score(molecule) = sum over distinct papers (grade_weight * mean confidence); grade_weight = grade/3, default 0.5 if ungraded",
        "lever_score": "score = evidence * (1 + 0.5 * n_targeted_gaps) - 0.3 * cost_penalty - 0.3 * clean_label_penalty",
        "cost_penalty": "low=0, medium=0.5, high=1",
        "clean_label_penalty": "0 (consumer-friendly) = 0, 1 (neutral) = 0.5, 2 (additive/E-number) = 1",
        "oav": "oav = concentration / threshold, only computed when both are sourced, single clean numbers in the same unit; otherwise null",
    }


def build_limits(rejection_rate=None, gold_precision=None):
    limits = [
        "Literature-based prediction, not a tasted or proven result.",
        "Costs and clean-label scores in the lever catalog are assumed by the team, not measured.",
        "Cooked meat evidence is pooled across all cooking methods found in the corpus (no single cooking state is isolated).",
        "Corpus coverage is uneven: some protein/meat pairs have few or no directly matching papers.",
    ]
    if rejection_rate is not None:
        limits.append(f"Extraction rejection rate for the last live run: {rejection_rate * 100:.1f}%.")
    if gold_precision is not None:
        limits.append(f"Gold-set extraction precision: {gold_precision * 100:.1f}%.")
    else:
        limits.append("Gold-set precision: pending (gold set not yet evaluated for this build).")
    return limits


# --- Top-level entry point ----------------------------------------------------


def present(protein, meat_target, pipeline_result, facts_rows, papers_by_title,
            source="precomputed", generated_at=None):
    """
    Build the full v2 Analysis response (see web/src/types.ts) from raw
    pipeline output.

    pipeline_result: the dict returned by core.pipeline.run/run_live, i.e.
        {"missing_notes": [...from gap.py, pre-v2...], "off_notes": [...], "ranked_levers": [...],
         "unmapped_levers": [...], "explanation": {...}, "rejection_stats": {...}}
        NOTE: present() recomputes off_notes/missing_notes from facts_rows
        directly (v2 grouping logic), it does not reuse pipeline_result's
        gap.py-shaped lists; it only reuses ranked_levers, unmapped_levers,
        explanation, rejection_stats.
    """
    import datetime

    evidence_store = {}

    off_notes, missing_notes, compound_classes, meat_marker_rows = build_off_notes_and_missing_notes(
        protein, meat_target, facts_rows, papers_by_title, evidence_store,
    )

    levers = build_levers(
        pipeline_result.get("ranked_levers", []),
        len(pipeline_result.get("unmapped_levers", [])),
        evidence_store, papers_by_title,
        off_notes, missing_notes,
    )

    family_profile = build_family_profile(off_notes, missing_notes)

    rejection_stats = pipeline_result.get("rejection_stats") or {}
    rejection_rate = rejection_stats.get("rejection_rate")

    explanation = pipeline_result.get("explanation", {"text": "", "citations_pruned": False})

    # Scope KPIs to facts actually used in this scenario's analysis (off-note
    # rows in scope for this protein + meat-marker rows relevant to this
    # target), not the full global facts.csv.
    scenario_relevant_rows = meat_marker_rows + [
        r for r in facts_rows
        if r.get("role") == "off_note" and food_scope(r.get("food", ""), protein) is not None
    ]
    n_papers_used = len({r.get("file") for r in scenario_relevant_rows if r.get("file")})

    kpis = {
        "n_papers_used": n_papers_used,
        "n_verified_facts": len(scenario_relevant_rows),
        "rejection_rate": rejection_rate if rejection_rate is not None else 0.0,
        "gold_precision": None,
        "n_offnote_molecules": len(off_notes),
        "n_levers_ranked": len(levers),
    }

    return {
        "scenario": {
            "protein": protein,
            "target": meat_target,
            "source": source,
            "generated_at": generated_at or datetime.datetime.utcnow().isoformat() + "Z",
        },
        "kpis": kpis,
        "off_notes": off_notes,
        "missing_notes": missing_notes,
        "compound_classes": compound_classes,
        "family_profile": family_profile,
        "levers": levers,
        "unmapped_lever_mentions": len(pipeline_result.get("unmapped_levers", [])),
        "explanation": {
            "text": explanation.get("text", ""),
            "citations_valid": not explanation.get("citations_pruned", False),
        },
        "formulas": build_formulas(),
        "limits": build_limits(rejection_rate=rejection_rate, gold_precision=None),
        "evidence": evidence_store,
    }
