import { useEffect, useState } from "react";
import "./index.css";
import Header from "./components/Header";
import KpiStrip from "./components/KpiStrip";
import TopFixesTable from "./components/TopFixesTable";
import { Skeleton } from "./components/Skeleton";
import { fetchAnalysis, fetchOptions, runAnalysisLive } from "./api";
import type { Analysis, Options } from "./types";

export default function App() {
  const [options, setOptions] = useState<Options | null>(null);
  const [protein, setProtein] = useState<string>("pea");
  const [target, setTarget] = useState<string>("beef burger");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available options once, then run the first analysis.
  useEffect(() => {
    fetchOptions()
      .then((opts) => {
        setOptions(opts);
        setProtein(opts.proteins[0]);
        setTarget(opts.targets[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (options) {
      void handleAnalyze(protein, target);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options]);

  async function handleAnalyze(p = protein, t = target) {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchAnalysis(p, t);
      setAnalysis(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRunLive() {
    setIsLoading(true);
    setError(null);
    try {
      const result = await runAnalysisLive(protein, target);
      setAnalysis(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-emerald-50/40">
      <Header
        proteins={options?.proteins ?? []}
        targets={options?.targets ?? []}
        protein={protein}
        target={target}
        onProteinChange={(p) => {
          setProtein(p);
          void handleAnalyze(p, target);
        }}
        onTargetChange={(t) => {
          setTarget(t);
          void handleAnalyze(protein, t);
        }}
        onAnalyze={() => void handleAnalyze()}
        onRunLive={() => void handleRunLive()}
        isLoading={isLoading}
        source={analysis?.scenario.source ?? null}
      />

      {error && (
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        </div>
      )}

      {isLoading && !analysis && (
        <div className="max-w-7xl mx-auto px-6 pt-6 flex gap-3">
          <Skeleton className="h-20 flex-1" />
          <Skeleton className="h-20 flex-1" />
          <Skeleton className="h-20 flex-1" />
          <Skeleton className="h-20 flex-1" />
        </div>
      )}

      {analysis && <KpiStrip kpis={analysis.kpis} />}

      {analysis && (
        <main className="max-w-7xl mx-auto px-6 py-6">
          <TopFixesTable analysis={analysis} />
        </main>
      )}
    </div>
  );
}
