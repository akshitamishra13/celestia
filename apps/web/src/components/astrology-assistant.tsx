"use client";

import { useState, type FormEvent } from "react";
import { askAstrology, downloadReport, generateAstrologyReport } from "@/lib/api/astrology";
import type { AssistantResult } from "@/types/astrology";

export function AstrologyAssistant() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError("");
    try { setResult((await askAstrology(question)).data); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to answer right now."); }
    finally { setBusy(false); }
  }

  async function report() {
    setBusy(true); setError("");
    try { setResult((await generateAstrologyReport()).data); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to create the report."); }
    finally { setBusy(false); }
  }

  return <section className="flow-card assistant-card">
    <div className="assistant-heading"><div><span>Knowledge grounded assistant</span><h2>Ask about your Kundli</h2><p>Answers use your calculated chart, retrieved reference passages, and linked astrology concepts.</p></div><button className="secondary-action" type="button" disabled={busy} onClick={report}>Generate personalized overview</button></div>
    <form className="assistant-form" onSubmit={submit}><label htmlFor="assistant-question">Your question</label><div><input id="assistant-question" value={question} onChange={e => setQuestion(e.target.value)} minLength={3} maxLength={1000} placeholder="For example, what does Mercury's placement suggest about learning?" required/><button className="primary-action" disabled={busy}>{busy ? "Working…" : "Ask"}</button></div></form>
    {error && <p className="flow-error">{error}</p>}
    {result && <div className="assistant-result"><h3>{result.kind === "personalized-report" ? "Your personalized overview" : "Astrology assistant"}</h3><p className="assistant-answer">{result.answer}</p>
      {result.report_id && <button className="secondary-action" type="button" onClick={() => downloadReport(result.report_id!)}>Download this report as PDF</button>}
      <h4>Sources</h4><ol className="assistant-citations">{result.citations.map(c => <li key={c.id}><strong>[{c.id}] {c.title}</strong> — {c.url ? <a href={c.url} target="_blank" rel="noreferrer">{c.source}</a> : c.source}</li>)}</ol>
      <details><summary>How this answer was assembled</summary><p>Vector index: {result.retrieval.index}; encoder: {result.retrieval.embedding_model}; response time: {result.latency_ms} ms.</p>{result.graph_context.length > 0 && <p>Connected concepts: {result.graph_context.join(", ")}</p>}<p>Verified chart facts: {result.chart_facts.join(" · ")}</p></details>
    </div>}
  </section>;
}
