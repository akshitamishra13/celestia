export type BirthDetails = { name: string; date_of_birth: string; time_of_birth: string; place: string; gender?: string };
export type Planet = { name: string; sign: string; degree: number; house: number; nakshatra: string };
export type Kundli = { id: string; report_id: string; profile: BirthDetails; summary: Record<string, string>; planets: Planet[]; dashas: Array<{planet: string; period: string}>; chart: Record<string, string>; interpretation: string };
export type CompatibilityFactor = { name: string; nature: string; description: string; score?: number | null; maximum?: number | null };
export type Compatibility = { id: string; report_id: string; overall_score: number; maximum_score: number; components: CompatibilityFactor[]; strengths: string[]; areas_to_understand: string[]; summary: string; guidance: string; person_a: BirthDetails; person_b: BirthDetails };
export type ReportSummary = { id: string; report_type: string; source_id: string; title: string; created_at: string };
