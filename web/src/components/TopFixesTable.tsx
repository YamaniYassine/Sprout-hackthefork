import { Fragment, useState } from "react";
import type { Analysis, Co2Impact } from "../types";
import { buildTopPairings } from "../lib/pairings";
import { CLEAN_LABEL_COLORS, co2BandColor, familyColor } from "../theme";
import { EmptyState } from "./Skeleton";
import EvidenceQuote from "./EvidenceQuote";
import MoreInfoPanel from "./MoreInfoPanel";

const MAX_QUOTES_SHOWN = 2;

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
      <div className="w-24 h-2 rounded-full bg-sprout-mint overflow-hidden">
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
    <div className="bg-white border border-sprout-paleSage rounded-xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-sprout-paleSage">
        <h2 className="font-display text-lg font-bold text-sprout-dark">Top 5 fixes</h2>
        <p className="text-sm text-sprout-sage mt-0.5">
          The strongest off-taste molecules found in the plant protein, and the best-supported
          plant-only additive or process to fix each one. Click a row for the supporting evidence.
        </p>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="bg-white text-sprout-green text-left border-b border-sprout-paleSage">
            <th className="px-5 py-2.5 font-semibold w-12 uppercase text-xs tracking-wide">#</th>
            <th className="px-5 py-2.5 font-semibold uppercase text-xs tracking-wide">Off-taste molecule</th>
            <th className="px-5 py-2.5 font-semibold uppercase text-xs tracking-wide">
              Recommended additive / process
            </th>
            <th className="px-5 py-2.5 font-semibold uppercase text-xs tracking-wide">Impact</th>
            <th className="px-5 py-2.5 w-8"></th>
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
                  className="border-t border-gray-100 bg-white hover:bg-sprout-cream cursor-pointer"
                >
                  <td className="px-5 py-3 font-display font-bold text-sprout-green">{rank}</td>
                  <td className="px-5 py-3">
                    <div className="font-medium text-sprout-dark">{offNote.molecule}</div>
                    <div className="mt-1 flex items-center gap-2">
                      <FamilyChip family={offNote.family} />
                      <span className="text-xs text-sprout-midSage">{offNote.n_papers} paper(s)</span>
                      {offNote.scope === "general" && (
                        <span className="text-xs text-slate-400 italic">general plant protein</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    {lever ? (
                      <>
                        <div className="font-medium text-sprout-dark">{lever.name}</div>
                        <div className="text-xs text-sprout-midSage mt-0.5 capitalize">
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
                  <td className="px-5 py-3">
                    <Chevron open={isOpen} />
                  </td>
                </tr>

                {isOpen && (
                  <tr className="bg-sprout-cream border-t border-gray-100">
                    <td></td>
                    <td colSpan={4} className="px-5 py-4">
                      <div className="grid grid-cols-3 gap-5">
                        <div>
                          <div className="text-xs font-semibold uppercase tracking-wide text-sprout-green mb-1.5">
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

                        <div>
                          <div className="text-xs font-semibold uppercase tracking-wide text-sprout-green mb-1.5">
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
                            <span className="text-slate-400 italic text-xs">
                              No ranked lever addresses this molecule yet.
                            </span>
                          )}
                        </div>

                        <div>
                          <div className="text-xs font-semibold uppercase tracking-wide text-sprout-green mb-1.5">
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
                            <span className="text-slate-400 italic text-xs">
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
