import { useState, type ReactNode } from "react";
import type { Analysis } from "../types";
import { familyColor } from "../theme";

/**
 * "More info" toggle inside each row's drop-down. It reveals scenario-level
 * context (the same for every row of a scenario):
 *   1. The cited explanation (core/explain.py output). The raw "[file p.N]"
 *      tags are shown as numbered chips, with a numbered source list below.
 *      Hovering a chip or a source shows the supporting quote when the
 *      scenario's evidence set contains one for that file and page.
 *   2. The Limits box (literature-based caveats, rejection rate, etc.)
 *   3. Missing meat-like notes (molecules entirely absent from the plant base,
 *      not just "off", a different question than the off-notes table)
 */

// "[some-file.pdf p.9]" (an optional ".0" after the page is tolerated)
const CITATION = /\[([^[\]]+?)\s+p\.\s*(\d+)(?:\.\d+)?\]/g;

type Source = { n: number; file: string; page: number; quote: string | null };

function CitationChip({ source }: { source: Source }) {
  const label = `${source.file} p.${source.page}`;
  return (
    <span
      title={source.quote ? `\u201C${source.quote}\u201D \u2014 ${label}` : label}
      className="cursor-help inline-flex items-center justify-center align-super mx-px min-w-[16px] h-4 px-1 rounded-full bg-sprout-green text-white text-[10px] font-bold leading-none"
    >
      {source.n}
    </span>
  );
}

function renderExplanation(text: string, analysis: Analysis): { nodes: ReactNode[]; sources: Source[] } {
  const evidence = Object.values(analysis.evidence);
  const sources: Source[] = [];
  const numberFor = new Map<string, number>();
  const nodes: ReactNode[] = [];
  let cursor = 0;

  for (const m of text.matchAll(CITATION)) {
    const start = m.index ?? 0;
    const file = m[1].trim();
    const page = Number(m[2]);
    const id = `${file}|${page}`;

    let n = numberFor.get(id);
    let source: Source;
    if (n === undefined) {
      n = sources.length + 1;
      numberFor.set(id, n);
      source = {
        n,
        file,
        page,
        quote: evidence.find((e) => e.file === file && e.page === page)?.quote ?? null,
      };
      sources.push(source);
    } else {
      source = sources[n - 1];
    }

    // text before this citation; drop the space before the bracket so the chip hugs the word
    nodes.push(text.slice(cursor, start).replace(/\s+$/, ""));
    nodes.push(<CitationChip key={`c${start}`} source={source} />);
    cursor = start + m[0].length;
  }
  nodes.push(text.slice(cursor));
  return { nodes, sources };
}

const LABEL = "text-[11px] font-bold uppercase tracking-widest text-sprout-green mb-2";

export default function MoreInfoPanel({ analysis }: { analysis: Analysis }) {
  const [open, setOpen] = useState(false);
  const explanationText = analysis.explanation.text;
  const { nodes, sources } = renderExplanation(explanationText, analysis);

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
          <div className="col-span-2 bg-white rounded-xl border border-sprout-paleSage p-5">
            <div className={LABEL}>Cited explanation</div>
            <p className="text-sm text-sprout-deepGreen leading-relaxed whitespace-pre-line">
              {explanationText ? nodes : "No explanation available for this scenario."}
            </p>
            {!analysis.explanation.citations_valid && (
              <p className="text-xs text-amber-600 italic mt-2">
                Some citations could not be verified and were removed.
              </p>
            )}
            {sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-sprout-paleSage">
                <div className="text-[10px] font-bold uppercase tracking-widest text-sprout-midSage mb-1.5">
                  Sources
                </div>
                <ol className="space-y-1">
                  {sources.map((s) => (
                    <li
                      key={s.n}
                      title={s.quote ?? undefined}
                      className="flex gap-2 text-[11px] text-sprout-midSage"
                    >
                      <span className="font-bold text-sprout-green w-4 shrink-0">{s.n}</span>
                      <span className="break-all">
                        {s.file} p.{s.page}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4">
            <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
              <div className={LABEL}>Limits</div>
              <ul className="text-xs text-sprout-deepGreen list-disc pl-4 space-y-0.5">
                {analysis.limits.map((limit, i) => (
                  <li key={i}>{limit}</li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-xl border border-sprout-paleSage p-4">
              <div className={LABEL}>Missing vs. meat (molecules entirely absent from the plant base)</div>
              {analysis.missing_notes.length === 0 ? (
                <span className="text-sprout-midSage italic text-xs">No evidence found in the corpus.</span>
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
        </div>
      )}
    </div>
  );
}
