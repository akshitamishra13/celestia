import json

import httpx

from app.core.config import get_settings


KOOTA_MEANINGS = {
    "varna": "Varna traditionally compares values, outlook, and the way two people approach responsibility and personal growth.",
    "vashya": "Vashya considers mutual influence, attraction, and how naturally the pair responds to one another.",
    "vasya kuta": "Vashya considers mutual influence, attraction, and how naturally the pair responds to one another.",
    "tara": "Tara, or Dina, considers wellbeing, fortune, and the supportive rhythm between the birth stars.",
    "dina kuta": "Dina, or Tara, considers wellbeing, fortune, and the supportive rhythm between the birth stars.",
    "yoni": "Yoni traditionally represents instinctive affinity, affection, and physical or emotional comfort.",
    "yoni kuta": "Yoni traditionally represents instinctive affinity, affection, and physical or emotional comfort.",
    "graha maitri": "Graha Maitri compares the friendship of the Moon-sign lords and is associated with mental rapport and communication.",
    "graha maitram": "Graha Maitri compares the friendship of the Moon-sign lords and is associated with mental rapport and communication.",
    "gana": "Gana compares temperament and behavioural style: how each person tends to react, adapt, and express themselves.",
    "bhakoot": "Bhakoot, or Rashi Kuta, considers Moon-sign dynamics connected with shared direction, emotional flow, and domestic life.",
    "rasi kuta": "Rashi Kuta, also called Bhakoot, considers Moon-sign dynamics connected with shared direction and emotional flow.",
    "nadi": "Nadi is the highest-weighted Ashtakoot factor and traditionally considers constitutional similarity and long-term vitality.",
    "nadi kuta": "Nadi is the highest-weighted Ashtakoot factor and traditionally considers constitutional similarity and long-term vitality.",
}


def _factor_section(factor: dict) -> dict[str, str]:
    name = str(factor.get("name") or "Compatibility factor")
    score, maximum = factor.get("score"), factor.get("maximum")
    meaning = KOOTA_MEANINGS.get(name.lower(), str(factor.get("description") or f"{name} is one part of the traditional compatibility calculation."))
    if score is not None and maximum:
        ratio = float(score) / float(maximum)
        result = "strong support" if ratio >= .75 else "some support with room for understanding" if ratio >= .4 else "a point that may need conscious understanding"
        why = f"This pair received {score:g} out of {maximum:g} points, which the calculation treats as {result}."
    else:
        why = f"The calculation describes this factor as {str(factor.get('nature') or 'neutral').lower()}."
    detail = str(factor.get("description") or "").strip()
    return {"title": name, "content": " ".join(filter(None, [meaning, why, detail]))}


def _fallback(data: dict) -> dict:
    score, maximum = data.get("overall_score", 0), data.get("maximum_score", 36)
    ratio = float(score) / float(maximum or 1)
    tone = "strong traditional alignment" if ratio >= .75 else "a mixed but workable traditional match" if ratio >= .5 else "several areas that deserve careful conversation"
    return {
        "overview": f"The calculated score is {score:g} out of {maximum:g}. In Ashtakoot terms, this suggests {tone}. The total is a sum of separate factors, so the individual scores explain more than the headline number alone.",
        "sections": [_factor_section(item) for item in data.get("components", [])],
        "practical_guidance": list(data.get("strengths", []))[:2] + list(data.get("areas_to_understand", []))[:2],
        "disclaimer": "This explanation interprets a traditional astrological system. It is not scientific, medical, legal, or relationship advice and does not predict relationship success.",
        "generation_method": "structured-fallback",
    }


def _output_text(response: dict) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content.get("text", ""))
    return ""


def interpret_compatibility(data: dict) -> dict:
    """Create a grounded interpretation; remain usable when an LLM is not configured."""
    fallback = _fallback(data)
    settings = get_settings()
    if not settings.openai_api_key.strip():
        return fallback
    source = {key: data.get(key) for key in ("overall_score", "maximum_score", "components", "strengths", "areas_to_understand", "summary", "guidance", "person_a", "person_b")}
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "overview": {"type": "string"},
            "sections": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {"title": {"type": "string"}, "content": {"type": "string"}}, "required": ["title", "content"]}},
            "practical_guidance": {"type": "array", "items": {"type": "string"}},
            "disclaimer": {"type": "string"},
        }, "required": ["overview", "sections", "practical_guidance", "disclaimer"],
    }
    prompt = """Explain this traditional Ashtakoot compatibility result in warm, plain language. Explain every supplied factor (including what Varna means), why its awarded points follow from the supplied values or description, relationship strengths, areas for discussion, and practical non-deterministic guidance. Never invent chart facts or scores. Do not claim astrology is scientific or predictive. Do not mention AI, language models, or how the interpretation was generated. Return only the requested structured result.\n\nDATA:\n""" + json.dumps(source, default=str)
    try:
        response = httpx.post(
            f"{settings.openai_api_url.rstrip('/')}/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json={"model": settings.openai_model, "input": prompt, "text": {"format": {"type": "json_schema", "name": "compatibility_report", "strict": True, "schema": schema}}},
            timeout=settings.provider_timeout_seconds,
        )
        response.raise_for_status()
        result = json.loads(_output_text(response.json()))
        result["generation_method"] = "openai"
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return fallback
