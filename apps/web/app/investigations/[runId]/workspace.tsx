"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import "./workspace.css";

type AgentEvent = {
  id: string;
  sequence: number;
  agent: string;
  status: string;
  summary: string;
  provider: string | null;
  model: string | null;
  prompt_version: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
};

type Claim = {
  id: string;
  text: string;
  verdict: string;
  confidence: number;
  citations: { id: string; quote: string }[];
};

type Run = {
  id: string;
  status: string;
  current_stage: string | null;
  blocked_reason: string | null;
  provider_used: string;
  events: AgentEvent[];
  claims: Claim[];
  draft: { title: string; body: string; status: string } | null;
  editorial_decisions: {
    id: string;
    action: string;
    editor_name: string;
    note: string | null;
    created_at: string;
  }[];
  adversarial_findings: {
    id: string;
    agent: string;
    severity: string;
    category: string;
    claim_index: number | null;
    summary: string;
    recommendation: string;
    created_at: string;
  }[];
};

const demoRun: Run = {
  id: "demo-investigation",
  status: "review",
  current_stage: "human_editor",
  blocked_reason: null,
  provider_used: "openai",
  events: [
    { id: "1", sequence: 1, agent: "assignment_editor", status: "completed", summary: "Assigned 8 source snapshots across the newsroom", provider: "workflow", model: null, prompt_version: "assignment-editor-v1", input_tokens: 0, output_tokens: 0, latency_ms: 0 },
    { id: "2", sequence: 2, agent: "researcher", status: "completed", summary: "Extracted 19 schema-validated claims", provider: "openai", model: "gpt-5.4-mini", prompt_version: "researcher-v1", input_tokens: 2840, output_tokens: 921, latency_ms: 1840 },
    { id: "3", sequence: 3, agent: "reporter", status: "completed", summary: "Generated a cited newsroom draft", provider: "openai", model: "gpt-5.4-mini", prompt_version: "reporter-v1", input_tokens: 1630, output_tokens: 740, latency_ms: 1520 },
    { id: "4", sequence: 4, agent: "fact_checker", status: "completed", summary: "Completed evidence and independence review", provider: "openai", model: "gpt-5.4-mini", prompt_version: "fact-checker-v1", input_tokens: 2180, output_tokens: 510, latency_ms: 1310 },
  ],
  claims: [
    { id: "c1", text: "Transit service changed shortly after 14:00 local time.", verdict: "supported", confidence: 0.88, citations: [{ id: "q1", quote: "Service changed at approximately 14:00, according to the operations notice." }] },
    { id: "c2", text: "Officials have not released a final restoration timeline.", verdict: "supported", confidence: 0.82, citations: [{ id: "q2", quote: "A final timeline has not yet been issued by the authority." }] },
    { id: "c3", text: "Early reports disagree on the geographic extent of the disruption.", verdict: "disputed", confidence: 0.61, citations: [{ id: "q3", quote: "Reports differ on whether the eastern corridor was affected." }] },
  ],
  draft: {
    title: "Transit authority reviews conflicting disruption reports",
    body: "Transit service changed shortly after 14:00 local time, according to two independent reports. [1]\n\nOfficials have not released a final restoration timeline. [2]\n\nEarly accounts differ on the geographic extent of the disruption, and that detail remains under editorial review. [3]",
    status: "human_review",
  },
  editorial_decisions: [],
  adversarial_findings: [
    { id: "f1", agent: "misinformation_analyst", severity: "medium", category: "conflicting_accounts", claim_index: 2, summary: "Independent accounts disagree on the disruption boundary.", recommendation: "Keep the geographic extent explicitly unresolved.", created_at: "2026-08-20T10:00:00Z" },
    { id: "f2", agent: "bias_auditor", severity: "low", category: "framing_balance", claim_index: null, summary: "Authority statements receive more prominence than rider accounts.", recommendation: "Add direct attribution when more evidence becomes available.", created_at: "2026-08-20T10:00:01Z" },
  ],
};

const label = (value: string) => value.replaceAll("_", " ");

