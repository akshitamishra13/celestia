from datetime import date, time
from uuid import uuid4

from app.models.astrology import BirthProfile
from app.providers.astrology import NavamshaProvider, ProviderError


def profile(name: str = "Test Person", gender: str | None = None) -> BirthProfile:
    return BirthProfile(id=uuid4(), user_id=uuid4(), name=name, gender=gender, date_of_birth=date(1998, 5, 14),
        time_of_birth=time(10, 30), birth_place="Kanpur, India", canonical_place="Kanpur, Uttar Pradesh, India",
        latitude="26.449900", longitude="80.331900", timezone="Asia/Kolkata")


def test_navamsha_chart_normalization(monkeypatch) -> None:
    provider = NavamshaProvider()
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    chart_response = {"ascendant": {"zodiac_sign_name": "Leo", "longitude": 130}, "planets": {
        name: {"zodiac_sign_name": "Leo", "longitude": 130 + index, "nakshatra_name": "Magha", "nakshatra_pada": 2}
        for index, name in enumerate(planets)}}
    dasha_response = {"mahadasha": {"planet": "Jupiter", "start_date": "2020-01-01", "end_date": "2036-01-01"},
        "antardasha": {"planet": "Saturn"}}
    monkeypatch.setattr(provider, "_call", lambda path, payload: dasha_response if path == "dasha/current" else chart_response)
    result = provider.generate_birth_chart(profile())
    assert result["summary"]["lagna"] == "Leo"
    assert result["summary"]["current_mahadasha"] == "Jupiter"
    assert len(result["planets"]) == 9
    assert result["calculation"]["provider"] == "navamsha"


def test_navamsha_chart_survives_temporary_dasha_failure(monkeypatch) -> None:
    provider = NavamshaProvider()
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    chart_response = {"ascendant": {"zodiac_sign_name": "Leo", "longitude": 130}, "planets": {
        name: {"zodiac_sign_name": "Leo", "longitude": 130 + index, "nakshatra_name": "Magha", "nakshatra_pada": 2}
        for index, name in enumerate(planets)}}

    def fake_call(path, payload):
        if path == "dasha/current":
            raise ProviderError("Temporary Dasha outage")
        return chart_response

    monkeypatch.setattr(provider, "_call", fake_call)
    result = provider.generate_birth_chart(profile())
    assert len(result["planets"]) == 9
    assert result["dashas"] == []
    assert result["summary"]["current_mahadasha"] == "Not returned"


def test_navamsha_compatibility_normalization(monkeypatch) -> None:
    provider = NavamshaProvider()
    response = {"total_score": 27, "maximum_score": 36, "breakdown": {
        "varna": {"score": 1, "max_score": 1, "description": "Supportive values"},
        "nadi": {"score": 0, "max_score": 8, "description": "Requires consideration"}}}
    captured = {}
    def fake_call(path, payload):
        captured.update({"path": path, "payload": payload})
        return response
    monkeypatch.setattr(provider, "_call", fake_call)
    result = provider.generate_compatibility(profile("A", "female"), profile("B", "male"))
    assert captured["path"] == "compatibility/ashtakoot/detailed"
    assert captured["payload"]["bride"]["timezone"] == 5.5
    assert result["overall_score"] == 27
    assert result["maximum_score"] == 36
    assert result["components"][0]["name"] == "Varna"
