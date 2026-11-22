# RoleProof Django

An AI-assisted synthetic request desk: React/TypeScript frontend, Django HTTP API and a real isolated PostgreSQL store accessed through a scoped RPC. The Django HTTP application is a separate mode. Its shared demo database has a bounded workspace-cap recovery described in `HOSTED_VERIFY.md`; existing records and permissions were preserved.

The Django layer implements URL routing, JSON request handling, middleware, response headers, cookie handling and static responses. It calls PostgreSQL directly over the database provider's HTTPS RPC. It does **not** proxy requests through the Flask or Node modes and does **not** use Django ORM, Django models, migrations or Django's user authentication system.

## Features

- Create fictional tickets, list/search/filter the queue and update status.
- Persist records in PostgreSQL and reload them in the browser.
- Separate synthetic workspaces using a random HttpOnly cookie; workspaces expire after seven days.
- Optimistic version checks reject stale updates; one workspace cannot update another workspace's ticket.
- JSON validation, same-origin write checks, an 8192-byte request cap and redacted storage failures.
- Metrics and spreadsheet-formula-safe CSV export.
- Keyboard focus handling, inert rendering of HTML-like text, responsive queue and busy-save behavior.

This is substantial AI-assisted portfolio implementation, debugging and testing, not independent authorship, a candidate assessment, unaided coding ability or production customer experience. Do not enter private or customer information. Cookie-isolated demo workspaces are not a customer authentication service. Free-tier hosting and database limits apply.

## Verification as of 23 November 2026

Live demo: https://roleproof-django.vercel.app/

- 15 Django integration tests passed against the actual local PostgreSQL engine in PGlite, including persistence, workspace isolation, stale versions, cookie flags, validation, origin checks, CSV safety and error handling.
- A separate PostgreSQL migration regression reproduced the old 100-workspace cap, preserved every existing record and permission while changing only the cap, recovered fresh workspaces, enforced the new 500-workspace cap and rejected a repeated migration safely.
- Five browser flows passed against the public Django deployment and real remote database: create/update/reload/search/filter; no horizontal overflow at 320/390/1280 pixels; keyboard focus and Escape; inert HTML-like text; busy-save behavior.
- Hosted desktop and mobile screenshots were visually inspected.

The initial hosted run exposed the shared store's full 100-workspace cap. It was not counted as a pass. A cap-only recovery in the existing free project preserved all 100 workspaces and 531 tickets and was followed by successful fresh-workspace checks across the Django, original, Python and Next demos. See `HOSTED_VERIFY.md` for scope and limitations.

## Run

Use Python 3.10 or newer locally; the deployed Python runtime can use 3.12.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
ROLEPROOF_LOCAL=1 python local_server.py
```

Open the address printed by the local server, port 8806. `ROLEPROOF_LOCAL=1` is for localhost only. Production does not set it and uses Secure cookies and HTTPS origin checks.

The checked-in database client key is intentionally publishable, with only the existing scoped demo RPC accessible. No service-role key, admin credential or private project database is included. The SQL fixture is a reproducible local test schema, not a new production migration.

## Rebuild frontend and test

The checked-in static assets are built from `frontend/` using Vite.

```sh
cd frontend
npm install
npm run build
cd ..
npm install
ROLEPROOF_LOCAL=1 python test_django.py
node test_capacity.mjs
npx playwright install chromium
npx playwright test
```

The root package includes PGlite and Playwright test dependencies. The Django tests start and stop a local PostgreSQL fixture. Browser tests use the app's configured remote synthetic store, so they create temporary fictional workspaces. Set `PROOF_URL` to an already deployed host for browser acceptance without starting a local server.

## Provenance

The React queue and PostgreSQL RPC schema derive from this repository's existing RoleProof Desk work. The Django HTTP layer is a new port, retaining the visible synthetic-data and AI-assistance labels. Runtime dependencies are pinned in `requirements.txt`. React/Vite and PGlite/Playwright remain their upstream projects, not original framework work.
