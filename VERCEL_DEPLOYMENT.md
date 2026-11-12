# Vercel + PostgreSQL portfolio variant

This branch adds a Vercel Node API and isolated Supabase PostgreSQL database. It is AI-assisted synthetic portfolio work, not a personal assessment or a claim of unaided authorship.

## Status

Implementation and local PostgreSQL/HTTP tests passed. Live deployment and live acceptance remain pending. Do not use this document as evidence of a finished hosted app until a dated live result is added.

## Design

React calls a same-origin Node API. The API hashes a random 256-bit HttpOnly workspace cookie and invokes a narrow PostgreSQL RPC. Raw cookie values never enter the database. The database uses an unexposed private schema with RLS and no anon/authenticated table grants. A SECURITY DEFINER function with a fixed search path validates every request and scopes each query to the supplied hash. Anon can call only that public function, not private tables. The publishable key is public, not a database admin key; no service-role key belongs in this app.

Database row locks serialize each workspace's writes; a global advisory lock caps active workspaces at100. Each workspace expires after7days, with cascade cleanup on new-session creation, has at most40tickets and20write attempts/minute. Optimistic versions prevent stale updates. The public RPC accepts bearer workspace hashes, so this remains a bounded anonymous demo, not an authentication system for private/customer records. Random new-session traffic can exhaust the shared100workspace capacity; there is no claim of production anti-abuse protection.

All entries must be fictional. Browser workspace cookies are not user accounts. Clear site cookies to lose access. Data expires and free hosts can suspend service. Do not enter confidential data.

## Deployment

1. In an isolated Supabase Free project, apply `schema.postgres.sql` using an approved credential route. Never run it against an existing product database.
2. Import this branch into a new Vercel Hobby project, keeping it a personal non-commercial portfolio demo.
3. Set `SUPABASE_URL` to the actual project's HTTPS URL and `SUPABASE_PUBLISHABLE_KEY` to its publishable key. Both are public values. Never set the database password or service-role key in Vercel.
4. Build with `npm run build`. The Vercel rewrite routes `/api/*` to `api/desk.mjs`.
5. Run remote acceptance: real DB health; session cookie flags; create/update/reload; stale409; another workspace404; bad input400; CSRF403; mobile/desktop UI. Local green tests do not replace this.

Free-plan conditions checked November13,2026: Vercel Hobby is personal non-commercial only and may pause usage at limits. Supabase Free has500MB DB,2active projects and pauses after1week inactivity. There is no uptime guarantee or automatic paid upgrade authorized. No card, trial or paid add-on is needed. Hosting services are free tiers; the application dependencies and PostgreSQL stack are open source, but this does not make hosted Vercel an open-source service.

Sources:
- https://vercel.com/docs/plans/hobby
- https://vercel.com/docs/functions/runtimes/node-js
- https://supabase.com/pricing
- https://supabase.com/docs/guides/api/securing-your-api

## Reproducible checks

`npm ci --ignore-scripts && npm run build && npm run test:postgres`

The PostgreSQL tests use PGlite's actual PostgreSQL WASM engine, not a SQL mock. HTTP tests exercise the Node API against that engine. These tests are local, not a hosted database assertion. `npm audit --audit-level=low` checked no known advisories on the build date. Existing Python/Worker tests remain separate variants.

Dependency licences: React/ReactDOM/Vite MIT; TypeScript/Playwright/PGlite Apache-2.0 (from installed package metadata). PostgreSQL retains its own licence. Preserve dependency licences and inspect actual installed package metadata for redistribution.
