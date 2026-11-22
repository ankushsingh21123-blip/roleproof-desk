# Hosted verification: RoleProof Django

Verified 23 November 2026 against https://roleproof-django.vercel.app/ in fresh anonymous browser contexts, using the real remote PostgreSQL store.

## Public browser acceptance

All five browser flows passed after the capacity recovery:

- Create a fictional ticket, update its status, reload from the database, search and filter.
- No horizontal overflow at 320, 390 and 1280 CSS pixels.
- Modal keyboard focus stays inside; Escape closes it when not saving.
- HTML-like ticket text stays text and creates no executable image element.
- A saving form cannot be dismissed; modal document-scroll locking is restored afterward.

Hosted desktop and mobile screenshots were visually inspected for readable text, complete rows and sensible spacing. No browser errors were recorded in the create/update/persistence flow. These are dated acceptance checks, not an uptime guarantee.

## Capacity incident and recovery

The first public browser run passed the create/update/persistence flow but four later fresh-workspace flows failed. The shared synthetic store had reached its internal 100-workspace guard. A health response of 200 did not mean fresh workspaces were available.

The same fresh-workspace limitation was confirmed on the original RoleProof Desk, Python and Next demos. The existing free project's two ticket tables occupied 409,600 bytes, with 100 active workspaces and 531 fictional tickets. This was an application guard, not a full-storage error.

`capacity-recovery.sql` changed only that guard from 100 to 500. Transaction checks verified the function definition otherwise stayed identical, execution grants and owner stayed identical, and every existing workspace and ticket stayed identical. No paid plan, storage allocation, billing, seven-day retention or per-workspace rate/record limit changed. No visitor data was deleted.

Afterward, each of the four public ticket demos created a fresh workspace with HTTP 201, loaded five fictional tickets, and reopened the same workspace with HTTP 200 and unchanged records. Secure, HttpOnly and SameSite=Strict cookie flags were checked. The complete five-flow public Django browser suite then passed.

Semantic Support Atlas shares the database project but uses separate read-only vector tables/functions. Its fresh anonymous retrieval and responsive-browser checks also passed during the incident; the ticket-workspace guard did not block semantic retrieval.

## Reproducible local checks

- `ROLEPROOF_LOCAL=1 python test_django.py`: 15 Django integration tests against actual local PostgreSQL through PGlite.
- `node test_capacity.mjs`: separate actual-PostgreSQL migration/capacity regression. Reproduces the old cap, proves preservation, checks recovery and the new cap, and checks safe replay rejection. It is not a hosted load test.
- `PROOF_URL=https://roleproof-django.vercel.app npx playwright test`: the public browser suite. It creates temporary fictional workspaces, so run it after meaningful changes rather than repeatedly consuming demo capacity.

The recovery script is one-time and intentionally rejects an already-changed or unexpected guard. Do not apply it blindly to another database. Fresh installations use the 500-workspace guard already present in `schema.postgres.sql`.

## Boundaries

This is an AI-assisted synthetic portfolio application, not unaided authorship, an employer assessment, a production customer service or evidence of professional Django experience. The backend uses Django HTTP routing/views/middleware/cookies and direct scoped PostgreSQL RPC. It does not use Django ORM, models, migrations or built-in user authentication.

Cookie-separated workspaces are not customer authentication. Do not enter private or customer information. Hosting and database free-tier limits can still pause or constrain the demo. The new 500-workspace guard remains finite.
