"""Small offline retrieval/citation/latency evaluation; run from apps/api."""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.astrology_assistant import answer
import app.services.astrology_assistant as assistant_module
from app.core.config import get_settings

# Keep the benchmark reproducible and avoid making paid/remote API calls.
_local_settings = get_settings().model_copy(update={"openai_api_key": ""})
assistant_module.get_settings = lambda: _local_settings

CASES = [("How does the Moon relate to emotional habits?", "S2"), ("What themes are associated with career and vocation?", "S12"),
         ("What can the seventh house say about partnership?", "S11"), ("How are Mercury and learning traditionally discussed?", "S5"),
         ("What does a Vimshottari dasha period mean?", "S15")]
CHART = {"summary": {"lagna": "Taurus", "moon_sign": "Cancer", "nakshatra": "Pushya"},
         "planets": [{"name": "Moon", "sign": "Cancer", "house": 3}, {"name": "Mercury", "sign": "Gemini", "house": 2}],
         "dashas": [{"planet": "Jupiter", "period": "2024-2040"}]}


def main() -> None:
    documents = json.loads((Path(__file__).parents[1] / "app" / "knowledge" / "vedic_astrology.json").read_text(encoding="utf-8"))
    known = {d["id"] for d in documents}
    relevance, citation_ok, latencies, unsupported = [], [], [], []
    for question, expected in CASES:
        started = time.perf_counter(); result = answer(CHART, question); latencies.append((time.perf_counter() - started) * 1000)
        cited = {c["id"] for c in result["citations"]}; relevance.append(expected in cited); citation_ok.append(cited.issubset(known))
        claims = re.findall(r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s+in\s+([A-Z][a-z]+),?\s+house\s+(\d+)", result["answer"])
        supplied = {(p["name"], p["sign"], str(p["house"])) for p in CHART["planets"]}
        unsupported.append(any((planet, sign, house) not in supplied for planet, sign, house in claims))
    n = len(CASES)
    print(json.dumps({"cases": n, "retrieval_recall_at_4": sum(relevance) / n, "citation_id_validity": sum(citation_ok) / n,
        "unsupported_placement_rate": sum(unsupported) / n, "latency_ms_mean": round(statistics.mean(latencies), 1),
        "latency_ms_p95": round(sorted(latencies)[math.ceil(.95 * n) - 1], 1),
        "note": "Small curated smoke benchmark; placement-pattern check does not detect every unsupported statement."}, indent=2))


if __name__ == "__main__":
    main()
