# RoleProof Python + PostgreSQL

AI-assisted portfolio extension of the existing RoleProof React ticket desk, not an employer assessment. Substantial AI assistance was used for implementation, debugging and testing. Synthetic data only. No claim of unaided user authorship.

Status: local API and browser checks passed 17 Nov 2026. Public Python deployment is not yet verified. Existing Next/Node variants remain separate and unchanged.

Python Flask calls the existing isolated portfolio PostgreSQL RPC directly over HTTPS using a publishable key. It does not proxy the Node backend. The database schema is `../schema.postgres.sql`. No service-role key or database password is needed. Each Python browser gets a new independent random workspace cookie (SHA256 only sent to the database). The RPC enforces private schema access, isolation, atomic updates, 100 total active workspaces, 40 tickets/workspace, 20 writes/minute and seven-day expiry. Existing Node demo sessions are not reused.

Routes: health, session, ticket list/create/update, Python status counts at `/api/metrics`, CSV at `/api/export.csv`. CSV escapes formula-leading values. Same-origin JSON writes, request-size bounds, HttpOnly/Secure/SameSiteStrict cookie, generic errors and no-store headers. Static paths are allowlisted. No private customer records, accounts, production authentication or uptime guarantees. Host outages and quota exhaustion can stop this bounded anonymous demo.

`static/` contains the compiled existing React/TypeScript source from `../main.tsx` and `../style.css`, built with the pinned root lockfile. Footer identifies Python+PostgreSQL. The UI is not a new frontend or a claim of independent authorship. Rebuild with `npm ci --ignore-scripts && npm run build:legacy`, copy dist to static and update the small footer label to match this variant.

Deployment: separate Vercel Hobby personal/noncommercial Flask project, root `python-hosted`, production branch `proof-python-postgres`. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY to the existing isolated portfolio project's public configuration. No billing changes/card/trial/paid add-ons. Hobby limits pause service, not paid overage. No new terms or paid approval implied.

Tests: root npm ci, then Python venv install requirements.txt. `python test_python.py` launches an actual PGlite PostgreSQL fixture via `test_pg_bridge.mjs`: 13 tests pass (create/update/reload, foreign workspace404, stale409, CSRF403, cookie protections, validation, bounds, metrics, safe CSV and error redaction). Five existing Playwright flows also passed against Flask/local PostgreSQL, including320/390/1280 responsive layout, modal focus, escaped HTML titles and busy-save behavior. These are local tests, NOT hosted proof. `local_test_server.py` is only a local fixture and is never a production server.

Sources checked17Nov2026: https://vercel.com/docs/functions/runtimes/python , https://vercel.com/docs/plans/hobby . Flask BSD-3-Clause; existing dependency licences retained. Not a project-wide licence grant over other code.
