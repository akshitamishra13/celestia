import json

import httpx

from app.core.config import get_settings


REPORT_SECTIONS = [
    ("Core personality and life direction", "Lagna, Moon sign, Nakshatra, and the overall chart pattern"),
    ("Career and professional growth", "the 10th house, its occupants, Saturn, Sun, Mercury, Jupiter, and relevant supplied dashas"),
    ("Education and learning", "the 4th and 5th houses, Mercury, Jupiter, and the Moon"),
    ("Relationships and partnership", "the 7th house, Venus, Jupiter, Mars, and emotional patterns"),
    ("Money and resources", "the 2nd and 11th houses and their supplied planetary occupants"),
    ("Home and family", "the 2nd and 4th houses, Moon, and domestic themes"),
    ("Wellbeing and personal balance", "the 1st and 6th houses and general routines; do not give medical advice"),
    ("Current periods and timing", "only the Vimshottari Dasha periods included in the source data"),
]


def _planet_summary(data: dict) -> str:
    planets = data.get("planets", [])
    return "; ".join(f"{p.get('name')} in {p.get('sign')}, house {p.get('house')}" for p in planets)


def _house_planets(data: dict, *houses: int) -> str:
    names = [str(p.get("name")) for p in data.get("planets", []) if p.get("house") in houses]
    return ", ".join(names) if names else "no planets directly placed there"


def _planet(data: dict, name: str) -> dict:
    return next((p for p in data.get("planets", []) if str(p.get("name", "")).lower() == name.lower()), {})


def _placement(data: dict, name: str) -> str:
    planet = _planet(data, name)
    return f"{name} in {planet.get('sign')}, house {planet.get('house')}" if planet else f"the {name} placement"


def _fallback(data: dict) -> dict:
    summary = data.get("summary", {})
    lagna = summary.get("lagna", "the calculated ascendant")
    moon = summary.get("moon_sign", "the calculated Moon sign")
    nakshatra = summary.get("nakshatra", "the calculated Nakshatra")
    dashas = data.get("dashas", [])
    sections = [
        {"title": "Core personality and life direction", "content": f"With {lagna} rising, you may come across in the direct, exploratory, and growth-oriented style traditionally associated with this Lagna. A {moon} Moon suggests that you process feelings through the qualities associated with {moon}, while {nakshatra} adds intensity to the way you set goals and relate to other people. In everyday life, this combination can make you eager to move forward while still needing emotional balance and fairness before you feel settled."},
        {"title": "Career and professional growth", "content": f"The 10th house contains {_house_planets(data, 10)}. Along with {_placement(data, 'Saturn')}, {_placement(data, 'Sun')}, and {_placement(data, 'Mercury')}, this points to the working style shown by the chart. In practical terms, these placements describe whether you are more comfortable leading, organising, communicating, analysing, or building patiently. Career progress is likely to feel strongest when your role gives these qualities a useful outlet; difficult placements can show where consistency, authority, or workplace communication needs extra attention."},
        {"title": "Education and learning", "content": f"The education houses contain {_house_planets(data, 4, 5)}, while {_placement(data, 'Mercury')} describes information processing and {_placement(data, 'Jupiter')} describes broader understanding. In normal terms, this combination suggests the kinds of subjects and learning environments that may hold your attention. It can also show whether you learn best through structure, discussion, experimentation, repetition, or independent study, and where distraction or confidence may affect progress."},
        {"title": "Relationships and partnership", "content": f"The 7th house contains {_house_planets(data, 7)}; {_placement(data, 'Venus')} describes affection and relating, while {_placement(data, 'Mars')} describes drive and conflict response. Together with the {moon} Moon, these placements suggest how you seek closeness and react when needs differ. In everyday relationships, the supportive side can appear as warmth, loyalty, attraction, or cooperation; the challenging side may require clearer communication, patience, and room for both people to make decisions."},
        {"title": "Money and resources", "content": f"The income and gains houses contain {_house_planets(data, 2, 11)}. These houses, together with Jupiter and Mercury, are traditionally used to understand earning habits, saving, speech, networks, and long-term gains. In practical life, the pattern can show whether money develops more naturally through personal skill, communication, leadership, steady employment, business contacts, or patient accumulation, as well as where impulsive or unclear decisions deserve attention."},
        {"title": "Home and family", "content": f"The family and home houses contain {_house_planets(data, 2, 4)}, and the Moon is placed in {moon}. This combination describes the atmosphere that helps you feel secure. In day-to-day life, it may affect how strongly you value privacy, harmony, movement, family involvement, or a stable home base, and how readily you express feelings with relatives."},
        {"title": "Wellbeing and personal balance", "content": f"The 1st and 6th houses contain {_house_planets(data, 1, 6)}. Traditionally, these placements describe vitality, routines, workload, and the way stress is handled. In normal terms, the chart encourages awareness of how work patterns, rest, movement, and emotional habits affect your balance; challenging themes are best treated as reminders to build sustainable routines rather than as health predictions."},
        {"title": "Current periods and timing", "content": "The supplied Vimshottari periods are " + (", ".join(f"{d.get('planet')} ({d.get('period')})" for d in dashas) or "not available") + ". A planet's period traditionally brings its natal sign and house topics into stronger focus. In everyday terms, this can describe the kinds of responsibilities, opportunities, relationships, or inner priorities that may demand more attention during the period, but it does not guarantee a specific event."},
    ]
    return {
        "overview": f"This Kundli has {lagna} rising, the Moon in {moon}, and the Moon in {nakshatra} Nakshatra. The interpretation below connects those foundations with the supplied planetary houses and dashas across major areas of life.",
        "sections": sections,
        "practical_guidance": [],
        "disclaimer": "",
        "interpretation_version": "kundli-v2",
        "generation_method": "structured-fallback",
    }


