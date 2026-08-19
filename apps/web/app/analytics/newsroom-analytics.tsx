"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import "./analytics.css";

type Metric = { name: string; count: number };
type ProviderMetric = { provider: string; runs: number; tokens: number; latency_ms: number; estimated_cost_usd: number };
type Overview = { total_runs: number; total_claims: number; total_findings: number; status_breakdown: Metric[]; risk_breakdown: Metric[]; editorial_outcomes: Metric[]; providers: ProviderMetric[] };
type RunSummary = { id: string; story_title: string; status: string; provider_used: string; event_count: number; claim_count: number; finding_count: number; total_tokens: number; total_latency_ms: number; estimated_cost_usd: number; created_at: string };

const demoOverview: Overview = {
  total_runs: 38, total_claims: 247, total_findings: 31,
  status_breakdown: [{ name: "approved", count: 19 }, { name: "review", count: 8 }, { name: "blocked", count: 7 }, { name: "revision_requested", count: 4 }],
  risk_breakdown: [{ name: "high", count: 5 }, { name: "medium", count: 12 }, { name: "low", count: 14 }],
  editorial_outcomes: [{ name: "approved", count: 19 }, { name: "revision_requested", count: 4 }],
  providers: [{ provider: "gemini", runs: 21, tokens: 184320, latency_ms: 92740, estimated_cost_usd: 1.84 }, { provider: "deterministic", runs: 11, tokens: 0, latency_ms: 0, estimated_cost_usd: 0 }, { provider: "mock", runs: 6, tokens: 4500, latency_ms: 150, estimated_cost_usd: 0 }],
};
const demoRuns: RunSummary[] = [
  { id: "demo-01", story_title: "Transit authority revises restoration timeline", status: "approved", provider_used: "gemini", event_count: 6, claim_count: 9, finding_count: 2, total_tokens: 8640, total_latency_ms: 4380, estimated_cost_usd: .086, created_at: "2026-08-20T10:30:00Z" },
  { id: "demo-02", story_title: "Council procurement records prompt new questions", status: "review", provider_used: "gemini", event_count: 6, claim_count: 12, finding_count: 4, total_tokens: 11280, total_latency_ms: 5720, estimated_cost_usd: .113, created_at: "2026-08-20T09:12:00Z" },
  { id: "demo-03", story_title: "Conflicting accounts emerge after harbour closure", status: "blocked", provider_used: "deterministic", event_count: 6, claim_count: 5, finding_count: 3, total_tokens: 0, total_latency_ms: 0, estimated_cost_usd: 0, created_at: "2026-08-19T18:42:00Z" },
];
const label = (value: string) => value.replaceAll("_", " ");
const formatDate = (value: string) => new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
}).format(new Date(value));

export function NewsroomAnalytics() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [overview, setOverview] = useState<Overview>(demoOverview);
  const [runs, setRuns] = useState<RunSummary[]>(demoRuns);
  const [search, setSearch] = useState("");
  const [preview, setPreview] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/api/v1/analytics/overview`),
      fetch(`${apiUrl}/api/v1/investigations?limit=50`),
    ]).then(async ([overviewResponse, runsResponse]) => {
      if (!overviewResponse.ok || !runsResponse.ok) throw new Error("Analytics unavailable");
      setOverview(await overviewResponse.json());
      setRuns(await runsResponse.json());
      setPreview(false);
    }).catch(() => setPreview(true));
  }, [apiUrl]);

  const visibleRuns = runs.filter((run) => run.story_title.toLowerCase().includes(search.toLowerCase()));
  const approvalCount = overview.editorial_outcomes.find((item) => item.name === "approved")?.count ?? 0;
  const approvalRate = overview.total_runs ? Math.round((approvalCount / overview.total_runs) * 100) : 0;
  const maxStatus = Math.max(...overview.status_breakdown.map((item) => item.count), 1);

  return <main className="analytics-shell">
    <header className="analytics-header"><Link href="/">← Editorial desk</Link><div><span className="live-dot" /> Intelligence ledger</div></header>
    <section className="analytics-title"><div><p className="eyebrow">Newsroom intelligence / All investigations</p><h1>What the agents<br />are teaching us.</h1></div><p>Operational telemetry, adversarial risk, and human decisions—measured across every investigation.</p></section>
    {preview && <div className="preview-banner">Preview dataset · Start the API to display live newsroom metrics</div>}
    <section className="metric-strip"><article><span>Investigations</span><b>{overview.total_runs}</b><small>all recorded runs</small></article><article><span>Claims examined</span><b>{overview.total_claims}</b><small>source-backed assertions</small></article><article><span>Risk findings</span><b>{overview.total_findings}</b><small>adversarial flags</small></article><article><span>Approval rate</span><b>{approvalRate}%</b><small>human editorial outcome</small></article></section>
    <section className="analytics-grid">
      <article className="analytics-panel status-panel"><div className="analytics-label">Outcome distribution</div>{overview.status_breakdown.map((item) => <div className="status-row" key={item.name}><span>{label(item.name)}</span><div><i style={{ width: `${(item.count / maxStatus) * 100}%` }} /></div><b>{item.count}</b></div>)}</article>
      <article className="analytics-panel risk-panel"><div className="analytics-label">Adversarial risk</div><div className="risk-total"><b>{overview.total_findings}</b><span>structured findings</span></div>{overview.risk_breakdown.map((item) => <div className={`risk-line ${item.name}`} key={item.name}><span>{item.name}</span><b>{item.count}</b></div>)}</article>
      <article className="analytics-panel provider-panel"><div className="analytics-label">Provider performance</div>{overview.providers.map((item) => <div className="provider-row" key={item.provider}><div><b>{item.provider}</b><small>{item.runs} runs</small></div><span>{item.tokens.toLocaleString()} tok</span><span>{(item.latency_ms / 1000).toFixed(1)}s</span><strong>${item.estimated_cost_usd.toFixed(3)}</strong></div>)}</article>
    </section>
    <section className="run-ledger"><header><div><p className="analytics-label">Investigation ledger</p><h2>Recent runs</h2></div><input aria-label="Search investigations" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search story titles…" /></header><div className="run-table"><div className="run-row table-head"><span>Story</span><span>State</span><span>Provider</span><span>Claims / risks</span><span>Tokens</span><span>Cost</span></div>{visibleRuns.map((run) => <Link className="run-row" href={run.id.startsWith("demo") ? "/investigations/demo" : `/investigations/${run.id}`} key={run.id}><span><b>{run.story_title}</b><small>{formatDate(run.created_at)} UTC</small></span><span><i className={`ledger-state ${run.status}`} />{label(run.status)}</span><span>{run.provider_used}</span><span>{run.claim_count} / {run.finding_count}</span><span>{run.total_tokens.toLocaleString()}</span><span>${run.estimated_cost_usd.toFixed(3)}</span></Link>)}</div></section>
  </main>;
}
