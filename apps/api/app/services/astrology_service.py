import hashlib
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.astrology import BirthChart, BirthProfile, CompatibilityMatch, Report
from app.providers.astrology import NAKSHATRAS, PLANETS, SIGNS, NavamshaProvider, ProviderError, VedAstroProvider, _profile_data
from app.schemas.astrology import BirthDetails
from app.services.location_service import LocationService
from app.services.compatibility_interpreter import interpret_compatibility
from app.services.kundli_interpreter import interpret_kundli


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _profile_key(profile: BirthProfile) -> str:
    return f"{profile.date_of_birth}|{profile.time_of_birth}|{profile.latitude}|{profile.longitude}|{profile.timezone}"


class MockAstrologyProvider:
    name, version = "mock", "v1"

    def generate_birth_chart(self, profile: BirthProfile) -> dict:
        key = digest(f"{_profile_key(profile)}|lahiri|whole_sign|v1")
        seed = int(key[:12], 16); lagna = SIGNS[seed % 12]
        planets = []
        for index, planet in enumerate(PLANETS):
            value = seed // (index + 1); longitude = float(value % 36000) / 100; sign = SIGNS[int(longitude // 30) % 12]
            planets.append({"name": planet, "sign": sign, "degree": round(longitude % 30, 2), "longitude": longitude,
                "house": ((SIGNS.index(sign) - SIGNS.index(lagna)) % 12) + 1, "nakshatra": NAKSHATRAS[int(longitude / (360 / 27)) % 27], "pada": 1})
        moon = planets[1]; chart = {}
        for planet in planets: chart[str(planet["house"])] = ", ".join(filter(None, [chart.get(str(planet["house"])), planet["name"]]))
        dashas = [{"planet": PLANETS[(seed + i) % 7], "period": f"{2026 + i * 2}-{2028 + i * 2}"} for i in range(4)]
        return {"profile": _profile_data(profile), "summary": {"lagna": lagna, "moon_sign": moon["sign"], "nakshatra": moon["nakshatra"],
            "current_mahadasha": dashas[0]["planet"], "current_antardasha": dashas[1]["planet"]}, "planets": planets, "dashas": dashas, "chart": chart,
            "interpretation": "Deterministic test data. Enable VedAstro for live calculations.",
            "calculation": {"provider": "mock", "version": "v1", "ayanamsha": "lahiri", "house_system": "whole_sign"}}

    def generate_compatibility(self, a: BirthProfile, b: BirthProfile) -> dict:
        key = digest("|".join(sorted([_profile_key(a), _profile_key(b)])) + "|v2"); score = 55 + int(key[:4], 16) % 40
        components = [{"name": name, "nature": "Good" if score >= 70 else "Neutral", "description": "Deterministic test factor.", "score": score, "maximum": 100}
            for name in ["Emotional", "Communication", "Lifestyle", "Long-term"]]
        return {"overall_score": score, "maximum_score": 100, "components": components, "strengths": ["Deterministic supportive test factor."],
            "areas_to_understand": ["Deterministic reflective test factor."], "summary": "Deterministic compatibility data for offline development.",
            "guidance": "Mock output is not an astrological reading.", "person_a": _profile_data(a), "person_b": _profile_data(b),
            "calculation": {"provider": "mock", "version": "v2"}}


