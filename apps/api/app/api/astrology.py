from io import BytesIO
from xml.sax.saxutils import escape
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.models.astrology import BirthChart, BirthProfile, CompatibilityMatch, Report
from app.schemas.astrology import CompatibilityRequest, DataResponse, KundliRequest
from app.services.astrology_service import AstrologyService

router = APIRouter(tags=["astrology"])


def chart_payload(chart: BirthChart, report: Report) -> dict:
    return {"id": str(chart.id), "report_id": str(report.id), **chart.chart_data}


@router.post("/kundli", response_model=DataResponse)
def create_kundli(payload: KundliRequest, user: CurrentUser, database: DatabaseDependency) -> DataResponse:
    service = AstrologyService(database, user.id)
    if payload.birth_profile_id:
        profile = service.get_profile(payload.birth_profile_id)
    elif payload.birth_details:
        profile = service.create_profile(payload.birth_details)
    else:
        raise HTTPException(status_code=422, detail="Provide a saved profile or birth details.")
    chart = service.chart_for_profile(profile)
    report = service.ensure_report("kundli", chart.id, f"{profile.name}'s Kundli", chart.chart_data)
    service.commit()
    return DataResponse(data=chart_payload(chart, report))


@router.get("/kundli/latest", response_model=DataResponse)
def latest_kundli(user: CurrentUser, database: DatabaseDependency) -> DataResponse:
    report = database.scalar(select(Report).where(Report.user_id == user.id, Report.report_type == "kundli").order_by(Report.created_at.desc()))
    if not report:
        raise HTTPException(status_code=404, detail="No Kundli has been created yet.")
    chart = database.scalar(select(BirthChart).where(BirthChart.id == report.source_id))
    profile = database.scalar(select(BirthProfile).where(BirthProfile.id == chart.birth_profile_id))
    service = AstrologyService(database, user.id)
    chart = service.chart_for_profile(profile)
    report = service.ensure_report("kundli", chart.id, report.title, chart.chart_data)
    service.commit()
    return DataResponse(data=chart_payload(chart, report))


@router.post("/compatibility", response_model=DataResponse)
def create_compatibility(payload: CompatibilityRequest, user: CurrentUser, database: DatabaseDependency) -> DataResponse:
    service = AstrologyService(database, user.id)
    a = service.reference_chart_for_profile(service.create_profile(payload.person_a))
    b = service.reference_chart_for_profile(service.create_profile(payload.person_b))
    match = service.compatibility(a, b)
    report = service.ensure_report("compatibility", match.id, f"{payload.person_a.name} & {payload.person_b.name}", match.result_data)
    service.commit()
    return DataResponse(data={"id": str(match.id), "report_id": str(report.id), **match.result_data})


@router.get("/reports", response_model=DataResponse)
def reports(user: CurrentUser, database: DatabaseDependency) -> DataResponse:
    items = database.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc())).all()
    return DataResponse(data=[{"id": str(item.id), "report_type": item.report_type, "source_id": str(item.source_id),
        "title": item.title, "created_at": item.created_at.isoformat()} for item in items])


@router.get("/reports/{report_id}", response_model=DataResponse)
def report_detail(report_id: UUID, user: CurrentUser, database: DatabaseDependency) -> DataResponse:
    report = database.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return DataResponse(data={"id": str(report.id), "report_type": report.report_type, "title": report.title, **report.report_data})


