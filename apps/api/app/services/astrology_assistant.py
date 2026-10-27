"""Evidence-grounded astrology retrieval, graph context, and answer generation."""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any
import httpx
import faiss

from app.core.config import get_settings

KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "vedic_astrology.json"
_index_cache: tuple[object, list[dict], str, str] | None = None
_local_encoder: Any | None = None


def _knowledge() -> list[dict]:
    return json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _local_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Small deterministic fallback encoder; configure an embedding API for semantic vectors."""
    vector = [0.0] * dimensions
    for term in _terms(text):
        digest = hashlib.blake2b(term.encode(), digest_size=8).digest()
        number = int.from_bytes(digest, "little")
        vector[number % dimensions] += 1.0 if number & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _embed(texts: list[str]) -> tuple[list[list[float]], str]:
    settings = get_settings()
    # Local semantic embeddings are the default so retrieval works without a
    # hosted AI key. OpenAI embeddings remain an explicit opt-in.
    if settings.astrology_embedding_provider == "openai":
        if settings.openai_api_key.strip():
            try:
                response = httpx.post(f"{settings.openai_api_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                    json={"model": settings.openai_embedding_model, "input": texts}, timeout=20)
                response.raise_for_status()
                rows = sorted(response.json()["data"], key=lambda row: row["index"])
                vectors = [_normalize([float(value) for value in row["embedding"]]) for row in rows]
                return vectors, settings.openai_embedding_model
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                # Never load the large local transformer as an error fallback on
                # constrained hosts such as Render's 512 MB free instance.
                return [_local_embedding(text) for text in texts], "local-hash-embedding-v1"
        return [_local_embedding(text) for text in texts], "local-hash-embedding-v1"
    global _local_encoder
    try:
        from sentence_transformers import SentenceTransformer
        if _local_encoder is None:
            _local_encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        matrix = _local_encoder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [[float(value) for value in row] for row in matrix], "all-MiniLM-L6-v2 (local)"
    except (ImportError, OSError, RuntimeError, ValueError):
        # Keep the app usable in minimal/offline environments. This fallback is
        # lexical and deterministic; sentence-transformers is the semantic path.
        return [_local_embedding(text) for text in texts], "local-hash-embedding-v1"


class _PythonIPIndex:
    """Dependency-free exact inner-product search for local development."""
    def __init__(self) -> None:
        self.rows: list[list[float]] = []

    def add(self, vectors: list[list[float]]) -> None:
        self.rows.extend(vectors)

    def search(self, queries: list[list[float]], count: int):
        scores, positions = [], []
        for query in queries:
            ranked = sorted(((sum(a * b for a, b in zip(query, row)), i) for i, row in enumerate(self.rows)), reverse=True)[:count]
            scores.append([score for score, _ in ranked]); positions.append([i for _, i in ranked])
        return scores, positions


class _FaissIPIndex:
    """Adapt list-based embeddings to FAISS's required float32 matrix input."""
    def __init__(self, index: Any, numpy: Any) -> None:
        self.index = index
        self.numpy = numpy

    def search(self, queries: list[list[float]], count: int):
        matrix = self.numpy.asarray(queries, dtype=self.numpy.float32)
        return self.index.search(matrix, count)


def _make_index(vectors: list[list[float]]) -> tuple[Any, str]:
    try:
        import faiss
        import numpy as np
        matrix = np.asarray(vectors, dtype=np.float32)
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return _FaissIPIndex(index, np), "FAISS IndexFlatIP"
    except ImportError:
        index = _PythonIPIndex()
        index.add(vectors)
        return index, "Python exact inner-product fallback"


def _index():
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    docs = _knowledge()
    vectors, model = _embed([d["text"] for d in docs])
    index, backend = _make_index(vectors)
    _index_cache = index, docs, model, backend
    return _index_cache


class _NodeAccessor(dict):
    def __call__(self, data: bool = False):
        return list(self.items()) if data else list(self.keys())


class _PythonDiGraph:
    """Small NetworkX-shaped fallback used only when the optional package is absent."""
    def __init__(self) -> None:
        self.nodes = _NodeAccessor()
        self.edges: dict[str, set[str]] = {}

    def add_node(self, node: str, **metadata: Any) -> None:
        self.nodes.setdefault(node, {}).update(metadata)
        self.edges.setdefault(node, set())

    def add_edge(self, source: str, target: str, **_: Any) -> None:
        self.add_node(source); self.add_node(target); self.edges[source].add(target)

    def successors(self, node: str) -> set[str]:
        return self.edges.get(node, set())


def knowledge_graph():
    try:
        import networkx as nx
        graph = nx.DiGraph()
    except ImportError:
        graph = _PythonDiGraph()
    for sign in "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split():
        graph.add_node(f"sign:{sign.lower()}", kind="sign", label=sign)
    for planet in "Sun Moon Mars Mercury Jupiter Venus Saturn Rahu Ketu".split():
        graph.add_node(f"planet:{planet.lower()}", kind="planet", label=planet)
    for house in range(1, 13):
        graph.add_node(f"house:{house}", kind="house", label=f"House {house}")
    graph.add_node("concept:interpretation", kind="concept", label="Traditional interpretation")
    for sign in "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split():
        graph.add_edge(f"sign:{sign.lower()}", "concept:interpretation", relation="provides-symbolic-context")
    for d in _knowledge():
        p = d.get("planet", "").lower(); h = d.get("house"); s = d.get("sign", "").lower()
        concept = f"concept:{d['id']}"
        graph.add_node(concept, kind="concept", label=d["title"])
        if p: graph.add_edge(f"planet:{p}", concept, relation="traditionally-discussed-with")
        if h: graph.add_edge(f"house:{h}", concept, relation="traditionally-discussed-with")
        if s: graph.add_edge(f"sign:{s}", concept, relation="traditionally-discussed-with")
    return graph


