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

// Visual-only roadmap options, shown disabled for the pitch. Not wired to any data.
const PROTEINS_COMING_SOON = ["mycoprotein", "chickpea"];
const TARGETS_COMING_SOON = ["pork", "fish"];

function SelectField({
  step,
  label,
  options,
  comingSoon,
  value,
  onChange,
}: {
  step: string;
  label: string;
  options: string[];
  comingSoon: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
      <span className="text-[11px] font-bold tracking-widest uppercase text-sprout-green">
        {step} &middot; {label}
      </span>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-[50px] appearance-none rounded-xl border border-sprout-paleSage bg-white pl-4 pr-11 text-base font-medium text-sprout-dark capitalize focus:outline-none focus:ring-2 focus:ring-sprout-green cursor-pointer"
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
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-sprout-green"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    </label>
  );
}

function ArrowRight() {
  return (
    <div className="hidden md:flex h-[50px] items-center text-sprout-softSage" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-6 h-6"
      >
        <path d="M5 12h14M13 6l6 6-6 6" />
      </svg>
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
    <header>
      {/* Dark brand band, mirrors the title slide of the pitch deck */}
      <div className="bg-sprout-dark">
        <div className="max-w-7xl mx-auto px-6 pt-7 pb-14">
          <p className="text-xs font-bold tracking-widest uppercase text-sprout-lime">
            Plant-based flavor gap analysis
          </p>
          <h1 className="font-display text-4xl font-bold text-sprout-cream mt-1.5">Sprout</h1>
          <p className="mt-2 max-w-3xl text-sm text-sprout-mint">
            Mines the scientific literature for masking agents and scores them for taste, clean
            label and CO&#8322; footprint.
          </p>
        </div>
      </div>

      {/* Input card overlapping the band */}
      <div className="max-w-7xl mx-auto px-6 -mt-8">
        <div className="bg-white rounded-2xl border border-sprout-paleSage shadow-lg px-6 py-5 flex flex-wrap items-end gap-4">
          <SelectField
            step="1"
            label="Plant protein"
            options={proteins}
            comingSoon={PROTEINS_COMING_SOON}
            value={protein}
            onChange={onProteinChange}
          />
          <ArrowRight />
          <SelectField
            step="2"
            label="Meat target"
            options={targets}
            comingSoon={TARGETS_COMING_SOON}
            value={target}
            onChange={onTargetChange}
          />

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onAnalyze}
              disabled={isLoading}
              className="h-[50px] px-7 rounded-xl bg-sprout-green text-white text-base font-semibold hover:bg-sprout-deepGreen disabled:opacity-50 transition-colors shadow-sm"
            >
              {isLoading ? "Analyzing..." : "Analyze"}
            </button>
            <button
              type="button"
              onClick={onRunLive}
              disabled={isLoading}
              title="Re-run the full pipeline with fresh literature retrieval (calls AWS Bedrock)"
              className="h-[50px] px-5 rounded-xl border border-sprout-paleSage text-sprout-deepGreen text-sm font-semibold hover:bg-sprout-cream disabled:opacity-50 transition-colors"
            >
              Run live
            </button>
          </div>

          {source && (
            <div className="ml-auto self-center flex items-center gap-2 text-xs text-sprout-midSage">
              <span className="uppercase tracking-widest font-semibold">Source</span>
              <span
                className={
                  "px-2.5 py-1 rounded-full font-semibold " +
                  (source === "live"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-sprout-mint text-sprout-green")
                }
              >
                {source}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
