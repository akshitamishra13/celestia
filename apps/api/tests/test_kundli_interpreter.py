import json

from app.core.config import get_settings
from app.services.kundli_interpreter import interpret_kundli


def chart_data() -> dict:
    return {"profile": {"name": "A"}, "summary": {"lagna": "Leo", "moon_sign": "Taurus", "nakshatra": "Rohini"},
        "planets": [{"name": "Sun", "sign": "Leo", "house": 1}, {"name": "Moon", "sign": "Taurus", "house": 10}],
        "dashas": [{"planet": "Jupiter", "period": "2026-2032"}], "chart": {"1": "Sun", "10": "Moon"}, "calculation": {"provider": "mock"}}


def test_fallback_covers_major_life_areas() -> None:
    settings = get_settings()
    original = settings.openai_api_key
    settings.openai_api_key = ""
    try:
        result = interpret_kundli(chart_data())
    finally:
        settings.openai_api_key = original
    titles = {section["title"] for section in result["sections"]}
    assert len(result["sections"]) == 8
    assert {"Career and professional growth", "Education and learning", "Relationships and partnership"} <= titles
    assert "Leo" in result["overview"]
    assert result["practical_guidance"] == []
    assert result["disclaimer"] == ""
    assert "In everyday life" in result["sections"][0]["content"]


def test_llm_request_is_structured_and_chart_grounded(monkeypatch) -> None:
    fallback = interpret_kundli(chart_data())
    expected = {key: fallback[key] for key in ("overview", "sections")}
    captured = {}

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    settings = get_settings()
    original = settings.openai_api_key
    settings.openai_api_key = "test-key"
    monkeypatch.setattr("app.services.kundli_interpreter.httpx.post", fake_post)
    try:
        result = interpret_kundli(chart_data())
    finally:
        settings.openai_api_key = original
    assert result["generation_method"] == "openai"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert "Moon" in captured["input"]