def _graph_context(question: str, chart: dict) -> list[str]:
    graph = knowledge_graph()
    for placement in chart.get("planets", []):
        planet = str(placement.get("name", "")).lower()
        sign = str(placement.get("sign", "")).lower()
        house = placement.get("house")
        if planet and house:
            graph.add_edge(f"planet:{planet}", f"house:{house}", relation="calculated-placement")
        if planet and sign:
            graph.add_edge(f"planet:{planet}", f"sign:{sign}", relation="calculated-in")
    entities = {p.get("name", "").lower() for p in chart.get("planets", [])}
    entities |= {p.get("sign", "").lower() for p in chart.get("planets", [])}
    entities |= {str(p.get("house", "")) for p in chart.get("planets", [])}
    q = question.lower()
    entities |= {w for w in re.findall(r"[a-z]+", q)}
    concepts: set[str] = set()
    for node, meta in graph.nodes(data=True):
        if (meta.get("kind") == "planet" and meta.get("label", "").lower() in entities) or (meta.get("kind") == "sign" and meta.get("label", "").lower() in entities):
            concepts.update(graph.successors(node))
        if meta.get("kind") == "house" and node.split(":")[1] in entities:
            concepts.update(graph.successors(node))
    return [graph.nodes[n]["label"] for n in sorted(concepts)]


def _chart_facts(chart: dict) -> str:
    summary = chart.get("summary", {})
    facts = [f"Lagna: {summary.get('lagna', 'not supplied')}", f"Moon sign: {summary.get('moon_sign', 'not supplied')}", f"Nakshatra: {summary.get('nakshatra', 'not supplied')}"]
    facts.extend(f"{p.get('name')} in {p.get('sign')}, house {p.get('house')}" for p in chart.get("planets", []))
    facts.extend(f"Dasha: {d.get('planet')} {d.get('period')}" for d in chart.get("dashas", []))
    return "\n".join(facts)


def answer(chart: dict, question: str, *, report: bool = False) -> dict:
    started = time.perf_counter()
    index, docs, embedding_model, backend = _index()
    vectors, query_model = _embed([question])
    if query_model != embedding_model:
        # A hosted embedding request may fail after the index was built. Rebuild
        # locally so the index and query always use compatible vectors.
        vectors = [_local_embedding(d["text"]) for d in docs]
        index, backend = _make_index(vectors)
        _index_cache = index, docs, "local-hash-embedding-v1", backend
        embedding_model = "local-hash-embedding-v1"
        vectors = [_local_embedding(question)]
    scores, positions = index.search(vectors, min(4, len(docs)))
    selected = [(docs[int(i)], float(score)) for i, score in zip(positions[0], scores[0]) if i >= 0 and score > 0]
    graph_terms = _graph_context(question, chart)
    settings = get_settings()
    context = "\n\n".join(f"[{d['id']}] {d['text']}" for d, _ in selected)
    facts = _chart_facts(chart)
    prompt = f"""Answer using ONLY the chart facts and reference passages below. Never infer a placement absent from chart facts. Separate chart facts from traditional interpretation. Cite every interpretive paragraph with passage ids like [S1]. If evidence is insufficient, say so. Avoid deterministic predictions, health/financial advice, and invented aspects, yogas, house lords or events. Use plain language.\nQuestion: {question}\nVerified chart facts:\n{facts}\nRelevant graph concepts: {', '.join(graph_terms) or 'none'}\nReference passages:\n{context}\n"""
    text = ""
    if settings.openai_api_key.strip() and selected:
        try:
            response = httpx.post(f"{settings.openai_api_url.rstrip('/')}/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json={"model": settings.openai_model, "input": prompt}, timeout=45)
            response.raise_for_status()
            for item in response.json().get("output", []):
                for part in item.get("content", []):
                    if part.get("type") == "output_text": text += part.get("text", "")
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            text = ""
        allowed_citations = {d["id"] for d, _ in selected}
        used_citations = set(re.findall(r"\[(S\d+)\]", text))
        if not used_citations or not used_citations.issubset(allowed_citations):
            text = ""
    if not text:
        placement_lines = [line for line in facts.splitlines() if any(word in question.lower() for word in line.lower().replace(":", "").split()[:1])]
        placement_lines = placement_lines or facts.splitlines()[:3]
        evidence = " ".join(f"{d['text']} [{d['id']}]" for d, _ in selected)
        text = ("Your calculated chart shows " + "; ".join(placement_lines) + ". " + evidence) if evidence else "I could not retrieve a relevant reference passage for this question. Please try a more specific question about a supplied planet, sign, or house."
    citations = [{"id": d["id"], "title": d["title"], "source": d["source"], "url": d.get("url"), "score": round(score, 4)} for d, score in selected]
    return {"answer": text, "citations": citations, "chart_facts": facts.splitlines(), "graph_context": graph_terms,
        "retrieval": {"index": backend, "embedding_model": embedding_model}, "latency_ms": round((time.perf_counter()-started)*1000, 1), "kind": "personalized-report" if report else "answer"}

