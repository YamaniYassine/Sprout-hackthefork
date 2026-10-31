"""
Central configuration for FlavorGap.

Hard constraints (see project brief):
- AWS region us-east-1 only.
- Credentials come from the environment. Never put keys/tokens here.
- Bedrock rate limit ~1 req/s for the whole app (enforced in core/bedrock.py).
- Model IDs below were picked by running, on 2026-10-31:
    aws bedrock list-inference-profiles --region us-east-1
    aws bedrock list-foundation-models --region us-east-1
  Both Haiku 4.5 and Sonnet 4.6 only support inference-profile invocation
  (inferenceTypesSupported == ["INFERENCE_PROFILE"]), so we use the "us."
  system-defined inference profile IDs, not raw foundation-model IDs.
"""

import os

# --- AWS ---
AWS_REGION = "us-east-1"

# --- Knowledge base (already built, do not change) ---
KNOWLEDGE_BASE_ID = "KFTWFAD3IC"
KB_NUMBER_OF_RESULTS = 10

# --- Bedrock models (inference profile IDs, verified ACTIVE in-account) ---
# Fast model: extraction of structured fact rows from retrieved chunks.
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
# Stronger model: writes the final cited explanation.
SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

# --- Bedrock throttle / retry ---
MIN_SECONDS_BETWEEN_CALLS = 1.1  # global throttle, ~1 req/s max for the whole app
MAX_RETRIES = 5
RETRY_BASE_DELAY_SECONDS = 2.0  # exponential backoff base on ThrottlingException

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
PDFS_DIR = os.path.join(DATA_DIR, "pdfs")
TEXT_DIR = os.path.join(DATA_DIR, "text")
SCENARIOS_DIR = os.path.join(DATA_DIR, "scenarios")

PAPERS_CSV = os.path.join(DATA_DIR, "papers.csv")
FACTS_CSV = os.path.join(DATA_DIR, "facts.csv")
REJECTED_CSV = os.path.join(DATA_DIR, "rejected.csv")
GOLD_CSV = os.path.join(DATA_DIR, "gold.csv")
LEVER_CATALOG_CSV = os.path.join(DATA_DIR, "lever_catalog.csv")

# --- S3 (data source behind the KB, informational only) ---
KB_S3_BUCKET = "foodie-kb"

# --- Scope filter: keywords that disqualify a lever/food/compound mention ---
# Out of scope: insects, animal-origin ingredients, animal feed.
BLOCKLIST_KEYWORDS = [
    "insect", "cricket", "mealworm", "locust", "silkworm",
    "animal feed", "feedstock for livestock", "livestock feed",
    "beef fat", "tallow", "lard", "gelatin", "gelatine",
    "egg white", "egg yolk", "whey", "casein", "milk protein",
    "meat extract", "bone broth", "fish sauce", "fish meal",
    "chicken fat", "pork fat", "animal fat",
]

# --- Ranking weights (kept here so the UI can display the formula) ---
GRADE_WEIGHT_DIVISOR = 3.0  # grade_weight = grade / 3
DEFAULT_GRADE_WEIGHT = 0.5  # used when a paper has no grade
GAP_COVERAGE_WEIGHT = 0.5  # score multiplier per targeted gap: (1 + 0.5 * n_targeted_gaps)
COST_PENALTY_WEIGHT = 0.3
CLEAN_LABEL_PENALTY_WEIGHT = 0.3

COST_TIER_PENALTY = {"low": 0.0, "medium": 0.5, "high": 1.0}
CLEAN_LABEL_PENALTY = {0: 0.0, 1: 0.5, 2: 1.0}

# --- Data origin labels shown in the UI ---
ORIGIN_SOURCED = "sourced"
ORIGIN_MODEL_EXTRACTED = "model-extracted"
ORIGIN_ASSUMED = "assumed"
ORIGIN_SYNTHETIC = "synthetic"

# --- Demo scenarios (3 proteins x 2 targets, grilled/cooked) ---
PROTEINS = ["pea", "soy", "faba"]
MEAT_TARGETS = ["beef burger", "chicken"]
DEMO_SCENARIOS = [
    {"protein": "pea", "meat_target": "beef burger", "cooking": "grilled"},
    {"protein": "soy", "meat_target": "chicken", "cooking": "grilled"},
    {"protein": "faba", "meat_target": "beef burger", "cooking": "grilled"},
]
