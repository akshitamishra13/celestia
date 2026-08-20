"use client";
import { useState, type FormEvent } from "react";
import { ProtectedPage } from "@/components/layout/protected-page";
import { createCompatibility, downloadReport } from "@/lib/api/astrology";
import type { BirthDetails, Compatibility } from "@/types/astrology";
import { BirthplaceInput } from "@/components/birthplace-input";
import { PlainLanguageReport } from "@/components/plain-language-report";

function details(data: FormData, prefix: string): BirthDetails {
  const latitude = data.get(`${prefix}_latitude`);
  const longitude = data.get(`${prefix}_longitude`);
  return {
    name: String(data.get(`${prefix}_name`)),
    gender: String(data.get(`${prefix}_gender`)),
    date_of_birth: String(data.get(`${prefix}_date`)),
    time_of_birth: String(data.get(`${prefix}_time`)),
    place: String(data.get(`${prefix}_place`)),
    ...(latitude && longitude ? { latitude: Number(latitude), longitude: Number(longitude) } : {}),
  };
}
function PersonFields({ prefix, title }: { prefix: string; title: string }) {
  return (
    <fieldset>
      <legend>{title}</legend>
      <label>
        Name
        <input name={`${prefix}_name`} required />
      </label>
      <label>
        Gender / identity
        <input name={`${prefix}_gender`} placeholder="Optional" />
      </label>
      <label>
        Date of birth
        <input name={`${prefix}_date`} type="date" required />
      </label>
      <label>
        Time of birth
        <input name={`${prefix}_time`} type="time" required />
      </label>
      <BirthplaceInput name={`${prefix}_place`} />
    </fieldset>
  );
}

export default function CompatibilityPage() {
  const [result, setResult] = useState<Compatibility | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(e.currentTarget);
    try {
      setResult(
        (await createCompatibility(details(data, "a"), details(data, "b")))
          .data,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to calculate compatibility.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <ProtectedPage title="Love Compatibility">
      {result ? (
        <CompatibilityReport result={result} />
      ) : (
        <form className="flow-card compatibility-form" onSubmit={submit}>
          <p>
            Compare two profiles without making assumptions about relationship
            type or gender.
          </p>
          <div className="people-grid">
            <PersonFields prefix="a" title="Person A" />
            <PersonFields prefix="b" title="Person B" />
          </div>
          {error && <p className="flow-error">{error}</p>}
          <button className="primary-action" disabled={loading}>
            {loading ? "Calculating..." : "Calculate compatibility"}
          </button>
        </form>
      )}
    </ProtectedPage>
  );
}

function CompatibilityReport({ result }: { result: Compatibility }) {
  return (
    <div className="report-stack">
      <section className="flow-card compatibility-hero">
        <div className="score-ring">
          <strong>{result.overall_score}</strong>
          <span>of {result.maximum_score}</span>
        </div>
        <div>
          <span>VedAstro match report</span>
          <h2>
            {result.person_a.name} &amp; {result.person_b.name}
          </h2>
          <p>{result.summary}</p>
        </div>
        <button
          className="primary-action"
          onClick={() => downloadReport(result.report_id)}
        >
          Download PDF
        </button>
      </section>
      {result.components.length > 0 && (
        <section className="flow-card guna-details">
          <h2>36 Gun Milan details</h2>
          <p>Each row compares one of the eight Ashtakoot factors. The values belong to each person; points show the contribution to the overall score.</p>
          <div className="table-wrap"><table><thead><tr><th>Koota</th><th>{result.person_a.name}</th><th>{result.person_b.name}</th><th>Points</th><th>Meaning</th></tr></thead><tbody>{result.components.map((factor, index) => <tr key={`${factor.name}-${index}`}><td><strong>{factor.name}</strong>{factor.has_dosha && <small className="dosha-flag">Dosha indicated</small>}</td><td>{factor.person_a_value ?? "—"}</td><td>{factor.person_b_value ?? "—"}</td><td><strong>{factor.score ?? "—"} / {factor.maximum ?? "—"}</strong>{factor.raw_score != null && factor.score != null && factor.raw_score !== factor.score && <small>Raw: {factor.raw_score}</small>}</td><td>{factor.description}</td></tr>)}</tbody></table></div>
          {result.cancellations?.some((item) => item.applies) && <div className="cancellation-note"><strong>Applied classical adjustments</strong><ul>{result.cancellations.filter((item) => item.applies).map((item) => <li key={item.rule_id}>{item.koota.replaceAll("_", " ")}: {item.restored_points} points restored</li>)}</ul></div>}
        </section>
      )}
      <PlainLanguageReport report={result.plain_language_report} />
      <div className="two-column">
        <section className="flow-card">
          <h2>Strengths</h2>
          <ul>
            {result.strengths.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
        <section className="flow-card">
          <h2>Areas to understand</h2>
          <ul>
            {result.areas_to_understand.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
      </div>
      <section className="flow-card">
        <h2>Guidance</h2>
        <p>{result.guidance}</p>
      </section>
    </div>
  );
}
