// Single source of truth for colors used across the table, bar chart, radar
// chart, and chips, so the same family/origin always renders the same color.

export const FAMILY_COLORS: Record<string, string> = {
  // off-note families
  beany: "#a16207", // amber-700
  "green/grassy": "#16a34a", // green-600
  "fatty/rancid": "#b45309", // amber-800ish
  "mushroom/earthy": "#78350f", // brown
  sulfurous: "#ca8a04", // yellow-700
  "bitter/astringent": "#7c3aed", // violet-600
  "other off-note": "#64748b", // slate-500

  // meat families
  meaty: "#dc2626", // red-600
  roasted: "#c2410c", // orange-700
  "fatty/fried": "#ea580c", // orange-600
  "sweet/caramel": "#db2777", // pink-600
  "other meat note": "#475569", // slate-600
};

export function familyColor(family: string): string {
  return FAMILY_COLORS[family] ?? "#64748b";
}

export const ORIGIN_COLORS: Record<string, { bg: string; text: string }> = {
  sourced: { bg: "#dbeafe", text: "#1d4ed8" }, // blue
  "model-extracted": { bg: "#e0e7ff", text: "#4338ca" }, // indigo
  "sourced-computed": { bg: "#ccfbf1", text: "#0f766e" }, // teal
  assumed: { bg: "#ffedd5", text: "#c2410c" }, // orange
  synthetic: { bg: "#e5e7eb", text: "#4b5563" }, // grey
};

export function originColor(origin: string) {
  return ORIGIN_COLORS[origin] ?? ORIGIN_COLORS.synthetic;
}

export const CLEAN_LABEL_COLORS: Record<number, { bg: string; text: string; label: string }> = {
  0: { bg: "#dcfce7", text: "#15803d", label: "consumer-friendly" },
  1: { bg: "#e5e7eb", text: "#4b5563", label: "neutral" },
  2: { bg: "#ffedd5", text: "#c2410c", label: "additive" },
};

export const COST_TIER_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: "#dcfce7", text: "#15803d" },
  medium: { bg: "#fef9c3", text: "#854d0e" },
  high: { bg: "#fee2e2", text: "#b91c1c" },
};
