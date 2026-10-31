"""
FlavorGap - Streamlit UI.

Run with: streamlit run app.py

Sidebar lets the user freely choose protein, meat target, cooking state, and
two filter toggles. Main area shows, in order: missing meat-like notes,
off-notes, ranked levers (with the scoring formula), cited explanation,
evidence panel, and a Limits box.
"""

import os

import streamlit as st

from core import config, pipeline

st.set_page_config(page_title="FlavorGap", layout="wide")

ORIGIN_BADGE = {
    config.ORIGIN_SOURCED: "🟢 sourced",
    config.ORIGIN_MODEL_EXTRACTED: "🔵 model-extracted",
    config.ORIGIN_ASSUMED: "🟠 assumed",
    config.ORIGIN_SYNTHETIC: "⚪ synthetic",
}


def origin_badge(origin):
    return ORIGIN_BADGE.get(origin, f"⚫ {origin}")


# --- Sidebar: user picks everything, nothing is forced ---
st.sidebar.title("FlavorGap")
st.sidebar.caption("Plant-based flavor gap analysis, literature-based.")

protein = st.sidebar.selectbox("Plant protein", config.PROTEINS, index=0)
meat_target = st.sidebar.selectbox("Meat target", config.MEAT_TARGETS, index=0)

st.sidebar.divider()
only_grade_2plus = st.sidebar.toggle("Only papers with grade >= 2", value=False)
exclude_e_numbers = st.sidebar.toggle("Exclude E-number levers", value=False)

st.sidebar.divider()
run_live = st.sidebar.button("Run live (ignore precomputed cache)")

min_grade = 2 if only_grade_2plus else None

st.title(f"{protein.capitalize()} -> {meat_target} (cooked meat, all cooking methods pooled)")

with st.spinner("Running analysis..."):
    result = pipeline.run(
        protein, meat_target,
        min_grade=min_grade, exclude_e_numbers=exclude_e_numbers,
        force_live=run_live,
    )

source_note = "precomputed scenario file" if result.get("loaded_from_cache_file") else "live pipeline run"
st.caption(f"Source: {source_note}")

# --- 1. Missing meat-like notes ---
st.header("1. Missing meat-like notes")
missing_notes = result["missing_notes"]
if not missing_notes:
    st.info("No evidence found in the corpus for this section.")
else:
    for m in missing_notes:
        with st.expander(f"{m['descriptor'].capitalize()}  —  {m['n_papers']} supporting paper(s)", expanded=True):
            st.write(f"Compounds: {', '.join(m['compounds'])}")
            st.write(f"Papers: {', '.join(m['papers'])}")
            st.caption(origin_badge(config.ORIGIN_MODEL_EXTRACTED))

# --- 2. Off-notes of the plant protein ---
st.header("2. Off-notes of the plant protein")
off_notes = result["off_notes"]
if not off_notes:
    st.info("No evidence found in the corpus for this section.")
else:
    for o in off_notes:
        with st.expander(f"{o['descriptor'].capitalize()}  —  {o['n_papers']} supporting paper(s)", expanded=True):
            st.write(f"Compounds: {', '.join(o['compounds'])}")
            st.write(f"Papers: {', '.join(o['papers'])}")
            st.caption(origin_badge(config.ORIGIN_MODEL_EXTRACTED))

# --- 3. Ranked plant-only levers ---
st.header("3. Ranked plant-only levers")
ranked_levers = result["ranked_levers"]
unmapped_levers = result.get("unmapped_levers", [])

if not ranked_levers:
    st.info("No ranked levers for this scenario yet.")
else:
    table_rows = []
    for i, lever in enumerate(ranked_levers, 1):
        table_rows.append({
            "rank": i,
            "lever": lever["lever"],
            "type": lever["type"],
            "score": lever["score"],
            "# papers": lever["n_papers"],
            "cost tier": lever["cost_tier"],
            "clean-label": lever["clean_label"],
            "confidence": lever["mean_confidence"],
        })
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    st.caption(f"{origin_badge(config.ORIGIN_ASSUMED)} for cost tier / clean-label columns  |  "
               f"{origin_badge(config.ORIGIN_MODEL_EXTRACTED)} for evidence rows")

with st.expander("Scoring formula"):
    st.code(
        "evidence = sum over distinct supporting papers (grade_weight * mean confidence)\n"
        "  grade_weight = grade / 3   (default 0.5 if the paper is ungraded)\n\n"
        "score = evidence * (1 + 0.5 * n_targeted_gaps)\n"
        "        - 0.3 * cost_penalty\n"
        "        - 0.3 * clean_label_penalty\n\n"
        "cost_penalty:        low=0, medium=0.5, high=1\n"
        "clean_label_penalty: 0 (consumer-friendly), 0.5 (neutral), 1 (additive/E-number)",
        language="text",
    )

if unmapped_levers:
    with st.expander(f"Unmapped lever mentions ({len(unmapped_levers)}) — not ranked"):
        for u in unmapped_levers:
            st.write(f"- {u}")

# --- 4. Explanation with citations ---
st.header("4. Explanation")
explanation = result["explanation"]
st.write(explanation["text"])
if explanation.get("citations_pruned"):
    st.warning("Some citations in the raw model output could not be verified and were removed.")
st.caption(f"{explanation['word_count']} words  |  {origin_badge(config.ORIGIN_MODEL_EXTRACTED)}")

# --- 5. Evidence panel ---
st.header("5. Evidence panel")
all_evidence_rows = []
for m in missing_notes:
    all_evidence_rows.extend(m["rows"])
for o in off_notes:
    all_evidence_rows.extend(o["rows"])
for lever in ranked_levers:
    all_evidence_rows.extend(lever.get("matched_facts", []))

seen = set()
unique_rows = []
for r in all_evidence_rows:
    key = (r.get("file"), r.get("page"), r.get("compound"), r.get("quote"))
    if key in seen:
        continue
    seen.add(key)
    unique_rows.append(r)

if not unique_rows:
    st.info("No evidence rows to display.")
else:
    for r in unique_rows:
        label = f"{r.get('compound')} ({r.get('descriptor')}) — {r.get('file')} p.{r.get('page')}"
        with st.expander(label):
            st.write(f"**Quote:** \u201c{r.get('quote')}\u201d")
            st.write(f"**File:** {r.get('file')}")
            st.write(f"**Page:** {r.get('page')}")
            st.write(f"**Role:** {r.get('role')}  |  **Confidence:** {r.get('confidence')}")
            st.caption(origin_badge(r.get("origin", config.ORIGIN_MODEL_EXTRACTED)))

# --- 6. Limits box ---
st.header("6. Limits")
rejection_stats = result.get("rejection_stats")
with st.container(border=True):
    st.markdown("""
- This is a **literature-based prediction**, not a tasted or proven result.
- Cost tiers and clean-label scores in the lever catalog are **assumed** by the team, not measured.
- Results depend on the papers available in the corpus; absence of a note or lever here does not mean
  the literature doesn't have it, only that it wasn't found by this tool's queries.
""")
    if rejection_stats:
        st.write(
            f"Extraction rejection rate for this run: **{rejection_stats['rejection_rate'] * 100:.1f}%** "
            f"({rejection_stats['rejected']}/{rejection_stats['raw_rows']} rows rejected by deterministic checks)."
        )
    else:
        st.write("Rejection-rate stats are only available after a live pipeline run (not from precomputed cache).")
