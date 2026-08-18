import { apiRequest } from "./client";
import type { BirthDetails, Compatibility, Kundli, ReportSummary } from "@/types/astrology";

type Response<T> = { success: true; data: T };
export const createKundli = (birth_details: BirthDetails) => apiRequest<Response<Kundli>>("/kundli", { method: "POST", body: JSON.stringify({ birth_details }) });
export const getLatestKundli = () => apiRequest<Response<Kundli>>("/kundli/latest");
export const createCompatibility = (person_a: BirthDetails, person_b: BirthDetails) => apiRequest<Response<Compatibility>>("/compatibility", { method: "POST", body: JSON.stringify({ person_a, person_b }) });
export const getReports = () => apiRequest<Response<ReportSummary[]>>("/reports");

export async function downloadReport(reportId: string) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
  const response = await fetch(`${base}/reports/${reportId}/pdf`, { credentials: "include" });
  if (!response.ok) throw new Error("Unable to download this report.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = "astrolive-report.pdf"; anchor.click(); URL.revokeObjectURL(url);
}
