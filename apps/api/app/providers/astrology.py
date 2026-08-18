import re
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings
from app.models.astrology import BirthProfile

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]


class ProviderError(RuntimeError):
    pass


class AstrologyProvider(Protocol):
    name: str
    version: str
    def generate_birth_chart(self, profile: BirthProfile) -> dict: ...
    def generate_compatibility(self, a: BirthProfile, b: BirthProfile) -> dict: ...


def _offset(profile: BirthProfile) -> str:
    local = datetime.combine(profile.date_of_birth, profile.time_of_birth).replace(tzinfo=ZoneInfo(profile.timezone))
    delta = local.utcoffset()
    if delta is None:
        raise ProviderError("Unable to resolve the historical timezone offset.")
    minutes = int(delta.total_seconds() // 60)
    return f"{'+' if minutes >= 0 else '-'}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def _time_payload(profile: BirthProfile) -> dict:
    return {"StdTime": f"{profile.time_of_birth:%H:%M} {profile.date_of_birth:%d/%m/%Y} {_offset(profile)}",
        "Location": {"Name": profile.canonical_place, "Longitude": float(profile.longitude), "Latitude": float(profile.latitude)}}


def _offset_hours(profile: BirthProfile) -> float:
    local = datetime.combine(profile.date_of_birth, profile.time_of_birth).replace(tzinfo=ZoneInfo(profile.timezone))
    delta = local.utcoffset()
    if delta is None:
        raise ProviderError("Unable to resolve the historical timezone offset.")
    return delta.total_seconds() / 3600


def _navamsha_birth_payload(profile: BirthProfile) -> dict:
    settings = get_settings()
    return {
        "year": profile.date_of_birth.year, "month": profile.date_of_birth.month, "date": profile.date_of_birth.day,
        "hours": profile.time_of_birth.hour, "minutes": profile.time_of_birth.minute, "seconds": profile.time_of_birth.second,
        "latitude": float(profile.latitude), "longitude": float(profile.longitude), "timezone": _offset_hours(profile),
        "settings": {"observation_point": settings.astrology_observation_point,
            "ayanamsha": settings.astrology_ayanamsha.lower(), "language": "en", "node_type": settings.astrology_node_type},
    }


def _unwrap(data: object) -> object:
    if not isinstance(data, dict): return data
    if data.get("Status") == "Fail": raise ProviderError(str(data.get("Payload", "VedAstro calculation failed.")))
    value = data.get("Payload", data)
    while isinstance(value, dict) and len(value) == 1:
        value = next(iter(value.values()))
    return value


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)): return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _records_map(value: object, names: list[str]) -> dict[str, object]:
    output: dict[str, object] = {}
    if isinstance(value, str):
        for part in value.split(","):
            label, separator, item = part.partition("-")
            matched = next((name for name in names if name.lower() == label.strip().lower()), None)
            if matched and separator: output[matched] = item.strip()
        return output
    if isinstance(value, dict):
        for key, item in value.items():
            if key in names: output[key] = item
        if output: return output
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict): continue
            label = next((str(v) for k, v in item.items() if k.lower() in {"planet", "planetname", "house", "housename", "name"}), "")
            planet = next((p for p in names if p.lower() == label.lower()), None)
            if planet:
                output[planet] = next((v for k, v in item.items() if k.lower() not in {"planet", "planetname", "house", "housename", "name"}), item)
    return output


