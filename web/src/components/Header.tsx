type HeaderProps = {
  proteins: string[];
  targets: string[];
  protein: string;
  target: string;
  onProteinChange: (p: string) => void;
  onTargetChange: (t: string) => void;
  onAnalyze: () => void;
  onRunLive: () => void;
  isLoading: boolean;
  source: "precomputed" | "live" | null;
};

function SegmentedControl({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={
              "px-3 py-1.5 text-sm font-medium rounded-md capitalize transition-colors " +
              (value === opt
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100")
            }
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Header({
  proteins,
  targets,
  protein,
  target,
  onProteinChange,
  onTargetChange,
  onAnalyze,
  onRunLive,
  isLoading,
  source,
}: HeaderProps) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-end gap-3">
          <h1 className="text-2xl font-bold text-slate-900">FlavorGap</h1>
          <span className="text-sm text-slate-500 pb-0.5">
            Plant-based flavor gap analysis, literature-based
          </span>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <SegmentedControl
            label="Protein"
            options={proteins}
            value={protein}
            onChange={onProteinChange}
          />
          <SegmentedControl
            label="Target"
            options={targets}
            value={target}
            onChange={onTargetChange}
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onAnalyze}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? "Analyzing..." : "Analyze"}
            </button>
            <button
              type="button"
              onClick={onRunLive}
              disabled={isLoading}
              className="px-3 py-2 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              Run live
            </button>
          </div>

          {source && (
            <span
              className={
                "px-2.5 py-1 rounded-full text-xs font-semibold " +
                (source === "live"
                  ? "bg-amber-100 text-amber-800"
                  : "bg-slate-100 text-slate-700")
              }
            >
              {source}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
