// Single source of truth for colors used across the table, bar chart, radar
// chart, and chips, so the same family/origin always renders the same color.
//
// Brand palette extracted from the Sprout pitch deck
// (~/Sprout_Hackathon_Pitch_final.pptx theme colors):
export const BRAND = {
  dark: "#12291E", // near-black forest green, headings/dark surfaces
  cream: "#F5F8F1", // off-white background
  sage: "#4B5D53", // muted secondary text
  paleSage: "#DEE3DC", // light borders/surfaces
  green: "#2F7A4A", // primary accent (buttons, links, eyebrow labels)
  lime: "#A6E07A", // highlight accent, used sparingly
  deepGreen: "#3D5246", // body text on light backgrounds
  mint: "#C9DCCD", // soft accent surfaces
  midSage: "#5A6E61", // captions/footnotes
  softSage: "#9DB5A4", // muted accents
};

export const FAMILY_COLORS: Record<string, string> = {
  // off-note families (kept visually distinct from each other and from the
  // meat-note families below; greens are reserved for the meat/fix side so
  // off-notes don't read as "good" -- warm/earthy tones here instead)
  beany: "#854d0e", // amber-800
  "green/grassy": "#6d8f35", // olive -- distinct from brand green, still plant-toned
  "fatty/rancid": "#a16207", // amber-700
  "mushroom/earthy": "#57534e", // stone-600
  sulfurous: "#ca8a04", // yellow-700
  "bitter/astringent": "#6d28d9", // violet-700
  "other off-note": "#6b7280", // gray-500

  // meat families (warm reds/oranges, the "target" side)
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
  if (score < 35) return { bg: BRAND.mint, text: BRAND.green, label: "low" };
  if (score < 75) return { bg: "#fef9c3", text: "#854d0e", label: "medium" };
  return { bg: "#fee2e2", text: "#b91c1c", label: "high" };
}

export function originColor(origin: string) {
  return ORIGIN_COLORS[origin] ?? ORIGIN_COLORS.synthetic;
}

export const CLEAN_LABEL_COLORS: Record<number, { bg: string; text: string; label: string }> = {
  0: { bg: BRAND.mint, text: BRAND.green, label: "consumer-friendly" },
  1: { bg: "#e5e7eb", text: "#4b5563", label: "neutral" },
  2: { bg: "#ffedd5", text: "#c2410c", label: "additive" },
};

export const COST_TIER_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: BRAND.mint, text: BRAND.green },
  medium: { bg: "#fef9c3", text: "#854d0e" },
  high: { bg: "#fee2e2", text: "#b91c1c" },
};
