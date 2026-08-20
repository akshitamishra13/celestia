import { apiRequest, getAccessToken } from "./client";
import type { BirthDetails, Compatibility, Kundli, PlaceSuggestion, ReportSummary } from "@/types/astrology";

type Response<T> = { success: true; data: T };
export const createKundli = (birth_details: BirthDetails) => apiRequest<Response<Kundli>>("/kundli", { method: "POST", body: JSON.stringify({ birth_details }) });
export const getLatestKundli = () => apiRequest<Response<Kundli>>("/kundli/latest");
export const createCompatibility = (person_a: BirthDetails, person_b: BirthDetails) => apiRequest<Response<Compatibility>>("/compatibility", { method: "POST", body: JSON.stringify({ person_a, person_b }) });
export const getReports = () => apiRequest<Response<ReportSummary[]>>("/reports");
export const suggestLocations = (query: string, signal?: AbortSignal) => apiRequest<Response<PlaceSuggestion[]>>(`/locations/suggest?q=${encodeURIComponent(query)}`, { signal });

export async function downloadReport(reportId: string) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
  const token = getAccessToken();
  const response = await fetch(`${base}/reports/${reportId}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Unable to download this report.");
  }
  const blob = await response.blob();
  if (blob.type !== "application/pdf" || blob.size === 0) throw new Error("The server returned an invalid PDF file.");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `celestia-report-${reportId.slice(0, 8)}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
