# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository.

## What this is

Order Enquiry System: a FastAPI + React app for entering, importing, and
tracking orders, with a Gmail-based intake pipeline (unattended email →
Excel import → PDF receipt → draft reply) and a sales dashboard.

Order table: `OrderID (PK, autoincrement), ProductID, Qty, Price, OrderDate`.

## Architecture

```
backend/app/
  main.py          FastAPI app, CORS, router registration
  database.py      SQLAlchemy engine/session (SQLite by default, Postgres via DATABASE_URL)
  models.py        Order ORM model
  schemas.py       Pydantic request/response models
  crud.py          DB queries: CRUD + sales aggregation (summary/by-day/top-products)
  excel_utils.py   Parses an uploaded .xlsx/.xls into validated OrderCreate rows
  receipts.py      Renders a one-page PDF receipt for an order (fpdf2)
  routers/
    orders.py      /api/orders CRUD, /api/orders/import, /api/orders/{id}/receipt
    sales.py       /api/sales/summary, /by-day, /top-products (dashboard data)

backend/email_watcher.py   Standalone script (not part of the API process):
  polls IMAP for unread "Order Enquiry" emails, extracts the Excel attachment,
  POSTs it to /api/orders/import, then fetches the inserted orders back and
  saves a plain-text receipt as a Gmail draft reply (IMAP APPEND to
  IMAP_DRAFTS_FOLDER) — it never sends automatically.

frontend/src/
  App.jsx                    Tab switcher: Orders vs Dashboard
  api.js                     fetch wrappers, one function per endpoint
  components/OrderForm.jsx, ImportForm.jsx, SearchBar.jsx, OrderTable.jsx
  components/Dashboard.jsx   Stat tiles + inline-SVG bar charts (no chart library)
```

Data flow for the email pipeline: Gmail inbox → `email_watcher.py` (IMAP) →
`POST /api/orders/import` → SQLAlchemy insert → `email_watcher.py` reads the
new orders back via `GET /api/orders/{id}` → drafts a reply into Gmail. The
watcher only talks to the backend over HTTP; it has no direct DB access.

## Commands

```bash
# Backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000

# Backend tests + lint (run from repo root; also covers root tests/)
python -m pytest -q
flake8 .

# Frontend
cd frontend && npm install
npm run dev      # http://localhost:5173, proxies /api to :8000
npm run build
npm run lint      # oxlint

# Email watcher (needs backend running + backend/.env configured)
cd backend && python email_watcher.py --once
```

## Conventions

- Order field names are PascalCase end-to-end (`OrderID`, `ProductID`, `Qty`,
  `Price`, `OrderDate`) — matches the DB columns, Pydantic schemas, and the
  JSON the frontend consumes. Don't snake_case them.
- New read endpoints that aggregate across orders belong in `crud.py` +
  `routers/sales.py`, following the existing `date_from`/`date_to` filter
  pattern already used by `search_orders`.
- The frontend has no chart library dependency — `Dashboard.jsx` draws bar
  charts as inline SVG. Keep it that way unless the dashboard's needs
  genuinely outgrow it; don't add recharts/d3 for cosmetic reasons.
- `backend/orders.db` is a local SQLite file, gitignored — safe to delete for
  a clean slate.
- The email watcher must never send email directly; it only ever creates a
  **draft** so a human reviews/sends the reply.

## Deployment

CI/CD is `.github/workflows/ci-cd.yml`: every push/PR to `main` runs pytest +
flake8 + a frontend build. Pushing a `v*` tag additionally triggers the
`deploy` job, which POSTs to two Render deploy hook secrets
(`RENDER_BACKEND_DEPLOY_HOOK`, `RENDER_FRONTEND_DEPLOY_HOOK`).

Hosting is Render, defined in `render.yaml` (backend web service + static
frontend + managed Postgres). See the README's "Cloud deployment" section for
the one-time setup steps (connecting the repo as a Render Blueprint, wiring
`CORS_ORIGINS`/`VITE_API_BASE_URL`, adding the deploy hook secrets) — those
steps require access to the Render and GitHub dashboards and can't be done
from this repo alone.

The email watcher is not a web service; run it as a Render Background
Worker/Cron Job (or any always-on machine) with the same env vars as
`backend/.env.example`.
