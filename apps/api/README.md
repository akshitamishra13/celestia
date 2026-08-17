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

Authentication now includes signup, login, logout, current-session lookup, Argon2 password hashing, and HTTP-only session cookies.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and replace `JWT_SECRET` before any shared deployment.
