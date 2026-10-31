"""
scripts/build_scenarios.py (v2)

Runs the full pipeline for all 6 scenarios (3 proteins x 2 meat targets, no
cooking state) and saves data/scenarios/<protein>__<target>.json. The API's
GET /api/analysis route loads these files directly (no Bedrock calls); the
POST /api/analysis/run route reruns live and overwrites the file.

Run once after facts.csv has reasonable coverage. Safe to re-run: it will
reuse cached Bedrock calls and only append genuinely new facts.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config, pipeline


def build_all_scenarios(top_n_chunks=None):
    os.makedirs(config.SCENARIOS_DIR, exist_ok=True)

    for scenario in config.DEMO_SCENARIOS:
        protein = scenario["protein"]
        meat_target = scenario["meat_target"]
        print(f"Building scenario: {protein} -> {meat_target}")

        result = pipeline.run_live(protein, meat_target, top_n_chunks=top_n_chunks)
        path = pipeline.save_scenario(protein, meat_target, result)

        print(f"  -> saved {path}")
        print(f"  rejection_stats: {result['rejection_stats']}")
        print(f"  ranked_levers: {len(result['ranked_levers'])}  unmapped: {len(result['unmapped_levers'])}")
        print()


if __name__ == "__main__":
    build_all_scenarios()
