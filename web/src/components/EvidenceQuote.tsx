import type { Evidence } from "../types";
import { originColor } from "../theme";

function OriginBadge({ origin }: { origin: string }) {
  const c = originColor(origin);
  return (
    <span
      className="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {origin}
    </span>
  );
}

export default function EvidenceQuote({ evidence }: { evidence: Evidence }) {
  return (
    <div className="text-xs text-sprout-deepGreen bg-sprout-cream border border-sprout-paleSage border-l-4 border-l-sprout-green rounded-xl px-3 py-2.5">
      <p className="font-display italic text-[13px] leading-snug text-sprout-dark">&ldquo;{evidence.quote}&rdquo;</p>
      <div className="flex items-center gap-2 mt-1.5 text-sprout-midSage">
        <span className="font-medium">
          {evidence.file} p.{evidence.page ?? "?"}
        </span>
        <OriginBadge origin={evidence.origin} />
        {evidence.paper_grade !== null && <span>grade {evidence.paper_grade}/3</span>}
      </div>
    </div>
  );
}
