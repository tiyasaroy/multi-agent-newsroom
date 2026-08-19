"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import "./editorial-control-center.css";

type Provider = "gemini" | "openai" | "mock" | "deterministic";
type SourceDraft = { title: string; publisher: string; url: string; snapshot_text: string };
const blankSource = (): SourceDraft => ({ title: "", publisher: "", url: "", snapshot_text: "" });
const providerDetails: Record<Provider, { label: string; note: string }> = {
  gemini: { label: "Gemini", note: "Live · 3.6 Flash" },
  openai: { label: "OpenAI", note: "Live · GPT" },
  mock: { label: "Simulation", note: "Model-shaped" },
  deterministic: { label: "Local", note: "No API cost" },
};

export function EditorialControlCenter() {
  const router = useRouter();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [provider, setProvider] = useState<Provider>("gemini");
  const [sources, setSources] = useState<SourceDraft[]>([blankSource(), blankSource()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const readySources = useMemo(() => sources.filter((source) => (
    Boolean(source.url.trim()) || (Boolean(source.title.trim()) && source.snapshot_text.trim().length >= 20)
  )), [sources]);

  const updateSource = (index: number, field: keyof SourceDraft, value: string) => {
    setSources((current) => current.map((source, sourceIndex) => sourceIndex === index ? { ...source, [field]: value } : source));
  };

  const launch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (readySources.length < 2) {
      setError("Add at least two complete source snapshots for independent verification.");
      return;
    }
    setSubmitting(true);
    try {
      const storyResponse = await fetch(`${apiUrl}/api/v1/stories`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), summary: summary.trim() || null }),
      });
      if (!storyResponse.ok) throw new Error("The story desk rejected this assignment.");
      const story: { id: string } = await storyResponse.json();
      const capturedCounts = await Promise.all(readySources.map(async (source) => {
        const automatic = Boolean(source.url.trim()) && source.snapshot_text.trim().length < 20;
        const endpoint = automatic
          ? `${apiUrl}/api/v1/stories/${story.id}/sources/ingest`
          : `${apiUrl}/api/v1/stories/${story.id}/sources`;
        const body = automatic
          ? { url: source.url.trim(), max_items: 5 }
          : { title: source.title.trim(), publisher: source.publisher.trim() || null, url: source.url.trim() || null, kind: source.url.trim() ? "article" : "manual", snapshot_text: source.snapshot_text.trim() };
        const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        if (!response.ok) {
          const payload: { detail?: string } = await response.json();
          throw new Error(payload.detail ?? `Source “${source.title || source.url}” could not be attached.`);
        }
        const captured = await response.json();
        return Array.isArray(captured) ? captured.length : 1;
      }));
      if (capturedCounts.reduce((total, count) => total + count, 0) < 2) {
        throw new Error("Ingestion produced fewer than two independent source snapshots.");
      }
      const runResponse = await fetch(`${apiUrl}/api/v1/stories/${story.id}/investigations?provider=${provider}&background=true`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() } });
      if (!runResponse.ok) throw new Error("The agent team could not be launched.");
      const run: { id: string } = await runResponse.json();
      router.push(`/investigations/${run.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The newsroom could not start this run.");
      setSubmitting(false);
    }
  };

  return (
    <main className="control-center">
      <header className="control-header">
        <Link href="/" className="brand"><span>THE SIGNAL DESK</span><b>Multi-Agent Newsroom</b></Link>
        <div className="system-state"><i /> All desks operational</div>
      </header>
      <section className="control-intro">
        <div><p className="eyebrow">Editorial control center / New assignment</p><h1>Put a story<br />under pressure.</h1></div>
        <p>Commission an evidence-first investigation. Independent agents will extract claims, draft with citations, and challenge every material assertion before a human sees it.</p>
      </section>
      <form className="assignment-grid" onSubmit={launch}>
        <section className="briefing-column">
          <div className="form-section-heading"><span>01</span><div><b>Assignment brief</b><small>Define what the newsroom should investigate</small></div></div>
          <label className="field-label" htmlFor="story-title">Working headline</label>
          <input id="story-title" className="headline-input" value={title} onChange={(event) => setTitle(event.target.value)} minLength={5} maxLength={240} required placeholder="What is happening—and what needs proving?" />
          <label className="field-label" htmlFor="story-summary">Editorial context <em>optional</em></label>
          <textarea id="story-summary" value={summary} onChange={(event) => setSummary(event.target.value)} maxLength={2000} rows={4} placeholder="Known context, unanswered questions, and reporting priorities…" />
          <div className="form-section-heading source-heading"><span>02</span><div><b>Source evidence</b><small>Minimum two independent snapshots</small></div><strong>{readySources.length}/{sources.length} ready</strong></div>
          <div className="source-list">
            {sources.map((source, index) => (
              <article className="source-editor" key={index}>
                <div className="source-number"><span>S{String(index + 1).padStart(2, "0")}</span>{sources.length > 2 && <button type="button" onClick={() => setSources((current) => current.filter((_, i) => i !== index))}>Remove</button>}</div>
                <div className="source-fields">
                  <input aria-label={`Source ${index + 1} title`} value={source.title} onChange={(event) => updateSource(index, "title", event.target.value)} minLength={source.url ? undefined : 3} required={!source.url} placeholder="Source title (automatic for URL capture)" />
                  <div className="source-meta"><input aria-label={`Source ${index + 1} publisher`} value={source.publisher} onChange={(event) => updateSource(index, "publisher", event.target.value)} placeholder="Publisher / author" /><input aria-label={`Source ${index + 1} URL`} value={source.url} onChange={(event) => updateSource(index, "url", event.target.value)} type="url" placeholder="URL (optional)" /></div>
                  <textarea aria-label={`Source ${index + 1} snapshot`} value={source.snapshot_text} onChange={(event) => updateSource(index, "snapshot_text", event.target.value)} minLength={source.url ? undefined : 20} required={!source.url} rows={4} placeholder={source.url ? "Leave blank to capture this URL or RSS feed automatically…" : "Paste the exact source excerpt agents may use as evidence…"} />
                  {source.url && source.snapshot_text.trim().length < 20 && <small className="capture-mode">Automatic capture · SSRF protected · credibility signals recorded</small>}
                </div>
              </article>
            ))}
          </div>
          <button className="add-source" type="button" onClick={() => setSources((current) => [...current, blankSource()])}>+ Add another source</button>
        </section>
        <aside className="launch-column"><div className="launch-sticky">
          <div className="form-section-heading"><span>03</span><div><b>Deploy the desk</b><small>Select the investigation engine</small></div></div>
          <div className="provider-list">{(Object.keys(providerDetails) as Provider[]).map((value) => <label className={`provider-option ${provider === value ? "selected" : ""}`} key={value}><input type="radio" name="provider" value={value} checked={provider === value} onChange={() => setProvider(value)} /><i /><span><b>{providerDetails[value].label}</b><small>{providerDetails[value].note}</small></span><em>{provider === value ? "Selected" : ""}</em></label>)}</div>
          <div className="deployment-plan"><div><span>01</span><p><b>Researcher</b>Extract atomic claims</p></div><div><span>02</span><p><b>Reporter</b>Build cited draft</p></div><div><span>03</span><p><b>Misinformation</b>Red-team claims</p></div><div><span>04</span><p><b>Bias auditor</b>Audit framing</p></div><div><span>05</span><p><b>Fact-checker</b>Verify evidence</p></div><div><span>06</span><p><b>Human editor</b>Make final call</p></div></div>
          {error && <p className="launch-error" role="alert">{error}</p>}
          <button className="launch-button" disabled={submitting} type="submit"><span>{submitting ? "Deploying agents…" : "Launch investigation"}</span><b>→</b></button>
          <p className="launch-note">Live runs may consume provider API quota. Every model action is logged with tokens and latency.</p>
        </div></aside>
      </form>
    </main>
  );
}
