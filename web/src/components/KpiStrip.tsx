import type { Analysis } from "../types";

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex-1 min-w-[140px] bg-white border border-emerald-200 rounded-xl px-4 py-3 shadow-sm">
      <div className="text-2xl font-bold text-emerald-900">{value}</div>
      <div className="text-xs text-emerald-700 mt-0.5">{label}</div>
    </div>
  );
}

export default function KpiStrip({ kpis }: { kpis: Analysis["kpis"] }) {
  const goldText =
    kpis.gold_precision === null
      ? "gold set pending"
      : `gold precision ${(kpis.gold_precision * 100).toFixed(0)}%`;

  return (
    <div className="max-w-7xl mx-auto px-6 pt-6">
      <div className="flex flex-wrap gap-3">
        <KpiCard label="Papers used" value={kpis.n_papers_used} />
        <KpiCard label="Verified facts" value={kpis.n_verified_facts} />
        <KpiCard label="Off-note molecules found" value={kpis.n_offnote_molecules} />
        <KpiCard label="Levers ranked" value={kpis.n_levers_ranked} />
      </div>
      <div className="text-xs text-emerald-700/70 mt-2">
        Extraction rejection rate: {(kpis.rejection_rate * 100).toFixed(1)}% &middot; {goldText}
      </div>
    </div>
  );
}
