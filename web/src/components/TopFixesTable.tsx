import { Fragment, useState } from "react";
import type { Analysis, Co2Impact } from "../types";
import { buildTopPairings } from "../lib/pairings";
import { CLEAN_LABEL_COLORS, co2BandColor, familyColor } from "../theme";
import { EmptyState } from "./Skeleton";
import EvidenceQuote from "./EvidenceQuote";
import MoreInfoPanel from "./MoreInfoPanel";

const MAX_QUOTES_SHOWN = 2;

function papers(n: number): string {
  return `${n} ${n === 1 ? "paper" : "papers"}`;
}

function CleanLabelChip({ tier }: { tier: 0 | 1 | 2 }) {
  const c = CLEAN_LABEL_COLORS[tier];
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {c.label}
      <span className="text-[10px] opacity-70">(assumed)</span>
    </span>
  );
}

function Co2Chip({ impact }: { impact: Co2Impact }) {
  const c = co2BandColor(impact.score);
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {c.label} impact ({impact.score}/100)
      <span className="text-[10px] opacity-70">(predicted)</span>
    </span>
  );
}

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
      <div className="w-28 h-2.5 rounded-full bg-sprout-mint overflow-hidden">
        <div className="h-full bg-sprout-green" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-sprout-deepGreen font-mono">{score.toFixed(2)}</span>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className={"w-4 h-4 text-sprout-green transition-transform " + (open ? "rotate-180" : "")}
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function TopFixesTable({ analysis }: { analysis: Analysis }) {
  const pairings = buildTopPairings(analysis, 5);
  const maxScore = Math.max(...pairings.map((p) => p.offNote.evidence_score), 1);
  const [openRank, setOpenRank] = useState<number | null>(null);

  if (pairings.length === 0) {
    return <EmptyState message="No off-note molecules found in the corpus for this scenario." />;
  }

  return (
    <div className="bg-white border border-sprout-paleSage rounded-2xl shadow-sm overflow-hidden">
      <div className="px-6 py-5 bg-sprout-dark">
        <h2 className="font-display text-2xl font-bold text-sprout-cream">Top 5 fixes</h2>
        <p className="text-sm text-sprout-mint mt-1">
          The strongest off-taste molecules found in the plant protein, and the best-supported
          plant-only additive or process to fix each one. Click a row for the supporting evidence.
        </p>
      </div>

      {/* table-fixed: column widths no longer depend on the content of an opened row */}
      <table className="w-full table-fixed text-sm">
        <thead>
          <tr className="bg-sprout-cream text-sprout-green text-left border-b border-sprout-paleSage">
            <th className="px-6 py-3 font-bold w-20 uppercase text-[11px] tracking-widest">#</th>
            <th className="px-6 py-3 font-bold w-[30%] uppercase text-[11px] tracking-widest">
              Off-taste molecule
            </th>
            <th className="px-6 py-3 font-bold w-[34%] uppercase text-[11px] tracking-widest">
              Recommended additive / process
            </th>
            <th className="px-6 py-3 font-bold uppercase text-[11px] tracking-widest">Impact</th>
            <th className="px-4 py-3 w-14"></th>
          </tr>
        </thead>
        <tbody>
          {pairings.map(({ rank, offNote, lever }) => {
            const isOpen = openRank === rank;
            const moleculeQuoteIds = offNote.evidence_ids.slice(0, MAX_QUOTES_SHOWN);
            const leverQuoteIds = lever ? lever.evidence_ids.slice(0, MAX_QUOTES_SHOWN) : [];

            return (
              <Fragment key={offNote.molecule}>
                <tr
                  onClick={() => setOpenRank(isOpen ? null : rank)}
                  className="border-t border-sprout-paleSage/60 bg-white hover:bg-sprout-cream cursor-pointer"
                >
                  <td className="px-6 py-4 font-display text-xl font-bold text-sprout-green">
                    {rank}
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-semibold text-sprout-dark">{offNote.molecule}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                      <FamilyChip family={offNote.family} />
                      <span className="text-xs text-sprout-midSage">{papers(offNote.n_papers)}</span>
                      {offNote.scope === "general" && (
                        <span className="text-xs text-sprout-midSage italic">general plant protein</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {lever ? (
                      <>
                        <div className="font-semibold text-sprout-dark">{lever.name}</div>
                        <div className="text-xs text-sprout-midSage mt-0.5">
                          <span className="capitalize">{lever.kind}</span> &middot;{" "}
                          <span className="capitalize">{lever.cost_tier}</span> cost &middot;{" "}
                          {papers(lever.n_papers)}
                        </div>
                      </>
                    ) : (
                      <span className="text-sprout-midSage italic text-xs">No ranked lever found yet</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <ImpactBar score={offNote.evidence_score} max={maxScore} />
                  </td>
                  <td className="px-4 py-4">
                    <Chevron open={isOpen} />
                  </td>
                </tr>

                {isOpen && (
                  <tr className="bg-sprout-cream border-t border-sprout-paleSage">
                    <td></td>
                    <td colSpan={4} className="px-6 py-5">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
                          <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">
                            Why this molecule is flagged
                          </div>
                          <div className="flex flex-col gap-1.5">
                            {offNote.oav !== null && (
                              <div className="text-xs text-sprout-deepGreen">
                                <span className="font-medium">Odor activity value (OAV):</span>{" "}
                                <span className="font-mono">{offNote.oav}</span>
                              </div>
                            )}
                            {moleculeQuoteIds.map((id) => {
                              const ev = analysis.evidence[id];
                              return ev ? <EvidenceQuote key={id} evidence={ev} /> : null;
                            })}
                          </div>
                        </div>

                        <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
                          <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">
                            Why this fix is recommended
                          </div>
                          {lever ? (
                            <div className="flex flex-col gap-1.5">
                              <div>
                                <CleanLabelChip tier={lever.clean_label} />
                              </div>
                              {leverQuoteIds.map((id) => {
                                const ev = analysis.evidence[id];
                                return ev ? <EvidenceQuote key={id} evidence={ev} /> : null;
                              })}
                            </div>
                          ) : (
                            <span className="text-sprout-midSage italic text-xs">
                              No ranked lever addresses this molecule yet.
                            </span>
                          )}
                        </div>

                        <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
                          <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">
                            CO2 impact
                          </div>
                          {lever ? (
                            <div className="flex flex-col gap-1.5">
                              <div>
                                <Co2Chip impact={lever.co2_impact} />
                              </div>
                              <p className="text-xs text-sprout-sage italic">{lever.co2_impact.rationale}</p>
                            </div>
                          ) : (
                            <span className="text-sprout-midSage italic text-xs">
                              No ranked lever to estimate yet.
                            </span>
                          )}
                        </div>
                      </div>

                      <MoreInfoPanel analysis={analysis} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
