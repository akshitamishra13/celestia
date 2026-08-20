import json

from app.core.config import get_settings
from app.services.compatibility_interpreter import interpret_compatibility


def match_data() -> dict:
    return {"overall_score": 27, "maximum_score": 36, "components": [
        {"name": "Varna", "score": 1, "maximum": 1, "nature": "Good", "description": "Supportive values"}],
        "strengths": ["Shared values"], "areas_to_understand": ["Keep communicating"], "summary": "A supportive match", "guidance": "Reflective only",
        "person_a": {"name": "A"}, "person_b": {"name": "B"}}


def test_fallback_explains_varna_and_score() -> None:
    settings = get_settings()
    original = settings.openai_api_key
    settings.openai_api_key = ""
    try:
        result = interpret_compatibility(match_data())
    finally:
        settings.openai_api_key = original
    assert "values" in result["sections"][0]["content"].lower()
    assert "1 out of 1" in result["sections"][0]["content"]


def test_llm_uses_structured_grounded_output(monkeypatch) -> None:
    expected = {"overview": "27 of 36 explained", "sections": [{"title": "Varna", "content": "Values align."}],
        "practical_guidance": ["Talk openly."], "disclaimer": "Traditional interpretation only."}
    captured = {}

    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    settings = get_settings()
    original = settings.openai_api_key
    settings.openai_api_key = "test-key"
    monkeypatch.setattr("app.services.compatibility_interpreter.httpx.post", fake_post)
    try:
        result = interpret_compatibility(match_data())
    finally:
        settings.openai_api_key = original
    assert result["generation_method"] == "openai"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert result["sections"][0]["title"] == "Varna"
