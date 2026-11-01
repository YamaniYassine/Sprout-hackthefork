import { useState } from "react";
import type { Analysis } from "../types";
import { familyColor } from "../theme";

/**
 * Trial feature: a "More info" toggle inside each row's drop-down that
 * reveals scenario-level context the user asked to evaluate:
 *   1. The cited explanation paragraph (core/explain.py output)
 *   2. The Limits box (literature-based caveats, rejection rate, etc.)
 *   3. Missing meat-like notes (molecules entirely absent from the plant
 *      base, not just "off" -- a different question than the off-notes table)
 *
 * This is the same content for every row in a given scenario (it is not
 * per-molecule), shown on demand so it doesn't clutter the main per-row view.
 */
export default function MoreInfoPanel({ analysis }: { analysis: Analysis }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 pt-4 border-t border-sprout-paleSage">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
        className="text-[11px] font-bold tracking-widest uppercase text-sprout-green hover:text-sprout-deepGreen underline underline-offset-4"
      >
        {open ? "Hide more info" : "More info"}
      </button>

      {open && (
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
            <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">
              Cited explanation
            </div>
            <p className="text-xs text-sprout-deepGreen leading-relaxed">
              {analysis.explanation.text || "No explanation available for this scenario."}
            </p>
            {!analysis.explanation.citations_valid && (
              <p className="text-xs text-amber-600 italic mt-1">
                Some citations could not be verified and were removed.
              </p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
            <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">Limits</div>
            <ul className="text-xs text-sprout-deepGreen list-disc pl-4 space-y-0.5">
              {analysis.limits.map((limit, i) => (
                <li key={i}>{limit}</li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
            <div className="text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2">
              Missing vs. meat (molecules entirely absent from the plant base)
            </div>
            {analysis.missing_notes.length === 0 ? (
              <span className="text-sprout-midSage italic text-xs">
                No evidence found in the corpus.
              </span>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {analysis.missing_notes.slice(0, 10).map((m) => (
                  <span
                    key={m.molecule}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: familyColor(m.family) }}
                    title={`${m.n_papers} paper(s)`}
                  >
                    {m.molecule}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
