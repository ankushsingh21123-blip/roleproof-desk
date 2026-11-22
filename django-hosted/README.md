# RoleProof Django

An AI-assisted synthetic request desk: React/TypeScript frontend, Django HTTP API and a real isolated PostgreSQL store accessed through a scoped RPC. This folder is a separate mode. Existing RoleProof applications are unchanged.

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

## Verification as of 22 November 2026

- 15 Django integration tests passed against the actual local PostgreSQL engine in PGlite, including roundtrip persistence, workspace isolation, stale-version conflicts, cookie flags, validation, error redaction, origin checks, CSV safety and static response security.
- Five separate browser flows passed when serving this Django app locally while calling the **real remote PostgreSQL database**: create/update/reload/search/filter; no horizontal overflow at 320/390/1280 pixels; keyboard focus and Escape; HTML-like text; busy-save behavior.
- Desktop and mobile screenshots from that browser run were visually inspected.

These are not yet a public-host acceptance claim. Public-host results, if completed, are recorded separately in `HOSTED_VERIFY.md`.

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
npx playwright install chromium
npx playwright test
```

The root package includes PGlite and Playwright test dependencies. The Django tests start and stop a local PostgreSQL fixture. Browser tests use the app's configured remote synthetic store, so they create temporary fictional workspaces. Set `PROOF_URL` to an already deployed host for browser acceptance without starting a local server.

## Provenance

The React queue and PostgreSQL RPC schema derive from this repository's existing RoleProof Desk work. The Django HTTP layer is a new port, retaining the visible synthetic-data and AI-assistance labels. Runtime dependencies are pinned in `requirements.txt`. React/Vite and PGlite/Playwright remain their upstream projects, not original framework work.
