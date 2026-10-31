"""
FlavorGap API (FastAPI).

Routes:
    GET  /api/options                          -> proteins and targets
    GET  /api/analysis?protein=&target=         -> precomputed scenario, present.py applied, NO Bedrock calls
    POST /api/analysis/run                      -> live pipeline rerun (throttled, cached), saves scenario JSON
    GET  /api/evidence/{evidence_id}             -> full evidence record

In production (after `npm run build` in web/), this app also serves the
built frontend from web/dist/ so the whole demo is one command:

    uvicorn api.main:app --port 8000

Run for local dev (frontend on Vite, backend here) with CORS enabled for
the Vite dev server origin.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import config, facts as facts_module, pipeline, present

app = FastAPI(title="FlavorGap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server default
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory evidence index: evidence_id -> evidence record. Populated as
# scenarios are presented (lazily, on first request for each scenario).
# Evidence ids are content-derived hashes (see present._evidence_id), so
# they are stable and safe to accumulate across scenarios without collision.
_evidence_index: dict = {}


def _load_papers_by_title():
    if not os.path.exists(config.PAPERS_CSV):
        return {}
    with open(config.PAPERS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        return {row["_document_title"]: row for row in reader}


def _validate_scenario(protein: str, target: str):
    if protein not in config.PROTEINS:
        raise HTTPException(status_code=400, detail=f"Unknown protein '{protein}'. Valid: {config.PROTEINS}")
    if target not in config.MEAT_TARGETS:
        raise HTTPException(status_code=400, detail=f"Unknown target '{target}'. Valid: {config.MEAT_TARGETS}")


def _build_analysis(protein: str, target: str, force_live: bool, top_n_chunks=None, persist=False):
    pipeline_result = pipeline.run(
        protein, target, force_live=force_live, top_n_chunks=top_n_chunks, persist=persist,
    )
    source = "live" if not pipeline_result.get("loaded_from_cache_file") else "precomputed"

    all_facts = facts_module.load_facts()
    papers_by_title = _load_papers_by_title()

    result = present.present(protein, target, pipeline_result, all_facts, papers_by_title, source=source)

    # Merge this scenario's evidence into the global index so
    # GET /api/evidence/{id} can find it regardless of which scenario it
    # originally came from.
    _evidence_index.update(result["evidence"])

    return result


# --- Routes ------------------------------------------------------------------


@app.get("/api/options")
def get_options():
    """Return the available proteins and meat targets for the UI's selectors."""
    return {"proteins": config.PROTEINS, "targets": config.MEAT_TARGETS}


@app.get("/api/analysis")
def get_analysis(protein: str = Query(...), target: str = Query(...)):
    """
    Load the precomputed scenario JSON, apply present.py, return the full
    Analysis schema. Makes NO Bedrock calls: if no precomputed scenario file
    exists yet, this returns 404 (use POST /api/analysis/run instead).
    """
    _validate_scenario(protein, target)

    scenario_file = pipeline.scenario_path(protein, target)
    if not os.path.exists(scenario_file):
        raise HTTPException(
            status_code=404,
            detail=f"No precomputed scenario for {protein} -> {target}. Use POST /api/analysis/run to generate it.",
        )

    result = _build_analysis(protein, target, force_live=False)
    return result


class RunAnalysisRequest(BaseModel):
    protein: str
    target: str


@app.post("/api/analysis/run")
def run_analysis(body: RunAnalysisRequest):
    """
    Rerun the live pipeline for this scenario (retrieve -> extract -> verify
    -> gap -> rank -> explain, throttled to ~1 Bedrock call/second and disk
    cached), save the updated scenario JSON to data/scenarios/, and return
    the same Analysis schema as GET /api/analysis.
    """
    _validate_scenario(body.protein, body.target)
    result = _build_analysis(body.protein, body.target, force_live=True, persist=True)
    return result


@app.get("/api/evidence/{evidence_id}")
def get_evidence(evidence_id: str):
    """Return the full evidence record (quote, file, page, origin, confidence, paper_grade) for an id."""
    record = _evidence_index.get(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown evidence id '{evidence_id}'.")
    return record


# --- Static frontend (production) --------------------------------------------

_WEB_DIST = os.path.join(config.BASE_DIR, "web", "dist")
if os.path.isdir(_WEB_DIST):
    app.mount("/", StaticFiles(directory=_WEB_DIST, html=True), name="web")
