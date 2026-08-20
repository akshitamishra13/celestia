"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ProtectedPage } from "@/components/layout/protected-page";
import { ApiError } from "@/lib/api/client";
import {
  createKundli,
  downloadReport,
  getLatestKundli,
} from "@/lib/api/astrology";
import type { Kundli } from "@/types/astrology";
import { PlainLanguageReport } from "@/components/plain-language-report";
import { BirthplaceInput } from "@/components/birthplace-input";

export default function KundliPage() {
  const [kundli, setKundli] = useState<Kundli | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getLatestKundli()
      .then((response) => setKundli(response.data))
      .catch((caught: unknown) => {
        if (caught instanceof ApiError && caught.status === 404)
          setShowForm(true);
        else
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load your Kundli.",
          );
      })
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await createKundli({
        name: String(data.get("name")),
        date_of_birth: String(data.get("date")),
        time_of_birth: String(data.get("time")),
        place: String(data.get("place")),
        ...(data.get("latitude") && data.get("longitude")
          ? { latitude: Number(data.get("latitude")), longitude: Number(data.get("longitude")) }
          : {}),
      });
      setKundli(response.data);
      setShowForm(false);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to generate Kundli.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <ProtectedPage title="Your Vedic Birth Chart">
      {loading ? (
        <div className="flow-card flow-status">
          Resolving your birthplace and calculating your chart...
        </div>
      ) : showForm || !kundli ? (
        <form className="flow-card astro-form" onSubmit={submit}>
          <h2>{kundli ? "Create another Kundli" : "Create your Kundli"}</h2>
          <p>
            Enter the exact locality, city, PIN and country for the most
            accurate coordinates. Existing calculations remain available in
            report history.
          </p>
          <label>
            Full name
            <input name="name" required minLength={2} />
          </label>
          <div className="form-grid">
            <label>
              Date of birth
              <input
                name="date"
                type="date"
                max={new Date().toISOString().slice(0, 10)}
                required
              />
            </label>
            <label>
              Time of birth
              <input name="time" type="time" required />
            </label>
          </div>
          <BirthplaceInput />
          {error && <p className="flow-error">{error}</p>}
          <div className="form-actions">
            {kundli && (
              <button
                type="button"
                className="secondary-action"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
            )}
            <button className="primary-action">Generate live Kundli</button>
          </div>
        </form>
      ) : (
        <KundliReport
          kundli={kundli}
          onCreateAnother={() => {
            setError("");
            setShowForm(true);
          }}
        />
      )}
    </ProtectedPage>
  );
}

function KundliReport({
  kundli,
  onCreateAnother,
}: {
  kundli: Kundli;
  onCreateAnother: () => void;
}) {
  return (
    <>
      <PlainLanguageReport report={kundli.plain_language_report} />
      <KundliCalculation kundli={kundli} onCreateAnother={onCreateAnother} />
    </>
  );
}

function KundliCalculation({
  kundli,
  onCreateAnother,
}: {
  kundli: Kundli;
  onCreateAnother: () => void;
}) {
  return (
    <div className="report-stack">
      <section className="flow-card report-hero">
        <div>
          <span>Personal report</span>
          <h2>{kundli.profile.name}&apos;s Vedic Birth Chart</h2>
          <p>
            {kundli.profile.date_of_birth} · {kundli.profile.time_of_birth} ·{" "}
            {kundli.profile.place}
          </p>
        </div>
        <div className="form-actions">
          <button className="secondary-action" onClick={onCreateAnother}>
            Create another Kundli
          </button>
          <button
            className="primary-action"
            onClick={() => downloadReport(kundli.report_id)}
          >
            Download PDF
          </button>
        </div>
      </section>
      <section className="summary-grid">
        {Object.entries(kundli.summary).map(([key, value]) => (
          <article className="stat-tile" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>
      <section className="flow-card">
        <h2>North Indian chart</h2>
        <div className="kundli-chart">
          {Array.from({ length: 12 }, (_, index) => (
            <div key={index}>
              <span>{index + 1}</span>
              <strong>{kundli.chart[String(index + 1)] ?? "—"}</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="flow-card">
        <h2>Planetary positions</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Planet</th>
                <th>Sign</th>
                <th>Degree</th>
                <th>House</th>
                <th>Nakshatra</th>
              </tr>
            </thead>
            <tbody>
              {kundli.planets.map((planet) => (
                <tr key={planet.name}>
                  <td>{planet.name}</td>
                  <td>{planet.sign}</td>
                  <td>{planet.degree}°</td>
                  <td>{planet.house}</td>
                  <td>{planet.nakshatra}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="flow-card">
        <h2>Vimshottari Dasha</h2>
        <div className="dasha-list">
          {kundli.dashas.map((dasha) => (
            <div key={dasha.period}>
              <strong>{dasha.planet}</strong>
              <span>{dasha.period}</span>
            </div>
          ))}
        </div>
        <p className="prototype-note">{kundli.interpretation}</p>
      </section>
    </div>
  );
}
