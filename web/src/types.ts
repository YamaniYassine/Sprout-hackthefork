// Mirrors core/present.py's output shape (the FlavorGap v2 API response).
// Keep this file in sync with the Python side by hand; there is no codegen
// step for this hackathon build.

export type Origin =
  | "sourced"
  | "model-extracted"
  | "sourced-computed"
  | "assumed"
  | "predicted"
  | "synthetic";

export type Evidence = {
  id: string;
  quote: string;
  file: string;
  page: number | null;
  origin: Origin;
  confidence: number;
  paper_grade: number | null;
};

export type OffNote = {
  molecule: string;
  pubchem_cid: number | null;
  family: string;
  evidence_score: number;
  n_papers: number;
  oav: number | null;
  scope: "protein-specific" | "general";
  evidence_ids: string[];
};

export type MissingNote = {
  molecule: string;
  pubchem_cid: number | null;
  family: string;
  evidence_score: number;
  n_papers: number;
  evidence_ids: string[];
};

export type LeverKind = "ingredient" | "process" | "sourcing" | "precursor";

export type Co2Impact = {
  score: number; // 0-100, higher = higher predicted relative footprint
  rationale: string;
  origin: "predicted";
};

export type Lever = {
  rank: number;
  name: string;
  kind: LeverKind;
  score: number;
  n_papers: number;
  cost_tier: "low" | "medium" | "high";
  clean_label: 0 | 1 | 2;
  cost_origin: "assumed";
  removes_or_masks: string[];
  adds: string[];
  stated_dose: { text: string; evidence_id: string } | null;
  evidence_ids: string[];
  co2_impact: Co2Impact;
};

export type FamilyProfileRow = {
  family: string;
  side: "plant off-note" | "meat target";
  evidence_score: number;
};

export type Analysis = {
  scenario: {
    protein: string;
    target: string;
    source: "precomputed" | "live";
    generated_at: string;
  };
  kpis: {
    n_papers_used: number;
    n_verified_facts: number;
    rejection_rate: number;
    gold_precision: number | null;
    n_offnote_molecules: number;
    n_levers_ranked: number;
  };
  off_notes: OffNote[];
  missing_notes: MissingNote[];
  compound_classes: string[];
  family_profile: FamilyProfileRow[];
  levers: Lever[];
  unmapped_lever_mentions: number;
  explanation: { text: string; citations_valid: boolean };
  formulas: Record<string, string>;
  limits: string[];
  evidence: Record<string, Evidence>;
};

export type Options = {
  proteins: string[];
  targets: string[];
};