def _output_text(response: dict) -> str:
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return str(content.get("text", ""))
    return ""


def interpret_kundli(data: dict) -> dict:
    """Generate a chart-grounded traditional interpretation with an offline fallback."""
    fallback = _fallback(data)
    settings = get_settings()
    if not settings.openai_api_key.strip():
        return fallback
    source = {key: data.get(key) for key in ("profile", "summary", "planets", "dashas", "chart", "calculation")}
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "overview": {"type": "string"},
            "sections": {"type": "array", "minItems": 8, "maxItems": 8, "items": {"type": "object", "additionalProperties": False, "properties": {"title": {"type": "string"}, "content": {"type": "string"}}, "required": ["title", "content"]}},
        }, "required": ["overview", "sections"],
    }
    required = ", ".join(title for title, _ in REPORT_SECTIONS)
    prompt = f"""Write a detailed Vedic Kundli interpretation using only the supplied calculated chart. Return exactly eight sections, in this order: {required}. For every section, first connect the relevant supplied signs, houses, planets, Nakshatra, or dashas, then clearly explain their likely effect on the person's real daily life in simple, natural English. Describe recognizable tendencies, strengths, challenges, decisions, work style, study style, emotional needs, and relationship behaviour rather than merely defining astrological terms. Use 120-180 words per section. Do not add a practical-guidance section or disclaimer. Do not invent aspects, yogas, dignities, house lords, conjunctions, dates, remedies, or events not present in the data. Avoid deterministic predictions and medical claims. Do not mention AI, language models, or how the report was generated. Return only the requested structured result.\n\nCHART DATA:\n{json.dumps(source, default=str)}"""
    try:
        response = httpx.post(f"{settings.openai_api_url.rstrip('/')}/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            json={"model": settings.openai_model, "input": prompt, "text": {"format": {"type": "json_schema", "name": "kundli_report", "strict": True, "schema": schema}}},
            timeout=settings.provider_timeout_seconds)
        response.raise_for_status()
        result = json.loads(_output_text(response.json()))
        result["practical_guidance"] = []
        result["disclaimer"] = ""
        result["interpretation_version"] = "kundli-v2"
        result["generation_method"] = "openai"
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return fallback
