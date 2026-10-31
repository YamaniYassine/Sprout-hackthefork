// Single source of truth for colors used across the table, bar chart, radar
// chart, and chips, so the same family/origin always renders the same color.
// Overall palette is green-forward (plant-based product), per product direction.

export const BRAND = {
  50: "#f0fdf4",
  100: "#dcfce7",
  200: "#bbf7d0",
  300: "#86efac",
  400: "#4ade80",
  500: "#22c55e",
  600: "#16a34a",
  700: "#15803d",
  800: "#166534",
  900: "#14532d",
};

export const FAMILY_COLORS: Record<string, string> = {
  // off-note families (green-forward palette, varied by hue/lightness for distinction)
  beany: "#854d0e", // amber-800
  "green/grassy": "#16a34a", // brand green-600
  "fatty/rancid": "#a16207", // amber-700
  "mushroom/earthy": "#57534e", // stone-600
  sulfurous: "#ca8a04", // yellow-700
  "bitter/astringent": "#6d28d9", // violet-700
  "other off-note": "#6b7280", // gray-500

  // meat families
  meaty: "#b91c1c", // red-700
  roasted: "#c2410c", // orange-700
  "fatty/fried": "#ea580c", // orange-600
  "sweet/caramel": "#be185d", // pink-700
  "other meat note": "#44403c", // stone-700
};

export function familyColor(family: string): string {
  return FAMILY_COLORS[family] ?? "#64748b";
}

export const ORIGIN_COLORS: Record<string, { bg: string; text: string }> = {
  sourced: { bg: "#dbeafe", text: "#1d4ed8" }, // blue
  "model-extracted": { bg: "#e0e7ff", text: "#4338ca" }, // indigo
  "sourced-computed": { bg: "#ccfbf1", text: "#0f766e" }, // teal
  assumed: { bg: "#ffedd5", text: "#c2410c" }, // orange
  predicted: { bg: "#fae8ff", text: "#a21caf" }, // fuchsia -- distinct from assumed, signals "team estimate"
  synthetic: { bg: "#e5e7eb", text: "#4b5563" }, // grey
};

// CO2 impact score bands (0-100, higher = higher predicted relative footprint)
export function co2BandColor(score: number): { bg: string; text: string; label: string } {
  if (score < 35) return { bg: "#dcfce7", text: "#15803d", label: "low" };
  if (score < 75) return { bg: "#fef9c3", text: "#854d0e", label: "medium" };
  return { bg: "#fee2e2", text: "#b91c1c", label: "high" };
}

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
