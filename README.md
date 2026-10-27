# AstroLive

Deployment Link: https://celestia-as24-b6a0.vercel.app

Backend : https://celestia-1-cdim.onrender.com/
Frontend : https://celestia-as24-b6a0.vercel.app

AstroLive is a full-stack Vedic astrology application for generating Kundli, compatibility, and downloadable report experiences. It combines provider-backed astrology calculations with structured, plain-language interpretations while keeping calculated chart data separate from narrative explanations.

## Features

### Authentication and dashboard

- User signup and login
- Argon2 password hashing and expiring JWT bearer tokens
- Session restoration, protected pages, and logout
- User-owned charts, matches, and reports
- Responsive dashboard with a mobile sidebar
- Latest-Kundli snapshot showing Lagna, Moon sign, and Nakshatra

### Kundli

- Birthplace resolution to canonical coordinates and timezone
- Historical UTC-offset calculation from the submitted birth date
- Lagna, Moon sign, Nakshatra, planetary signs, degrees, and houses
- North Indian chart representation
- Current Vimshottari Dasha data when available
- Structured interpretations covering personality, career, education, relationships, money, home, personal balance, and timing

### Compatibility

- Detailed Ashtakoot or Gun Milan calculation
- Overall score and individual Koota factors
- Strengths, areas to understand, and classical adjustments
- Factor explanations describing what each Koota means and why its score was awarded

### Reports

- Persistent Kundli and compatibility report history
- User ownership checks on report access
- Structured A4 PDF downloads
- Planetary, Dasha, and compatibility tables
- Compact multi-page layouts with plain-language interpretations

### RAG-style astrology assistant

- The authenticated `/api/assistant/ask` and `/api/assistant/report` endpoints use the signed-in user's latest saved Kundli and return chart facts, source citations, retrieval details, and graph context.
- The retrieval corpus is `apps/api/app/knowledge/vedic_astrology.json`. Sentence Transformers creates local `all-MiniLM-L6-v2` semantic embeddings, and FAISS `IndexFlatIP` searches for up to four relevant passages.
- NetworkX builds a graph of planets, signs, houses, and interpretive concepts, then connects the user's calculated placements to that graph. Retrieved passages, verified chart facts, and related graph concepts are assembled as the answer context.
- This retrieval and graph pipeline runs without an OpenAI key. If a key is configured, the OpenAI Responses API can write the response; otherwise the app assembles a cited extractive response from chart facts and retrieved passages. The extractive fallback can include several passages, so the answer may be broader than the question.
- The regular API requirements include FAISS, NetworkX, and sentence-transformers. The first local semantic request downloads `all-MiniLM-L6-v2`. If those components are unavailable, deterministic feature-hash embeddings and Python vector/graph fallbacks keep the app usable, with lower retrieval quality.
- Run `python scripts/evaluate_astrology_assistant.py` from `apps/api` for a small benchmark of retrieval recall, citation ID validity, detected unsupported placement patterns, and latency. It is a smoke benchmark, not a comprehensive answer-quality evaluation.

#### Assistant request flow

```text
User question + latest owned Kundli
  -> embed question locally
  -> retrieve matching Jyotisha passages with FAISS
  -> build chart-placement context with NetworkX
  -> generate a cited answer with OpenAI, or assemble an extractive fallback
  -> show citations and retrieval details in the Kundli page
  -> save personalized overviews as reports that can be downloaded as PDFs
```

### Reliability

- Calculation caching based on birth data and provider configuration
- Navamsha as the default provider
- Optional VedAstro provider
- Deterministic mock provider for automated tests
- Bounded retries for temporary Navamsha failures
- Graceful Kundli generation when optional Dasha data is unavailable
- Structured fallback interpretations when an OpenAI API key is not configured

## Architecture

```text
celestia/
  apps/
    web/                      Next.js and React frontend
      src/app/                Application routes
      src/components/         Shared UI components
      src/features/           Authentication and dashboard features
      src/lib/api/            Typed API clients
      src/types/              Frontend domain types
    api/                      FastAPI backend
      app/api/                HTTP routes and dependencies
      app/core/               Configuration, database, and security
      app/models/             SQLAlchemy models
      app/providers/          Astrology provider adapters
      app/repositories/       Persistence abstractions
      app/services/           Domain and interpretation services
      tests/                  Unit and integration tests
  docs/                       Design and implementation notes
  output/pdf/                 Generated project documents
  tmp/                        Temporary local artifacts
```

### Main request flow

```text
Authenticate
  -> resolve birthplace and timezone
  -> calculate Kundli or compatibility
  -> normalize and cache provider data
  -> create a grounded interpretation
  -> persist the report
  -> display or download the PDF
```

The interpretation layer receives calculated chart or compatibility fields. It does not calculate planetary positions or compatibility scores.

