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

function Dropdown({
  label,
  options,
  comingSoon = [],
  value,
  onChange,
}: {
  label: string;
  options: string[];
  comingSoon?: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-semibold tracking-wide uppercase text-sprout-green">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[160px] rounded-lg border border-sprout-paleSage bg-white px-3 py-2 text-sm font-medium text-sprout-dark capitalize shadow-sm focus:outline-none focus:ring-2 focus:ring-sprout-green cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt} value={opt} className="capitalize">
            {opt}
          </option>
        ))}
        {comingSoon.map((opt) => (
          <option key={opt} value={opt} disabled className="capitalize text-gray-400">
            {opt} (coming soon)
          </option>
        ))}
      </select>
    </label>
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
    <header className="bg-white border-b border-sprout-paleSage">
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-end gap-3">
          <h1 className="font-display text-2xl font-bold text-sprout-dark">Sprout</h1>
          <span className="text-sm text-sprout-sage pb-0.5">
            Plant-based flavor gap analysis, literature-based
          </span>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <Dropdown
            label="Plant protein"
            options={proteins}
            comingSoon={["mycoprotein", "chickpea"]}
            value={protein}
            onChange={onProteinChange}
          />
          <Dropdown
            label="Meat target"
            options={targets}
            comingSoon={["pork", "fish"]}
            value={target}
            onChange={onTargetChange}
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onAnalyze}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg bg-sprout-green text-white text-sm font-semibold hover:bg-sprout-deepGreen disabled:opacity-50 transition-colors shadow-sm"
            >
              {isLoading ? "Analyzing..." : "Analyze"}
            </button>
            <button
              type="button"
              onClick={onRunLive}
              disabled={isLoading}
              className="px-3 py-2 rounded-lg border border-sprout-paleSage text-sprout-deepGreen text-sm font-medium hover:bg-sprout-cream disabled:opacity-50 transition-colors"
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
                  : "bg-sprout-mint text-sprout-green")
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
