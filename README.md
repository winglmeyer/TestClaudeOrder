# Order Enquiry System

A small order enquiry app: a FastAPI backend backed by SQLite/Postgres, a React
frontend for searching/entering/importing orders and viewing a sales
dashboard, and an IMAP watcher that ingests Excel attachments from
"Order Enquiry" emails, generates a PDF receipt per order, and drafts a reply
email (saved to the mailbox's Drafts folder, never auto-sent).

Order table columns: `OrderID, ProductID, Qty, Price, OrderDate`.

## Backend

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs once running.

Endpoints:
- `POST /api/orders` — create an order
- `GET /api/orders` — search orders (`order_id`, `product_id`, `date_from`, `date_to`)
- `GET /api/orders/{id}` / `PUT /api/orders/{id}` / `DELETE /api/orders/{id}`
- `POST /api/orders/import` — upload an Excel file (multipart `file`) with columns
  `OrderID, ProductID, Qty, Price, OrderDate`; rows are validated and inserted,
  a per-row error list and the list of inserted `order_ids` is returned
- `GET /api/orders/{id}/receipt` — a one-page PDF receipt for the order
- `GET /api/sales/summary` — total orders, qty, revenue, avg order value
  (optional `date_from`/`date_to`)
- `GET /api/sales/by-day` — revenue/qty/order count grouped by day
- `GET /api/sales/top-products` — qty/revenue grouped by product, highest revenue first

Config via environment variables (see `backend/.env.example`): `DATABASE_URL`, `CORS_ORIGINS`.

## Frontend

```
cd frontend
npm install
npm run dev
```

Opens on http://localhost:5173. Two tabs:
- **Orders** — add an order, import an Excel file, search/edit/delete existing
  orders, and download each order's PDF receipt
- **Dashboard** — stat tiles (total orders/revenue/avg order value) plus
  revenue-by-day and top-products charts, filterable by date range

The dev server proxies `/api` calls to the backend on port 8000.

## Email watcher (Gmail integration)

Polls a mailbox by IMAP for unread emails with "Order Enquiry" in the subject,
pulls the first `.xlsx`/`.xls` attachment from each, and POSTs it to the
backend's `/api/orders/import` endpoint — the same path used by the frontend's
import form. An email is marked read only after a successful import, so
failures are retried on the next poll.

After a successful import, the watcher fetches the newly inserted orders back
from the API, builds a plain-text receipt, and saves it as a **draft** reply
(via IMAP APPEND to `IMAP_DRAFTS_FOLDER`, default `[Gmail]/Drafts`) addressed
to the original sender — it is never sent automatically, so a person reviews
and sends it from Gmail.

Copy `backend/.env.example` to `backend/.env`, fill in your Gmail IMAP
credentials (`imap.gmail.com`, and an **app password** — Google Account →
Security → 2-Step Verification → App passwords — rather than your account
password), then run:

```
cd backend
python email_watcher.py          # polls forever, on POLL_INTERVAL_SECONDS
python email_watcher.py --once   # single pass, e.g. for a scheduled task/cron job
```

The backend must be running for the watcher to import successfully.

## Tests

```
python -m pytest -q
```

Runs both the existing root tests and the backend API tests (`backend/tests/`).

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push/PR to `main`:
- installs Python deps, runs `pytest`, lints with `flake8`
- installs Node deps and runs `npm run build` for the frontend

Pushing a `v*` tag additionally runs the `deploy` job, which hits two Render
deploy hooks (see below) to redeploy the backend and frontend.

## Cloud deployment (Render)

The backend and frontend deploy as two separate Render services, plus a
managed Postgres database, defined in [`render.yaml`](render.yaml):

1. In the Render dashboard: **New +** → **Blueprint**, point it at this GitHub
   repo. Render reads `render.yaml` and creates:
   - `order-enquiry-db` — a free Postgres instance
   - `order-enquiry-backend` — the FastAPI web service, wired to `order-enquiry-db`
     via `DATABASE_URL` automatically
   - `order-enquiry-frontend` — the static React build
2. After the first deploy, note the actual URLs Render assigned (it appends a
   random suffix if the name is taken). Update, in the Render dashboard:
   - `order-enquiry-backend`'s `CORS_ORIGINS` env var → the frontend's URL
   - `order-enquiry-frontend`'s `VITE_API_BASE_URL` env var → `<backend-url>/api`,
     then trigger a manual redeploy of the frontend so the build picks it up
3. Both services have `autoDeploy: false` — deploys are triggered explicitly
   (matching this repo's existing tag-gated deploy pattern) rather than on
   every push to `main`. To wire that up:
   - In each Render service: **Settings** → **Deploy Hook** → copy the URL
   - Add them as GitHub repo secrets: `RENDER_BACKEND_DEPLOY_HOOK` and
     `RENDER_FRONTEND_DEPLOY_HOOK` (**Settings** → **Secrets and variables** →
     **Actions** in GitHub)
   - Push a tag (e.g. `git tag v0.1.0 && git push origin v0.1.0`) to trigger a deploy

The email watcher (`backend/email_watcher.py`) isn't a web service — it's a
long-running/scheduled script. Options for running it in the cloud:
- Render **Background Worker** or **Cron Job** pointed at the same repo/branch,
  running `python email_watcher.py --once` on a schedule (Cron Job) or
  `python email_watcher.py` continuously (Background Worker), with the same
  IMAP/API env vars set on that service
- Any machine with network access to the deployed backend's `/api/orders/import`
  URL and IMAP credentials, run via Task Scheduler/cron
