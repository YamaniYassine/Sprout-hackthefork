import type { Analysis, Evidence, Options } from "./types";

// In dev (Vite on :5173), the backend runs separately on :8000.
// In production, the frontend is served BY FastAPI from the same origin,
// so relative paths ("/api/...") work automatically. Keep API_BASE "" and
// use a Vite dev-server proxy (see vite.config.ts) to avoid CORS entirely;
// CORS is still enabled server-side as a fallback.
const API_BASE = "";

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore json parse failure, fall back to statusText
    }
    throw new Error(detail);
  }
  return resp.json();
}

export async function fetchOptions(): Promise<Options> {
  const resp = await fetch(`${API_BASE}/api/options`);
  return handleResponse<Options>(resp);
}

export async function fetchAnalysis(protein: string, target: string): Promise<Analysis> {
  const params = new URLSearchParams({ protein, target });
  const resp = await fetch(`${API_BASE}/api/analysis?${params.toString()}`);
  return handleResponse<Analysis>(resp);
}

export async function runAnalysisLive(protein: string, target: string): Promise<Analysis> {
  const resp = await fetch(`${API_BASE}/api/analysis/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protein, target }),
  });
  return handleResponse<Analysis>(resp);
}

export async function fetchEvidence(evidenceId: string): Promise<Evidence> {
  const resp = await fetch(`${API_BASE}/api/evidence/${encodeURIComponent(evidenceId)}`);
  return handleResponse<Evidence>(resp);
}
