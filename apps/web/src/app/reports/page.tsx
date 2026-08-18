"use client";
import { useEffect, useState } from "react";
import { ProtectedPage } from "@/components/layout/protected-page";
import { downloadReport, getReports } from "@/lib/api/astrology";
import type { ReportSummary } from "@/types/astrology";

export default function ReportsPage() { const [reports, setReports] = useState<ReportSummary[]>([]); const [loading, setLoading] = useState(true); useEffect(() => { getReports().then(r => setReports(r.data)).finally(() => setLoading(false)); }, []); return <ProtectedPage title="Your Reports"><section className="flow-card">{loading ? <p>Loading reports...</p> : reports.length === 0 ? <div className="flow-status"><h2>No reports yet</h2><p>Create a Kundli or compatibility report to revisit it here.</p></div> : <div className="report-list">{reports.map(report => <article key={report.id}><div><span>{report.report_type}</span><h2>{report.title}</h2><p>Generated {new Date(report.created_at).toLocaleDateString("en-IN")}</p></div><button className="secondary-action" onClick={() => downloadReport(report.id)}>Download PDF</button></article>)}</div>}</section></ProtectedPage>; }