export function InvestigationWorkspace({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(runId === "demo" ? demoRun : null);
  const [error, setError] = useState<string | null>(null);
  const [editorName, setEditorName] = useState("Human Editor");
  const [editorNote, setEditorNote] = useState("");
  const [decisionPending, setDecisionPending] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    if (runId === "demo") return;
    let active = true;
    const load = async () => {
      const response = await fetch(`${apiUrl}/api/v1/investigations/${runId}`);
      if (!response.ok) throw new Error("Investigation could not be loaded");
      if (active) setRun(await response.json());
    };
    load().catch((reason: Error) => setError(reason.message));
    const stream = new EventSource(`${apiUrl}/api/v1/investigations/${runId}/events`);
    stream.addEventListener("agent_event", () => load().catch(() => undefined));
    stream.addEventListener("complete", () => {
      load().catch(() => undefined);
      stream.close();
    });
    stream.onerror = () => stream.close();
    return () => { active = false; stream.close(); };
  }, [apiUrl, runId]);

  const totals = useMemo(() => run?.events.reduce(
    (sum, event) => ({
      tokens: sum.tokens + (event.input_tokens ?? 0) + (event.output_tokens ?? 0),
      latency: sum.latency + (event.latency_ms ?? 0),
    }),
    { tokens: 0, latency: 0 },
  ), [run]);

  const submitDecision = async (action: "approve" | "request-revision") => {
    if (runId === "demo") return;
    setError(null);
    setDecisionPending(action);
    try {
      const response = await fetch(`${apiUrl}/api/v1/investigations/${runId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ editor_name: editorName.trim(), note: editorNote.trim() || null }),
      });
      if (!response.ok) {
        const payload: { detail?: string } = await response.json();
        throw new Error(payload.detail ?? "Editorial decision could not be recorded");
      }
      setRun(await response.json());
      setEditorNote("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Editorial decision failed");
    } finally {
      setDecisionPending(null);
    }
  };

  if (error) return <main className="workspace-state"><Link href="/">← Newsroom</Link><h1>{error}</h1></main>;
  if (!run) return <main className="workspace-state"><p>Connecting to the investigation desk…</p></main>;

  return (
    <main className="investigation-shell">
      <header className="investigation-header">
        <div><Link href="/">← Signal Desk</Link><p>Investigation / {run.id.slice(0, 8)}</p></div>
        <div className={`run-badge ${run.status}`}><span /> {label(run.status)}</div>
      </header>

      <section className="investigation-title">
        <div><p className="eyebrow">Human editorial gate · {run.provider_used}</p><h1>{run.draft?.title ?? "Investigation in progress"}</h1></div>
        <div className="run-totals"><b>{totals?.tokens.toLocaleString()}</b><span>tokens</span><b>{((totals?.latency ?? 0) / 1000).toFixed(1)}s</b><span>model time</span></div>
      </section>

      <section className="investigation-grid">
        <aside className="activity-rail">
          <div className="section-label">Agent activity</div>
          {run.events.map((event) => (
            <article className="activity-item" key={event.id}>
              <div className="activity-index">{String(event.sequence).padStart(2, "0")}</div>
              <div><h3>{label(event.agent)}</h3><p>{event.summary}</p><small>{event.model ?? event.provider ?? "workflow"} · {event.latency_ms ?? 0}ms</small></div>
            </article>
          ))}
        </aside>

        <article className="draft-column">
          <div className="section-label"><span>Editorial draft</span><em>{label(run.draft?.status ?? run.status)}</em></div>
          <div className="draft-copy">{run.draft?.body.split("\n").map((line, index) => <p key={index}>{line}</p>)}</div>
          {run.status === "review" && <div className="editor-gate">
            <div className="editor-identity"><label>Editor<input value={editorName} minLength={2} maxLength={120} onChange={(event) => setEditorName(event.target.value)} /></label><label>Decision note<textarea value={editorNote} maxLength={2000} rows={3} onChange={(event) => setEditorNote(event.target.value)} placeholder="Record the reasoning behind this decision…" /></label></div>
            <div className="editor-actions"><button disabled={Boolean(decisionPending) || editorName.trim().length < 2} onClick={() => submitDecision("request-revision")}>{decisionPending === "request-revision" ? "Recording…" : "Request revision"}</button><button className="approve" disabled={Boolean(decisionPending) || editorName.trim().length < 2} onClick={() => submitDecision("approve")}>{decisionPending === "approve" ? "Recording…" : "Approve for publication"}</button></div>
            <small className="gate-note">This decision is permanent and will be attached to the editorial audit trail.</small>
          </div>}
          {run.editorial_decisions.length > 0 && <section className="decision-log"><div className="section-label">Editorial audit trail</div>{run.editorial_decisions.map((decision) => <article key={decision.id}><span className={`decision-mark ${decision.action}`} /><div><b>{label(decision.action)}</b><p>{decision.note ?? "No editorial note provided."}</p><small>{decision.editor_name} · {new Date(decision.created_at).toLocaleString()}</small></div></article>)}</section>}
        </article>

        <aside className="evidence-column">
          <div className="section-label"><span>Adversarial review</span><em>{run.adversarial_findings.length} flags</em></div>
          <div className="risk-stack">{run.adversarial_findings.length === 0 ? <p className="risk-clear">No material misinformation or framing risks detected.</p> : run.adversarial_findings.map((finding) => <article className={`risk-card ${finding.severity}`} key={finding.id}><header><span>{label(finding.agent)}</span><b>{finding.severity}</b></header><h4>{label(finding.category)}</h4><p>{finding.summary}</p><small>{finding.recommendation}</small></article>)}</div>
          <div className="section-label claims-heading">Claims & evidence</div>
          {run.claims.map((claim, index) => (
            <details className="claim-card" key={claim.id} open={index === 0}>
              <summary><span className={`verdict ${claim.verdict}`} /> <b>Claim {index + 1}</b><em>{Math.round(claim.confidence * 100)}%</em></summary>
              <p>{claim.text}</p>
              {claim.citations.map((citation) => <blockquote key={citation.id}>“{citation.quote}”</blockquote>)}
            </details>
          ))}
        </aside>
      </section>
    </main>
  );
}
