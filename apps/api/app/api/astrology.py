from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.models.astrology import BirthChart, CompatibilityMatch, Report
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
    canvas = Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 58
    canvas.setTitle(report.title)
    canvas.setFont("Helvetica-Bold", 20); canvas.drawString(48, y, "AstroLive"); y -= 30
    canvas.setFont("Helvetica-Bold", 15); canvas.drawString(48, y, report.title); y -= 30
    canvas.setFont("Helvetica", 10)
    data = report.report_data
    lines = []
    if report.report_type == "kundli":
        profile, summary = data["profile"], data["summary"]
        lines += [f"Birth date: {profile['date_of_birth']}", f"Birth time: {profile['time_of_birth']}", f"Place: {profile['place']}", "",
            f"Lagna: {summary['lagna']}", f"Moon sign: {summary['moon_sign']}", f"Nakshatra: {summary['nakshatra']}", "", "Planetary positions"]
        lines += [f"{p['name']}: {p['sign']} {p['degree']} degrees, house {p['house']}" for p in data["planets"]]
    else:
        lines += [f"Overall compatibility: {data['overall_score']} / {data.get('maximum_score', 100)}", ""]
        lines += [f"{item.get('name', 'Factor')}: {item.get('nature', '')}" for item in data.get("components", [])]
        lines += ["", data["summary"], "", "Strengths"] + data["strengths"] + ["", "Areas to understand"] + data["areas_to_understand"]
    for line in lines:
        if y < 55: canvas.showPage(); canvas.setFont("Helvetica", 10); y = height - 55
        canvas.drawString(48, y, str(line)[:105]); y -= 17
    canvas.save(); output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="astrolive-{report.report_type}.pdf"'})
