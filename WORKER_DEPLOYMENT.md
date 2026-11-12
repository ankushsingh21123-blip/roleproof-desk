# Workers + D1 deployment variant

Status: implementation verified locally; no public full-stack deployment verified yet.
The existing GitHub Pages sandbox is still browser-only. Do not use its URL as backend/database proof.

This variant keeps the React frontend and replaces only the Python server with a JavaScript Worker and D1 SQLite. The Python version stays loopback-only. No AI model, API key, credit card or payment is needed to run the local checks.

## Reproduce locally

Requires Node.js 22+, npm, Python 3.10+ and internet for the initial dependency/browser downloads.

```sh
npm ci --ignore-scripts
npm run build
npm run test:api
npm run test:worker
npx playwright install chromium
npm run test:e2e
npm run test:e2e:worker
npm audit
```

`test:worker` creates a temporary D1 runtime directory, applies `schema.sql`, starts the real local Workers runtime, runs API integration tests and stops/removes it. It does not call remote D1. Browser tests use a local D1 directory under ignored `.wrangler/`. Never upload that directory or use real data. The two browser suites must run sequentially.

To explore the Worker variant locally:

```sh
npx wrangler d1 execute roleproof-desk-demo --local --file schema.sql
npm run dev:worker
```

Open the loopback URL printed by Wrangler. It runs the compiled React frontend, API and a local persistent SQLite-backed D1 implementation. This is useful preparation, not evidence of a deployed app.

## Security and demo limits

- Synthetic data only. This is a public portfolio demo, not a secure customer-data service or an independently audited production system.
- The browser receives a random 256-bit opaque cookie. Only its SHA-256 hash is stored in D1. The cookie is HttpOnly, SameSite=Strict and Secure on HTTPS. There is no user signup, password, real account or third-party identity provider.
- Every ticket read/update is scoped by that cookie's server-side workspace. Guessing another ticket ID cannot read or modify another workspace. Clearing the cookie loses access; there is no recovery.
- Workspace access expires after seven days. Expired rows are removed on the next new-workspace request. This is lazy cleanup, not guaranteed deletion at exactly seven days. The hosting provider may retain backups and infrastructure logs under its own terms.
- Maximum 100 active workspaces, 40 tickets per workspace, and 20 mutation attempts per minute per workspace. Capacity/rate-limit errors fail closed. Anonymous visitors can exhaust the demo's capacity; this is an availability limitation, not a claim of comprehensive abuse resistance.
- No cross-origin writes. Mutations require the exact current Origin, JSON and a custom client header. Strict field/enum/length checks and a bounded request-body reader reject oversized input. SQL is parameterized. Atomic version checks return 409 on stale writes.
- The app sends no custom analytics or raw IP addresses to D1. Cloudflare still processes network requests. Observability logging is disabled in the provided config. No browser variables contain credentials.
- No real confidential data, customer details, credentials, `.env`, database files or device information belong in tickets.

## Free-plan deployment prerequisites

Do not run a deployment unless the actual account is on Workers Free, no paid subscription/credit-card step is selected, and the verified account is the intended owner. The current configuration contains a deliberately invalid placeholder D1 database ID. It is not a ready remote database binding.

1. Verify the existing Cloudflare account's email, if its dashboard requires it.
2. Check the current Workers plan is Free. Stop if a paid plan, card, trial billing, paid storage or upgrade is requested.
3. Create a D1 database named `roleproof-desk-demo` on the Free plan. Put its actual non-secret database ID into `wrangler.jsonc`. Keep `binding` equal to `DB`.
4. Apply `schema.sql` to that specific remote D1 database using the dashboard SQL console, or the authenticated ordinary CLI: `npx wrangler d1 execute roleproof-desk-demo --remote --file schema.sql`.
5. Deploy this reviewed source with a normal Cloudflare GitHub integration or authenticated Wrangler deployment. Build command: `npm ci --ignore-scripts && npm run build`. The Worker entry is `worker.mjs`; assets come from `dist/`. Do not deploy the Python server or the static `docs/` sandbox as the backend.
6. Read the actual returned deployment URL. Verify `/api/health` reads the bound D1 successfully, then run a fresh browser create/update/reload test against that HTTPS URL. Check a second clean browser cannot see the first browser's new ticket. Restart/new-client persistence, Secure cookie, stale-update rejection and responsive screenshots are required evidence.
7. Only after those checks record the real URL, exact deployed commit, test time and remaining limits. A green build alone does not satisfy this step.

No paid upgrade is authorized. Free limits can make the app unavailable; that is preferable to an automatic charge. Official plan docs checked on 12 Nov 2026:

- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/d1/platform/pricing/

The documented Free plan currently includes 100,000 Worker requests/day, D1 5 million rows read/day, 100,000 rows written/day and 5 GB total storage. D1 rejects queries when Free limits are exhausted. Limits can change; verify the account and current docs before deployment. No free-forever or uptime guarantee is made here.

## Attribution

This extension was implemented and tested with AI assistance for Ankush Singh's portfolio. It does not establish independent personal authorship, work experience or performance on any employer assessment. Dependencies retain their licenses. The original Python/local and separate GitHub Pages limitations remain applicable to those versions.