## Technology stack

- Next.js 15, React 19, and TypeScript
- FastAPI and Pydantic
- FAISS, sentence-transformers, and NetworkX for local retrieval-augmented astrology responses
- SQLAlchemy with SQLite for local development
- Argon2 and PyJWT
- Navamsha and VedAstro provider adapters
- Nominatim and timezonefinder
- OpenAI Responses API for optional structured interpretations
- ReportLab for PDF generation
- Pytest for backend tests

## Local setup

### 1. Configure the API

From the repository root:

```powershell
cd apps\api
Copy-Item .env.example .env
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Update `apps/api/.env` with at least:

```dotenv
JWT_SECRET=replace-with-a-long-random-secret
ASTROLOGY_PROVIDER=navamsha
NAVAMSHA_API_KEY=your-navamsha-key
FRONTEND_ORIGIN=http://127.0.0.1:3000
```

For live generated interpretations, optionally add:

```dotenv
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

The astrology assistant uses local `all-MiniLM-L6-v2` embeddings by default. Set `ASTROLOGY_EMBEDDING_PROVIDER=openai` to use the configured OpenAI embedding model instead. The first local embedding run downloads the model; after that it is cached by the model library. OpenAI generation is optional; without a key, the assistant returns a cited extractive response. This feature's local embedding model is separate from the existing structured Kundli interpretation fallback.

Without `OPENAI_API_KEY`, AstroLive produces deterministic structured interpretations so report generation remains available.

Start the API:

```powershell
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Configure the web application

In a second terminal:

```powershell
cd apps\web
Copy-Item .env.example .env.local
npm install
npm run dev
```

The web application runs at `http://127.0.0.1:3000` and uses:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

## Provider selection

Use one of the following values in `apps/api/.env`:

```dotenv
ASTROLOGY_PROVIDER=navamsha
ASTROLOGY_PROVIDER=vedastro
ASTROLOGY_PROVIDER=mock
```

- `navamsha` is the default live provider and requires `NAVAMSHA_API_KEY`.
- `vedastro` is an alternative provider using `VEDASTRO_API_URL` and `VEDASTRO_API_KEY`.
- `mock` is deterministic and intended only for offline development and tests. Its output is not an astrological reading.

Restart the API after changing provider or environment settings.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup` | Create an account |
| `POST` | `/api/auth/login` | Authenticate |
| `GET` | `/api/auth/me` | Restore the current user |
| `POST` | `/api/auth/logout` | Complete the client logout flow |
| `POST` | `/api/kundli` | Generate or retrieve a Kundli |
| `GET` | `/api/kundli/latest` | Retrieve the latest Kundli |
| `POST` | `/api/compatibility` | Generate a compatibility report |
| `GET` | `/api/reports` | List the current user's reports |
| `GET` | `/api/reports/{id}` | Retrieve one owned report |
| `GET` | `/api/reports/{id}/pdf` | Download a report as PDF |
| `POST` | `/api/assistant/ask` | Ask about the latest Kundli using retrieved sources and graph context |
| `POST` | `/api/assistant/report` | Generate a cited personalized overview from the latest Kundli |
| `GET` | `/health` | Check API health |

Authenticated API requests use:

```http
Authorization: Bearer <access-token>
```

## Testing and validation

Run backend tests:

```powershell
cd apps\api
pytest -q
```

Run the frontend type check:

```powershell
cd apps\web
npm run typecheck
```

Current verified baseline:

- 13 backend tests passing
- Frontend TypeScript validation passing

The tests cover authentication, report ownership, Kundli caching, compatibility, PDF downloads, provider normalization, structured interpretations, and temporary Dasha failures.

Run the astrology assistant retrieval smoke benchmark separately:

```powershell
cd apps\api
python scripts/evaluate_astrology_assistant.py
```

It uses a small fixed set of questions and a synthetic chart; its metrics are useful for checking the retrieval path, not for claiming broad response quality.

## Known limitations

- The sidebar links to `/profile`, but a complete profile-management page is not implemented.
- The dashboard recent-reports card and several placeholder controls are not connected to live actions.
- Access tokens are stored in browser local storage; production authentication needs further hardening.
- Password reset, email verification, token revocation, and rate limiting are not implemented.
- SQLite and startup schema alterations should be replaced with a production database and formal migrations.
- Browser end-to-end, accessibility, load, and production-observability testing are still needed.
- Public Nominatim usage requires compliance review, attribution, caching, and an appropriate search interaction.
- The North Indian chart visualization is a simplified prototype.

## Important data note

Astrology calculations depend on accurate birth date, time, and location. Interpretations are generated from the calculated provider response and are intended as explanations of a traditional astrological system, not guaranteed predictions.
