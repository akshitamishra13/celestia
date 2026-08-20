import type { PlainLanguageReport as Report } from "@/types/astrology";

export function PlainLanguageReport({ report, showSupplementary = true }: { report?: Report; showSupplementary?: boolean }) {
  if (!report) return null;
  return <section className="flow-card plain-language-report"><span>Detailed interpretation</span><h2>Your results, in everyday language</h2><p>{report.overview}</p>{report.sections.map((section) => <div key={section.title}><h3>{section.title}</h3><p>{section.content}</p></div>)}{showSupplementary && report.practical_guidance.length > 0 && <div><h3>Practical guidance</h3><ul>{report.practical_guidance.map((item) => <li key={item}>{item}</li>)}</ul></div>}{showSupplementary && report.disclaimer && <p className="prototype-note">{report.disclaimer.replace(/^This AI-assisted explanation /i, "This explanation ")}</p>}</section>;
}
