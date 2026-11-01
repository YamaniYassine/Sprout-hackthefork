import type { Analysis } from "../types";

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex-1 min-w-[160px] bg-white border border-sprout-paleSage rounded-2xl px-5 py-4 shadow-sm">
      <div className="font-display text-4xl font-bold leading-none text-sprout-dark">{value}</div>
      <div className="text-[11px] font-bold tracking-widest uppercase text-sprout-green mt-2">{label}</div>
    </div>
  );
}

export default function KpiStrip({ kpis }: { kpis: Analysis["kpis"] }) {
  const goldText =
    kpis.gold_precision === null
      ? "gold set pending"
      : `gold precision ${(kpis.gold_precision * 100).toFixed(0)}%`;

  return (
    <div className="max-w-7xl mx-auto px-6 pt-8">
      <div className="flex flex-wrap gap-4">
        <KpiCard label="Papers used" value={kpis.n_papers_used} />
        <KpiCard label="Verified facts" value={kpis.n_verified_facts} />
        <KpiCard label="Off-note molecules found" value={kpis.n_offnote_molecules} />
        <KpiCard label="Levers ranked" value={kpis.n_levers_ranked} />
      </div>
      <div className="text-xs text-sprout-midSage mt-3">
        Extraction rejection rate: {(kpis.rejection_rate * 100).toFixed(1)}% &middot; {goldText}
      </div>
    </div>
  );
}
