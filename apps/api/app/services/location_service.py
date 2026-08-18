from dataclasses import dataclass
import re

import httpx
from fastapi import HTTPException
from timezonefinder import TimezoneFinder

from app.core.config import get_settings


@dataclass(frozen=True)
class ResolvedPlace:
    canonical_name: str
    latitude: float
    longitude: float
    timezone: str


class LocationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timezone_finder = TimezoneFinder(in_memory=True)

    def resolve(self, query: str) -> ResolvedPlace:
        cleaned = " ".join(query.split())
        if len(cleaned) < 2:
            raise HTTPException(status_code=422, detail="Please enter a valid birth place.")
        requested_postcode = re.search(r"(?<!\d)([1-9]\d{5})(?!\d)", cleaned)
        lookup_query = cleaned
        if requested_postcode:
            without_postcode = re.sub(rf"\b{requested_postcode.group(1)}\b,?", "", cleaned).strip(" ,")
            lookup_query = f"{requested_postcode.group(1)}, {without_postcode}"
        try:
            response = httpx.get(
                self.settings.geocoding_url,
                params={"q": lookup_query, "format": "jsonv2", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": self.settings.geocoding_user_agent},
                timeout=15,
            )
            response.raise_for_status()
            results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Birth-place lookup is temporarily unavailable. Please try again.") from exc
        if not results:
            raise HTTPException(status_code=422, detail="We could not resolve that birth place. Add the city, state, and country.")
        result = results[0]
        resolved_postcode = str(result.get("address", {}).get("postcode", ""))
        if requested_postcode and requested_postcode.group(1) != resolved_postcode:
            raise HTTPException(status_code=422, detail=f"The birth-place lookup did not match PIN {requested_postcode.group(1)}. Add the locality, city, state, PIN, and country.")
        latitude, longitude = float(result["lat"]), float(result["lon"])
        timezone = self.timezone_finder.timezone_at(lat=latitude, lng=longitude)
        if not timezone:
            raise HTTPException(status_code=422, detail="We could not determine the timezone for that birth place.")
        display_name = result.get("display_name", cleaned)
        if not requested_postcode and resolved_postcode:
            display_name = re.sub(rf",?\s*{re.escape(resolved_postcode)}(?=,|$)", "", display_name)
        return ResolvedPlace(display_name, latitude, longitude, timezone)