@router.get("/reports/{report_id}/pdf")
def report_pdf(report_id: UUID, user: CurrentUser, database: DatabaseDependency) -> StreamingResponse:
    report = database.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=13 * mm, leftMargin=13 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title=report.title, author="AstroLive")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", parent=styles["Title"], fontSize=17, leading=19, textColor=colors.HexColor("#BD5224"), alignment=TA_CENTER, spaceAfter=2))
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Heading1"], fontSize=15, leading=18, textColor=colors.HexColor("#4A2D32"), alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=12, leading=14, textColor=colors.HexColor("#4A2D32"), spaceBefore=7, spaceAfter=3))
    styles.add(ParagraphStyle(name="BodySoft", parent=styles["BodyText"], fontSize=8.5, textColor=colors.HexColor("#5F5149"), leading=11.5, spaceAfter=4))
    story = [Paragraph("AstroLive", styles["Brand"]), Paragraph(escape(report.title), styles["ReportTitle"])]
    data = report.report_data
    if report.report_type == "kundli":
        profile, summary = data["profile"], data["summary"]
        story += [Paragraph("Birth details", styles["Section"]), Paragraph(escape(f"Birth date: {profile['date_of_birth']} | Birth time: {profile['time_of_birth']} | Place: {profile['place']}"), styles["BodySoft"]),
            Paragraph("Chart summary", styles["Section"]), Paragraph(escape(f"Lagna: {summary['lagna']} | Moon sign: {summary['moon_sign']} | Nakshatra: {summary['nakshatra']}"), styles["BodySoft"]),
            Paragraph("Planetary positions", styles["Section"])]
        rows = [["Planet", "Sign", "Degree", "House"]] + [[str(p["name"]), str(p["sign"]), str(p["degree"]), str(p["house"])] for p in data["planets"]]
        story.append(Table(rows, colWidths=[42 * mm, 42 * mm, 35 * mm, 28 * mm], repeatRows=1, style=_table_style()))
        dashas = data.get("dashas", [])
        if dashas:
            story.append(Paragraph("Vimshottari Dasha", styles["Section"]))
            dasha_rows = [["Planet", "Period"]] + [[str(item.get("planet", "")), str(item.get("period", ""))] for item in dashas]
            story.append(Table(dasha_rows, colWidths=[55 * mm, 112 * mm], repeatRows=1, style=_table_style()))
        interpretation = data.get("plain_language_report") or {}
        if interpretation:
            story += [Paragraph("Detailed Kundli interpretation", styles["Section"]), Paragraph(escape(str(interpretation.get("overview", ""))), styles["BodySoft"])]
            for section in interpretation.get("sections", []):
                story += [Paragraph(escape(str(section.get("title", "Life area"))), styles["Section"]), Paragraph(escape(str(section.get("content", ""))), styles["BodySoft"])]
    else:
        score = f"{data['overall_score']} / {data.get('maximum_score', 36)}"
        story += [Paragraph("Compatibility overview", styles["Section"]), Paragraph(f"<b>Overall score: {escape(score)}</b>", styles["BodySoft"]), Paragraph(escape(str(data.get("summary", ""))), styles["BodySoft"])]
        components = data.get("components", [])
        if components:
            story.append(Paragraph("Ashtakoot factor breakdown", styles["Section"]))
            rows = [["Factor", "Score", "Assessment"]]
            for item in components:
                points = f"{item.get('score', '-')} / {item.get('maximum', '-')}"
                rows.append([Paragraph(escape(str(item.get("name", "Factor"))), styles["BodyText"]), points, str(item.get("nature", ""))])
            story.append(Table(rows, colWidths=[70 * mm, 42 * mm, 55 * mm], repeatRows=1, style=_table_style()))
        interpretation = data.get("plain_language_report") or {}
        if interpretation:
            story += [Paragraph("Your results in everyday language", styles["Section"]), Paragraph(escape(str(interpretation.get("overview", ""))), styles["BodySoft"])]
            for section in interpretation.get("sections", []):
                story += [Paragraph(escape(str(section.get("title", "Factor"))), styles["Section"]), Paragraph(escape(str(section.get("content", ""))), styles["BodySoft"])]
            guidance = interpretation.get("practical_guidance", [])
            if guidance:
                story.append(Paragraph("Practical guidance", styles["Section"]))
                story.extend(Paragraph(f"- {escape(str(item))}", styles["BodySoft"]) for item in guidance)
            disclaimer = str(interpretation.get("disclaimer", "")).replace("This AI-assisted explanation ", "This explanation ")
            story += [Spacer(1, 3), Paragraph(escape(disclaimer), styles["BodySoft"])]
    document.build(story)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="astrolive-{report.report_type}.pdf"'})


def _table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A2D32")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#EADBCA")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFFAF2")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
