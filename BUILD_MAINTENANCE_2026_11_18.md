# Build-tool security maintenance: 18 November 2026

AI-assisted maintenance of the existing proof, not a new user skill claim.

The November 18 repository check failed at npm audit: picomatch 4.0.7 and its fdir/tinyglobby/Vite dependants were flagged under GHSA-fc5q-39xc-vjpf. These were development dependencies. This does not establish production exploitability or a compromise.

The registry offered no patched picomatch. A local experiment with the audit-suggested Vite 6.2.7 downgrade revealed other audit findings and was rejected, not published. Current Vite 6.4.6 also retained the affected dependency chain.

## Narrow remediation

- Remove Vite and its React plugin from this branch's legacy production build.
- Pin esbuild 0.28.2 directly and use `build-legacy.mjs` to bundle the unchanged `main.tsx` and imported CSS.
- Keep the same `dist/` assets contract used by Python, Worker and PostgreSQL fixture tests. React remains in production mode; dependency licence notices are linked beside the output JS.
- Next.js build and source stay unchanged. No audit exception, severity threshold change, ignored advisory or forced upgrade.
- The old `vite.config.ts` is removed, since no Vite command remains in the package scripts. Historical documents remain historical; use `npm run build:legacy` to rebuild.

## Verification

Fresh npm install and audit: zero reported vulnerabilities at 18 Nov 06:36 IST. This is a point-in-time dependency report, not a guarantee against unknown flaws.

Local full Next + legacy build passed. Existing PostgreSQL schema/RPC and 12-check HTTP integration suites passed. Python API 13 tests, Worker API 17 tests, Python browser five tests and Worker browser five tests passed. Browser suites used installed system Chrome with otherwise unchanged test cases and disposable local databases. Actual 320/390/1280 legacy screenshots inspected: readable and no clipping.

The temporary publication workflow reruns the build, unchanged low-threshold npm audit and regression suites before committing these allowlisted sources, then deletes itself. Check that workflow's result and hosted deployment before calling the publication verified. Local tests alone are not a green hosted build.

Analytics is still a separate substantially AI-assisted synthetic SQLite demonstration. No customer data, personal secrets, paid service, resume change or new application is included in this maintenance.