def _sign(value: object, longitude: float | None = None) -> str:
    text = str(value)
    found = next((sign for sign in SIGNS if sign.lower() in text.lower()), None)
    if found: return found
    return SIGNS[int((longitude or 0) % 360 // 30)]


def _house(value: object, planet_sign: str, lagna: str) -> int:
    match = re.search(r"(?:House)?\s*(1[0-2]|[1-9])", str(value), re.I)
    if match: return int(match.group(1))
    return ((SIGNS.index(planet_sign) - SIGNS.index(lagna)) % 12) + 1


def _field(value: object, *names: str) -> object | None:
    if not isinstance(value, dict): return None
    lowered = {str(key).lower(): item for key, item in value.items()}
    return next((lowered[name.lower()] for name in names if name.lower() in lowered), None)


class NavamshaProvider:
    name, version = "navamsha", "api-v1"

    def __init__(self) -> None: self.settings = get_settings()

    def _call(self, path: str, payload: dict) -> object:
        if not self.settings.navamsha_api_key.strip():
            raise ProviderError("Navamsha API is selected, but NAVAMSHA_API_KEY is not configured in apps/api/.env.")
        try:
            response = httpx.post(f"{self.settings.navamsha_api_url.rstrip('/')}/{path.lstrip('/')}", json=payload,
                headers={"X-API-Key": self.settings.navamsha_api_key}, timeout=self.settings.provider_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict): raise ProviderError("Navamsha returned an unsupported response.")
            if int(data.get("statusCode", 200)) >= 400: raise ProviderError(str(data.get("message") or data.get("error") or "Navamsha calculation failed."))
            return data.get("output", data)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in {401, 403}: raise ProviderError("Navamsha rejected the API key. Check NAVAMSHA_API_KEY in apps/api/.env.") from exc
            if code == 429: raise ProviderError("Navamsha's request limit has been reached. Please try again shortly.") from exc
            raise ProviderError(f"Navamsha rejected the calculation (HTTP {code}).") from exc
        except ProviderError: raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("Navamsha is temporarily unavailable. Please try again shortly.") from exc

    def generate_birth_chart(self, profile: BirthProfile) -> dict:
        payload = _navamsha_birth_payload(profile)
        raw = self._call("kundali/basic", payload)
        dasha = self._call("dasha/current", payload)
        if not isinstance(raw, dict): raise ProviderError("Navamsha returned an unsupported Kundli response.")
        ascendant = _field(raw, "ascendant", "lagna") or {}
        lagna_longitude = _number(_field(ascendant, "longitude", "nirayana_longitude", "full_degree", "fullDegree"))
        lagna = _sign(_field(ascendant, "zodiac_sign_name", "sign", "rashi"), lagna_longitude)
        source = _field(raw, "planets", "planet_positions", "grahas")
        records = source if isinstance(source, dict) else {}
        planets = []
        for name in PLANETS:
            record = next((value for key, value in records.items() if str(key).lower() == name.lower()), None)
            if record is None: raise ProviderError(f"Navamsha response is missing {name}.")
            longitude = _number(_field(record, "longitude", "nirayana_longitude", "full_degree", "fullDegree", "absolute_degree"))
            sign = _sign(_field(record, "zodiac_sign_name", "sign", "rashi"), longitude)
            degree = _number(_field(record, "degree_in_sign", "norm_degree", "normDegree", "degree"))
            if longitude is None and degree is not None: longitude = SIGNS.index(sign) * 30 + degree
            if longitude is None: raise ProviderError(f"Navamsha response is missing the {name} longitude.")
            nak = _field(record, "nakshatra_name", "nakshatra", "constellation")
            if isinstance(nak, dict): nak = _field(nak, "name")
            nak_index = int((longitude % 360) / (360 / 27)) % 27
            planets.append({"name": name, "sign": sign, "degree": round(degree if degree is not None else longitude % 30, 2),
                "longitude": round(longitude, 4), "house": _house(_field(record, "house", "house_number"), sign, lagna),
                "nakshatra": str(nak or NAKSHATRAS[nak_index]), "pada": int(_number(_field(record, "nakshatra_pada", "pada")) or (int((longitude % (360 / 27)) / (360 / 108)) + 1))})
        moon = next(item for item in planets if item["name"] == "Moon")
        dashas = self._normalize_current_dasha(dasha)
        chart: dict[str, str] = {}
        for planet in planets: chart[str(planet["house"])] = ", ".join(filter(None, [chart.get(str(planet["house"])), planet["name"]]))
        return {"profile": _profile_data(profile), "summary": {"lagna": lagna, "moon_sign": moon["sign"], "nakshatra": moon["nakshatra"],
            "current_mahadasha": dashas[0]["planet"] if dashas else "Not returned", "current_antardasha": dashas[1]["planet"] if len(dashas) > 1 else "Not returned"},
            "planets": planets, "dashas": dashas, "chart": chart,
            "interpretation": "Calculated dynamically from the submitted birth details using Navamsha's Lahiri sidereal calculation. Astrology is a traditional interpretive system, not a scientific prediction.",
            "calculation": {"provider": self.name, "version": self.version, "ayanamsha": self.settings.astrology_ayanamsha.lower(), "house_system": "whole_sign"}}

    @staticmethod
    def _normalize_current_dasha(raw: object) -> list[dict[str, str]]:
        if not isinstance(raw, dict): return []
        output = []
        for field_name, label in (("mahadasha", "Mahadasha"), ("antardasha", "Antardasha"), ("pratyantardasha", "Pratyantardasha")):
            value = _field(raw, field_name)
            if value is None: continue
            planet = str(_field(value, "planet", "lord", "name") or value)
            item = {"planet": planet, "period": label, "nature": "Traditional period",
                "description": f"Current {planet} {label} calculated by Navamsha."}
            if isinstance(value, dict):
                if _field(value, "start", "start_date"): item["start"] = str(_field(value, "start", "start_date"))
                if _field(value, "end", "end_date"): item["end"] = str(_field(value, "end", "end_date"))
            output.append(item)
        return output

    def generate_compatibility(self, a: BirthProfile, b: BirthProfile) -> dict:
        groom, bride = (b, a) if (a.gender or "").lower() == "female" and (b.gender or "").lower() == "male" else (a, b)
        raw = self._call("compatibility/ashtakoot/detailed", {"bride": _navamsha_birth_payload(bride), "groom": _navamsha_birth_payload(groom)})
        if not isinstance(raw, dict): raise ProviderError("Navamsha returned an unsupported compatibility response.")
        score = _number(_field(raw, "effective_total_score", "total_score"))
        maximum = _number(_field(raw, "maximum_score")) or 36
        if score is None: raise ProviderError("Navamsha compatibility response did not include a total score.")
        breakdown = _field(raw, "breakdown", "kootas", "components") or {}
        components = []
        items = breakdown.items() if isinstance(breakdown, dict) else enumerate(breakdown) if isinstance(breakdown, list) else []
        for key, value in items:
            component_score = _number(_field(value, "score", "obtained_score"))
            component_max = _number(_field(value, "maximum_score", "max_score", "maximum"))
            ratio = component_score / component_max if component_score is not None and component_max else .5
            nature = "Good" if ratio >= .75 else "Neutral" if ratio >= .4 else "Challenging"
            label = str(_field(value, "name", "koota") or key).replace("_", " ").title()
            description = str(_field(value, "description", "result", "interpretation") or f"{label} received {component_score or 0:g} of {component_max or 0:g} points.")
            components.append({"name": label, "nature": nature, "description": description, "score": component_score, "maximum": component_max})
        positive = [item for item in components if item["nature"] == "Good"]
        difficult = [item for item in components if item["nature"] == "Challenging"]
        return {"overall_score": round(score, 1), "maximum_score": maximum, "components": components,
            "strengths": [f"{item['name']}: {item['description']}" for item in positive[:5]] or ["Review the supportive factors in the Ashtakoot breakdown."],
            "areas_to_understand": [f"{item['name']}: {item['description']}" for item in difficult[:5]] or ["Review every factor alongside the overall score."],
            "summary": str(_field(raw, "summary", "interpretation") or f"Navamsha calculated an Ashtakoot score of {score:g} out of {maximum:g}."),
            "guidance": "This is a traditional Ashtakoot calculation and should not be treated as a prediction of relationship success.",
            "person_a": _profile_data(a), "person_b": _profile_data(b),
            "calculation": {"provider": self.name, "version": self.version, "method": "Ashtakoot detailed", "ayanamsha": self.settings.astrology_ayanamsha.lower()}}


class VedAstroProvider:
    name, version = "vedastro", "api-v1"
    def __init__(self) -> None: self.settings = get_settings()

    def _call(self, method: str, payload: dict) -> object:
        body = {**payload, "APIKey": self.settings.vedastro_api_key}
        try:
            response = httpx.post(f"{self.settings.vedastro_api_url}/{method}", json=body, timeout=self.settings.provider_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            if data.get("Status") == "Fail": raise ProviderError(str(data.get("Payload", "VedAstro calculation failed.")))
            value = data.get("Payload", data)
            return value.get(method) if isinstance(value, dict) and method in value else value
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise ProviderError("VedAstro's free limit has been reached. Please wait one minute and try again.") from exc
            raise ProviderError(f"VedAstro rejected the calculation (HTTP {exc.response.status_code}). Please try again shortly.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("VedAstro is temporarily unavailable. Please try again shortly.") from exc

    def generate_birth_chart(self, profile: BirthProfile) -> dict:
        raw = self._call("AllTimeData", {"time": _time_payload(profile)})
        if not isinstance(raw, dict): raise ProviderError("VedAstro returned an unsupported chart response.")
        longitudes = _records_map(raw.get("AllPlanetLongitude", {}), PLANETS)
        signs = _records_map(raw.get("AllPlanetRasiSigns", {}), PLANETS)
        houses = _records_map(raw.get("HouseAllPlanetOccupiesBasedOnLongitudes", {}), PLANETS)
        stars = _records_map(raw.get("AllPlanetConstellation", {}), PLANETS)
        house_signs = _records_map(raw.get("AllHouseRasiSigns", {}), [f"House{i}" for i in range(1, 13)])
        lagna = _sign(raw.get("LagnaSignName") or house_signs.get("House1"))
        planets = []
        for planet in PLANETS:
            longitude = _number(longitudes.get(planet))
            if longitude is None: raise ProviderError(f"VedAstro response is missing the {planet} longitude.")
            sign = _sign(signs.get(planet), longitude)
            nak_index = int((longitude % 360) / (360 / 27)) % 27
            nakshatra = next((n for n in NAKSHATRAS if n.lower() in str(stars.get(planet, "")).lower()), NAKSHATRAS[nak_index])
            planets.append({"name": planet, "sign": sign, "degree": round(longitude % 30, 2), "longitude": round(longitude, 4),
                "house": _house(houses.get(planet), sign, lagna), "nakshatra": nakshatra, "pada": int((longitude % (360 / 27)) / (360 / 108)) + 1})
        moon = next(p for p in planets if p["name"] == "Moon")
        dasha_raw = self._call("DasaForNow", {"birthTime": _time_payload(profile), "levels": 3})
        dashas = _normalize_dashas(dasha_raw)
        chart: dict[str, str] = {}
        for planet in planets: chart[str(planet["house"])] = ", ".join(filter(None, [chart.get(str(planet["house"])), planet["name"]]))
        return {"profile": _profile_data(profile), "summary": {"lagna": lagna, "moon_sign": moon["sign"], "nakshatra": moon["nakshatra"],
            "current_mahadasha": dashas[0]["planet"] if dashas else "See Dasha details", "current_antardasha": dashas[1]["planet"] if len(dashas) > 1 else "See Dasha details"},
            "planets": planets, "dashas": dashas, "chart": chart,
            "interpretation": "Calculated dynamically from the submitted birth date, exact time, resolved coordinates, and historical timezone. Astrology is a traditional interpretive system, not a scientific prediction.",
            "calculation": {"provider": self.name, "version": self.version, "ayanamsha": self.settings.astrology_ayanamsha.lower(), "house_system": "whole_sign"}}

    def generate_compatibility(self, a: BirthProfile, b: BirthProfile) -> dict:
        male, female = (b, a) if (a.gender or "").lower() == "female" and (b.gender or "").lower() == "male" else (a, b)
        raw = self._call("MatchReport", {"maleBirthTime": _time_payload(male), "femaleBirthTime": _time_payload(female)})
        if not isinstance(raw, dict): raise ProviderError("VedAstro returned an unsupported match response.")
        score = next((_number(raw.get(k)) for k in ("KutaScore", "Score", "TotalScore", "CompatibilityScore") if raw.get(k) is not None), None)
        if score is None: raise ProviderError("VedAstro match response did not include a compatibility score.")
        predictions = raw.get("PredictionList") or raw.get("Predictions") or []
        components = []
        allowed = {"graha maitram", "rajju", "nadi kuta", "vasya kuta", "dina kuta", "guna kuta", "mahendra", "stree deergha",
            "rasi kuta", "vedha", "varna", "yoni kuta", "kuja dosa", "dosha samya", "sex energy", "planetary trine harmony",
            "sun-moon harmony", "venus-saturn connection", "marriage stability"}
        if isinstance(predictions, list):
            for item in predictions:
                if not isinstance(item, dict): continue
                if str(item.get("Name", "")).lower() not in allowed: continue
                nature = str(item.get("Nature", "Neutral"))
                description = ("Traditionally considered a challenging factor; consider it alongside the complete match report."
                    if nature.lower() in {"bad", "negative"} else str(item.get("Info") or item.get("Description") or item.get("Prediction") or ""))
                components.append({"name": str(item.get("Name", "Compatibility factor")), "nature": nature,
                    "description": description, "score": _number(item.get("Score")), "maximum": _number(item.get("Maximum"))})
        positive = [c for c in components if c["nature"].lower() in {"good", "excellent", "positive"}]
        difficult = [c for c in components if c["nature"].lower() in {"bad", "challenging", "negative"}]
        return {"overall_score": round(score, 1), "maximum_score": 100, "components": components,
            "strengths": [f"{c['name']}: {c['description'] or c['nature']}" for c in positive[:5]] or ["The calculated report contains supportive compatibility factors."],
            "areas_to_understand": [f"{c['name']}: {c['description'] or c['nature']}" for c in difficult[:5]] or ["Review each Kuta factor alongside the overall score."],
            "summary": str(raw.get("Summary", {}).get("ScoreSummary") if isinstance(raw.get("Summary"), dict) else raw.get("Summary") or f"VedAstro calculated a compatibility score of {score:g} out of 100."),
            "guidance": "This is a documented traditional Kuta calculation and should be used for reflection, not as a prediction of relationship success.",
            "person_a": _profile_data(a), "person_b": _profile_data(b), "calculation": {"provider": self.name, "version": self.version, "method": "MatchReport"}}


def _profile_data(profile: BirthProfile) -> dict:
    return {"id": str(profile.id), "name": profile.name, "date_of_birth": str(profile.date_of_birth), "time_of_birth": str(profile.time_of_birth),
        "place": profile.birth_place, "resolved_place": profile.canonical_place, "gender": profile.gender,
        "latitude": float(profile.latitude), "longitude": float(profile.longitude), "timezone": profile.timezone}


def _normalize_dashas(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, dict): return []
    output: list[dict[str, str]] = []
    current: object = raw
    labels = ["Mahadasha", "Antardasha", "Pratyantardasha"]
    for label in labels:
        if not isinstance(current, dict) or not current: break
        lord, value = next(iter(current.items()))
        if isinstance(value, dict):
            planet = str(value.get("Lord", lord))
            output.append({"planet": planet, "period": label, "nature": str(value.get("Nature", "Neutral")),
                "description": f"{planet} {label} calculated by VedAstro."})
            current = value.get("SubDasas", {})
        else: break
    return output
