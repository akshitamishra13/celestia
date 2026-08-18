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
