# WalkGuide API

A small FastAPI backend for the Little India & Kampong Glam walking guide's
content editor. Replaces the old localStorage-only editor with a real
database, so edits from any team member, on any device, show up instantly
for every visitor — no developer redeploy required.

## Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI app, CORS, router wiring
│   ├── config.py          # settings (reads .env)
│   ├── database.py        # SQLAlchemy engine/session
│   ├── models.py          # Place, User tables
│   ├── schemas.py         # request/response validation
│   ├── security.py        # password hashing + JWT
│   ├── deps.py             # get_current_user (login check)
│   ├── seed_content.json  # your original 44 places + menu/route config
│   └── routers/
│       ├── auth.py         # POST /auth/login, GET /auth/me
│       ├── places.py       # GET/POST/PUT/DELETE /places
│       └── config.py       # GET /config (menu, hotels, route)
├── scripts/
│   ├── seed_places.py      # one-time: load the 44 places into the DB
│   └── create_user.py      # create/update an editor login
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env — at minimum, change JWT_SECRET to a real random value:
python -c "import secrets; print(secrets.token_hex(32))"
```

## Load your existing content into the database

```bash
python -m scripts.seed_places
```

## Create a login for yourself (and anyone else who should edit content)

```bash
python -m scripts.create_user
```

Run this once per team member — each person gets their own email + password.

## Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs (Swagger UI) —
useful for testing endpoints directly before the frontend is wired up.

## Deploying

- Swap `DATABASE_URL` in `.env` to a real Postgres instance for anything
  beyond a single small deployment (SQLite is fine for low-traffic use, but
  doesn't handle concurrent writes as gracefully).
- Set `CORS_ORIGINS` to your real production frontend URL(s).
- Run behind a real process manager / reverse proxy (e.g. `gunicorn` with
  `uvicorn` workers behind nginx, or your host's standard Python app
  deployment) rather than `--reload` in production.
- Never commit `.env` — it's already covered by `.gitignore` conventions,
  but double-check before pushing.
