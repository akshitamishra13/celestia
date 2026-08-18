from datetime import date, time
from uuid import uuid4

from app.models.astrology import BirthProfile
from app.providers.astrology import VedAstroProvider


def profile(name: str = "Test Person") -> BirthProfile:
    return BirthProfile(id=uuid4(), user_id=uuid4(), name=name, date_of_birth=date(1998, 5, 14), time_of_birth=time(10, 30),
        birth_place="Kanpur, India", canonical_place="Kanpur, Uttar Pradesh, India", latitude="26.449900", longitude="80.331900", timezone="Asia/Kolkata")


def test_vedastro_chart_normalization(monkeypatch) -> None:
    provider = VedAstroProvider()
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    raw = {
        "LagnaSignName": "Leo",
        "AllPlanetLongitude": [{"Planet": planet, "Longitude": index * 35.5 + 10} for index, planet in enumerate(planets)],
        "AllPlanetRasiSigns": [{"Planet": planet, "Sign": "Leo"} for planet in planets],
        "HouseAllPlanetOccupiesBasedOnLongitudes": [{"Planet": planet, "House": f"House{index % 12 + 1}"} for index, planet in enumerate(planets)],
        "AllPlanetConstellation": [{"Planet": planet, "Constellation": "Magha"} for planet in planets],
        "DasaForNow": {"Mahadasa": "Jupiter", "Antardasa": "Saturn"},
    }
    dasha = {"Jupiter": {"Lord": "Jupiter", "Nature": "Good", "Description": "Jupiter Dasa", "SubDasas": {
        "Saturn": {"Lord": "Saturn", "Nature": "Neutral", "Description": "Saturn Bhukti"}}}}
    monkeypatch.setattr(provider, "_call", lambda method, payload: dasha if method == "DasaForNow" else raw)
    chart = provider.generate_birth_chart(profile())
    assert chart["summary"]["lagna"] == "Leo"
    assert chart["summary"]["current_mahadasha"] == "Jupiter"
    assert len(chart["planets"]) == 9
    assert chart["calculation"]["provider"] == "vedastro"


def test_vedastro_match_normalization(monkeypatch) -> None:
    provider = VedAstroProvider()
    raw = {"KutaScore": 72, "Summary": {"ScoreSummary": "Supportive match"}, "PredictionList": [
        {"Name": "Nadi Kuta", "Nature": "Good", "Description": "Supportive"},
        {"Name": "Vasya Kuta", "Nature": "Bad", "Description": "Requires understanding"},
    ]}
    monkeypatch.setattr(provider, "_call", lambda method, payload: raw)
    result = provider.generate_compatibility(profile("A"), profile("B"))
    assert result["overall_score"] == 72
    assert result["components"][0]["name"] == "Nadi Kuta"
    assert "Nadi Kuta" in result["strengths"][0]
