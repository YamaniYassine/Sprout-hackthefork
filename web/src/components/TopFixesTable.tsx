import type { Analysis } from "../types";
import { buildTopPairings } from "../lib/pairings";
import { familyColor } from "../theme";
import { EmptyState } from "./Skeleton";

function FamilyChip({ family }: { family: string }) {
  const color = familyColor(family);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {family}
    </span>
  );
}

function ImpactBar({ score, max }: { score: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (score / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 rounded-full bg-emerald-100 overflow-hidden">
        <div className="h-full bg-emerald-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-emerald-700 font-mono">{score.toFixed(2)}</span>
    </div>
  );
}

export default function TopFixesTable({ analysis }: { analysis: Analysis }) {
  const pairings = buildTopPairings(analysis, 5);
  const maxScore = Math.max(...pairings.map((p) => p.offNote.evidence_score), 1);

  if (pairings.length === 0) {
    return <EmptyState message="No off-note molecules found in the corpus for this scenario." />;
  }

  return (
    <div className="bg-white border border-emerald-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-emerald-100">
        <h2 className="text-lg font-bold text-emerald-900">Top 5 fixes</h2>
        <p className="text-sm text-emerald-700/80 mt-0.5">
          The strongest off-taste molecules found in the plant protein, and the best-supported
          plant-only additive or process to fix each one.
        </p>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="bg-emerald-50 text-emerald-800 text-left">
            <th className="px-5 py-2.5 font-semibold w-12">#</th>
            <th className="px-5 py-2.5 font-semibold">Off-taste molecule</th>
            <th className="px-5 py-2.5 font-semibold">Recommended additive / process</th>
            <th className="px-5 py-2.5 font-semibold">Impact</th>
          </tr>
        </thead>
        <tbody>
          {pairings.map(({ rank, offNote, lever }) => (
            <tr key={offNote.molecule} className="border-t border-emerald-100 hover:bg-emerald-50/50">
              <td className="px-5 py-3 font-bold text-emerald-700">{rank}</td>
              <td className="px-5 py-3">
                <div className="font-medium text-emerald-950">{offNote.molecule}</div>
                <div className="mt-1 flex items-center gap-2">
                  <FamilyChip family={offNote.family} />
                  <span className="text-xs text-emerald-600">{offNote.n_papers} paper(s)</span>
                  {offNote.scope === "general" && (
                    <span className="text-xs text-slate-400 italic">general plant protein</span>
                  )}
                </div>
              </td>
              <td className="px-5 py-3">
                {lever ? (
                  <>
                    <div className="font-medium text-emerald-950">{lever.name}</div>
                    <div className="text-xs text-emerald-600 mt-0.5 capitalize">
                      {lever.kind} &middot; {lever.cost_tier} cost &middot; {lever.n_papers} paper(s)
                    </div>
                  </>
                ) : (
                  <span className="text-slate-400 italic text-xs">No ranked lever found yet</span>
                )}
              </td>
              <td className="px-5 py-3">
                <ImpactBar score={offNote.evidence_score} max={maxScore} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
