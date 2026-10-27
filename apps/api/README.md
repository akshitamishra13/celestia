# AstroLive API

This directory will contain the FastAPI backend.

Planned source areas:

```text
app/
  api/          HTTP routes and dependencies
  core/         Configuration, security, and shared infrastructure
  models/       Database models
  schemas/      Request and response models
  services/     Application and domain logic
  repositories/ Persistence abstractions
  providers/    External provider integrations
tests/          Unit and integration tests
```

Authentication includes signup, login, logout, current-user lookup, Argon2 password hashing, and JWT bearer tokens. Send the token returned by signup or login as `Authorization: Bearer <token>`.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and replace `JWT_SECRET` before any shared deployment.

## Astrology provider

Navamsha is the default live provider. Create a free API key at `navamsha.in`, then set it in `apps/api/.env`:

```dotenv
ASTROLOGY_PROVIDER=navamsha
NAVAMSHA_API_KEY=your-key-here
```

Kundli generation uses Navamsha's basic Kundali and current Dasha endpoints. Compatibility uses its detailed Ashtakoot endpoint and retains the provider's 36-point score and Koota breakdown. Birth-place text is geocoded first, and the historical UTC offset is derived from the resolved timezone and submitted birth date.

For provider comparison or temporary fallback, set `ASTROLOGY_PROVIDER=vedastro`. Use `ASTROLOGY_PROVIDER=mock` only for offline tests; mock results are not astrological calculations. Restart the API after changing `.env`.

## Evidence-grounded astrology assistant

The authenticated `/api/assistant/ask` and `/api/assistant/report` routes use only the signed-in user's latest persisted Kundli. The assistant embeds passages from `app/knowledge/vedic_astrology.json` and the question with the local `all-MiniLM-L6-v2` Sentence Transformers model, then searches normalized vectors with FAISS `IndexFlatIP` (up to four positive matches). NetworkX relates verified chart placements to planet, sign, house, and interpretive-concept nodes; the resulting context is returned to the client and included in the generation prompt. The model is downloaded on first use. No OpenAI key is needed for embeddings or retrieval. Set `ASTROLOGY_EMBEDDING_PROVIDER=openai` to opt into hosted OpenAI embeddings; `OPENAI_API_KEY` enables optional response generation. Without a key, the API assembles a cited extractive answer from chart facts and retrieved passages, which may be broader than the question. If local model loading fails, deterministic feature-hash vectors and dependency-free vector/graph fallbacks keep the API usable with lower retrieval quality.

Run `python scripts/evaluate_astrology_assistant.py` from this directory for retrieval recall, citation identifier validity, detected unsupported placements, and response latency. The small curated sample is a demonstration harness, not comprehensive evaluation.
