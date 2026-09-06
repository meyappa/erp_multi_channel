# ChannelForge ERP

Multi-channel commerce operating system for Amazon, Shopee, Lazada, TikTok Shop, Shopify, and eBay.

Stack: FastAPI + SQLAlchemy (async) + Next.js 14. Demo mode uses SQLite so the app runs without Redis or Postgres. Production can switch to PostgreSQL (Supabase) and Celery + Redis.

## Architecture

See `docs/ARCHITECTURE.md`.

Core formula (auditable):

```
gross_profit = selling_price - cogs - marketplace_fees - shipping_cost - returns_refunds - ads
```

Every calculation can persist a `GrossProfitSnapshot` row.

## Quick start (local)

```bash
python3 -m pip install --break-system-packages -r backend/requirements.txt
cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`.

Demo users (password in parentheses):

- ava.chen@forge.example (admin123) — Admin
- marco.lee@forge.example (manager123) — Manager
- sofia.ng@forge.example (account123) — Accountant
- diego.ruiz@forge.example (warehouse123) — Warehouse
- viewer@forge.example (viewer123) — Viewer

## Production config

Copy `backend/.env.example` and set:

- `DATABASE_URL` — Supabase Postgres async URL (`postgresql+asyncpg://...`)
- `REDIS_URL`, `CELERY_BROKER_URL`
- `SECRET_KEY`, `ENCRYPTION_KEY`
- `USER_LLM_API_KEY` — optional, for live listing copy (heuristic fallback is always on)

Apply `supabase/schema.sql` in the Supabase SQL editor if you want the schema created outside SQLAlchemy.

## Tests

```bash
cd backend && PYTHONPATH=. python3 -m pytest -q
```

## Docker

```bash
docker compose up --build
```

API docs: `http://localhost:8000/docs`
