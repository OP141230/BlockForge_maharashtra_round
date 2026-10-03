const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function fetchRuns(status?: string) {
  const url = status ? `${API_BASE}/runs?status=${status}` : `${API_BASE}/runs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchRun(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}`);
  return res.json();
}

export async function fetchRunGraph(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}/graph`);
  if (!res.ok) throw new Error(`Failed to fetch graph for run ${runId}`);
  return res.json();
}

export async function fetchDiagnosis(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}/diagnosis`);
  if (!res.ok) throw new Error(`Failed to fetch diagnosis for run ${runId}`);
  return res.json();
}

export async function replayRun(runId: string, stepId: string, modifiedInput: Record<string, any>) {
  const res = await fetch(`${API_BASE}/runs/${runId}/replay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step_id: stepId, modified_input: modifiedInput }),
  });
  if (!res.ok) throw new Error(`Replay failed for run ${runId}`);
  return res.json();
}

export async function compareRuns(runId: string, baselineId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}/compare/${baselineId}`);
  if (!res.ok) throw new Error("Failed to compare runs");
  return res.json();
}

export async function fetchBenchmark() {
  const res = await fetch(`${API_BASE}/evaluation/benchmark`);
  if (!res.ok) throw new Error("Failed to fetch benchmark");
  return res.json();
}

export async function runBenchmarkSuite() {
  const res = await fetch(`${API_BASE}/evaluation/run`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to execute benchmark");
  return res.json();
}

export async function fetchPatterns() {
  const res = await fetch(`${API_BASE}/patterns`);
  if (!res.ok) throw new Error("Failed to fetch patterns");
  return res.json();
}