class AstrologyService:
    def __init__(self, database: Session, user_id: UUID):
        self.database, self.user_id, self.settings = database, user_id, get_settings()
        providers = {"navamsha": NavamshaProvider, "vedastro": VedAstroProvider, "mock": MockAstrologyProvider}
        provider_name = self.settings.astrology_provider.lower()
        if provider_name not in providers:
            raise RuntimeError(f"Unsupported ASTROLOGY_PROVIDER: {provider_name}")
        self.provider = providers[provider_name]()

    def create_profile(self, details: BirthDetails) -> BirthProfile:
        if self.settings.astrology_provider.lower() == "mock":
            canonical, latitude, longitude, timezone = details.place.title(), 26.4499, 80.3319, "Asia/Kolkata"
        else:
            location = LocationService().resolve(details.place)
            canonical, latitude, longitude, timezone = location.canonical_name, location.latitude, location.longitude, location.timezone
        profile = BirthProfile(user_id=self.user_id, name=details.name, gender=details.gender or None, date_of_birth=details.date_of_birth, time_of_birth=details.time_of_birth,
            birth_place=details.place, canonical_place=canonical, latitude=f"{latitude:.6f}", longitude=f"{longitude:.6f}", timezone=timezone)
        self.database.add(profile); self.database.flush(); return profile

    def get_profile(self, profile_id: UUID) -> BirthProfile:
        profile = self.database.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.user_id == self.user_id))
        if not profile: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Birth profile not found.")
        return profile

    def chart_for_profile(self, profile: BirthProfile) -> BirthChart:
        key = digest(f"{_profile_key(profile)}|{self.settings.astrology_ayanamsha}|whole_sign|{self.provider.name}|{self.provider.version}")
        existing = self.database.scalar(select(BirthChart).where(BirthChart.birth_profile_id == profile.id, BirthChart.calculation_key == key))
        if existing:
            if existing.chart_data.get("plain_language_report", {}).get("interpretation_version") != "kundli-v2":
                existing.chart_data = {**existing.chart_data, "plain_language_report": interpret_kundli(existing.chart_data)}
            return existing
        try: data = self.provider.generate_birth_chart(profile)
        except ProviderError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc
        data["plain_language_report"] = interpret_kundli(data)
        chart = BirthChart(birth_profile_id=profile.id, provider=self.provider.name, provider_version=self.provider.version,
            ayanamsha=self.settings.astrology_ayanamsha.lower(), calculation_key=key, chart_data=data)
        self.database.add(chart); self.database.flush(); return chart

    def reference_chart_for_profile(self, profile: BirthProfile) -> BirthChart:
        """Create a provider-free reference for matching; MatchReport performs the real calculation."""
        key = digest(f"{_profile_key(profile)}|{self.settings.astrology_ayanamsha}|match-reference-v1")
        existing = self.database.scalar(select(BirthChart).where(BirthChart.birth_profile_id == profile.id, BirthChart.calculation_key == key))
        if existing: return existing
        chart = BirthChart(birth_profile_id=profile.id, provider=self.provider.name, provider_version=self.provider.version,
            ayanamsha=self.settings.astrology_ayanamsha.lower(), calculation_key=key,
            chart_data={"profile": _profile_data(profile), "calculation": {"provider": self.provider.name, "purpose": "compatibility-reference"}})
        self.database.add(chart); self.database.flush(); return chart

    def compatibility(self, a: BirthChart, b: BirthChart) -> CompatibilityMatch:
        pair = sorted([a.calculation_key, b.calculation_key]); key = digest(f"{pair[0]}|{pair[1]}|{self.provider.name}|match-v2")
        existing = self.database.scalar(select(CompatibilityMatch).where(CompatibilityMatch.user_id == self.user_id, CompatibilityMatch.calculation_key == key))
        if existing:
            if not existing.result_data.get("plain_language_report"):
                existing.result_data = {**existing.result_data, "plain_language_report": interpret_compatibility(existing.result_data)}
            return existing
        profiles = [self.database.get(BirthProfile, chart.birth_profile_id) for chart in (a, b)]
        try: data = self.provider.generate_compatibility(profiles[0], profiles[1])
        except ProviderError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc
        data["plain_language_report"] = interpret_compatibility(data)
        match = CompatibilityMatch(user_id=self.user_id, person_a_chart_id=a.id, person_b_chart_id=b.id, compatibility_version="match-v2",
            calculation_key=key, result_data=data)
        self.database.add(match); self.database.flush(); return match

    def ensure_report(self, report_type: str, source_id: UUID, title: str, data: dict) -> Report:
        report = self.database.scalar(select(Report).where(Report.user_id == self.user_id, Report.report_type == report_type, Report.source_id == source_id))
        if not report:
            report = Report(user_id=self.user_id, report_type=report_type, source_id=source_id, title=title, report_data=data)
            self.database.add(report); self.database.flush()
        elif report.report_data != data:
            report.report_data = data
        return report

    def commit(self) -> None: self.database.commit()
