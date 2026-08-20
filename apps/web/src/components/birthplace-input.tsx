"use client";

import { useEffect, useRef, useState } from "react";
import { suggestLocations } from "@/lib/api/astrology";
import type { PlaceSuggestion } from "@/types/astrology";

type Mode = "coordinates" | "city";

export function BirthplaceInput({ name = "place" }: { name?: string }) {
  const [mode, setMode] = useState<Mode>("city");
  const [query, setQuery] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [selectedPlace, setSelectedPlace] = useState<PlaceSuggestion | null>(null);
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const ignoreNextSearch = useRef(false);
  const latitudeName = name.replace(/place$/, "latitude");
  const longitudeName = name.replace(/place$/, "longitude");

  useEffect(() => {
    if (mode !== "city") return;
    if (ignoreNextSearch.current) { ignoreNextSearch.current = false; return; }
    if (query.trim().length < 3) { setSuggestions([]); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      suggestLocations(query, controller.signal)
        .then((response) => { setSuggestions(response.data); setOpen(true); })
        .catch((error: unknown) => { if ((error as { name?: string }).name !== "AbortError") setSuggestions([]); });
    }, 350);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [mode, query]);

  function select(place: PlaceSuggestion) {
    ignoreNextSearch.current = true;
    setQuery(place.label);
    setSelectedPlace(place);
    setOpen(false);
  }

  return <div className="birthplace-field"><span className="field-label">Place of birth</span><div className="place-mode-tabs" role="group" aria-label="Birthplace entry method"><button type="button" className={mode === "coordinates" ? "active" : ""} onClick={() => setMode("coordinates")}>Longitude &amp; latitude</button><button type="button" className={mode === "city" ? "active" : ""} onClick={() => setMode("city")}>Search city</button></div>{mode === "coordinates" ? <div className="coordinate-grid"><label>Longitude<input name={longitudeName} type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} required /></label><label>Latitude<input name={latitudeName} type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></label><input type="hidden" name={name} value={latitude && longitude ? `${latitude}, ${longitude}` : "Coordinates"} /></div> : <label className="city-search"><span className="place-picker"><input name={name} value={query} onChange={(event) => { setQuery(event.target.value); setSelectedPlace(null); }} onFocus={() => setOpen(suggestions.length > 0)} onBlur={() => window.setTimeout(() => setOpen(false), 150)} required autoComplete="off" placeholder="Start entering a city" aria-autocomplete="list" aria-expanded={open} />{open && suggestions.length > 0 && <span className="place-suggestions" role="listbox">{suggestions.map((place) => <button type="button" role="option" key={`${place.latitude}-${place.longitude}`} onMouseDown={() => select(place)}>{place.label}</button>)}</span>}<input type="hidden" name={latitudeName} value={selectedPlace?.latitude ?? ""} /><input type="hidden" name={longitudeName} value={selectedPlace?.longitude ?? ""} /></span></label>}</div>;
}
