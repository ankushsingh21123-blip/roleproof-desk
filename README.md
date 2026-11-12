# RoleProof Desk

AI-assisted synthetic portfolio demo of a support-request queue.

**Live full-stack app:** https://roleproof-desk.vercel.app/

**Deployed source variant:** [deploy-vercel-postgres](https://github.com/ankushsingh21123-blip/roleproof-desk/tree/deploy-vercel-postgres).

React + TypeScript frontend, Node API on Vercel Hobby and isolated Supabase PostgreSQL database. Each browser gets a separate anonymous workspace. Create tickets, filter/search the queue, update statuses and reload to see persisted data.

## Verified live November13,2026,01:44IST

- Actual bound PostgreSQL health read.
- Browser create, API read, status update and reload persistence.
- Secure, HttpOnly, SameSiteStrict session cookie.
- Optimistic update conflict409 and cross-workspace update404.
- No browser JavaScript errors or horizontal overflow at320/390/1280.
- Desktop and mobile pixels inspected for layout/readability.

See `LIVE_POSTGRES_RESULTS.json`, `verify-postgres-deployed.mjs` and `VERCEL_DEPLOYMENT.md`. Local tests use the real PostgreSQL WASM engine plus HTTP integration; they are separate from deployed acceptance. `npm run test:postgres` reproduces local checks. CI also retains the original Python and Worker variant checks.

## Honest scope and limits

This is AI-assisted portfolio work, not a personal hiring assessment, independent-author claim or production/customer-data system. It demonstrates implementation, not proof the owner can explain every line unaided. Roles still need separate skill, eligibility and working-hours checks.

All records are fictional. Never enter private/customer information. Anonymous workspaces expire after7days; cleanup occurs on new-session creation. Global capacity100workspaces,40tickets/workspace,20write attempts/minute. Public-session creation can exhaust capacity; this is not a production anti-abuse system. No admin database credential is used by the app, only a public publishable key and narrow validated RPC. Private tables have RLS and no anon/authenticated grants.

Free hosting is not guaranteed uptime. Supabase can pause after1week inactivity, and Vercel Hobby can pause at usage limits. Vercel Hobby is personal/non-commercial only. No paid subscription, trial, credit card or automatic upgrade was used or authorized. Application dependencies are open source; that does not make every hosting service open source.

## Other variants

- `main` retains the original loopback-only Python/SQLite version.
- `deploy-worker-d1` is the separately tested Cloudflare Worker/D1 variant, not deployed because account email verification was unavailable.
- [GitHub Pages](https://ankushsingh21123-blip.github.io/roleproof-desk/) is a browser-only sandbox, not the hosted database proof.

See `VERCEL_DEPLOYMENT.md` for deployment architecture, safety boundaries, licences and official free-plan sources. Do not point applications to an old branch or screenshot and call it current full-stack deployment proof.
