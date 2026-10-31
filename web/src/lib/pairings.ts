import type { Analysis, Lever, OffNote } from "../types";

export type Pairing = {
  rank: number;
  offNote: OffNote;
  lever: Lever | null; // null if no ranked lever addresses this molecule
};

/**
 * Pair each off-note molecule with the best-ranked lever that removes/masks
 * it (levers are already sorted by rank, so the first match is the best).
 * Off-notes are ordered by evidence_score (strongest, best-supported
 * off-notes first), matching how core/present.py already sorts them.
 */
export function buildTopPairings(analysis: Analysis, limit = 5): Pairing[] {
  const leversByMolecule = new Map<string, Lever>();
  for (const lever of analysis.levers) {
    for (const molecule of lever.removes_or_masks) {
      const key = molecule.trim().toLowerCase();
      // levers are already rank-ordered, keep the first (best) match
      if (!leversByMolecule.has(key)) {
        leversByMolecule.set(key, lever);
      }
    }
  }

  const sortedOffNotes = [...analysis.off_notes].sort((a, b) => b.evidence_score - a.evidence_score);

  return sortedOffNotes.slice(0, limit).map((offNote, i) => ({
    rank: i + 1,
    offNote,
    lever: leversByMolecule.get(offNote.molecule.trim().toLowerCase()) ?? null,
  }));
}
