# SQL product-funnel proof (AI-assisted)

An additive learning/portfolio extension inspired by common product-analyst tasks, including Kraftapp AI's public November 2026 listing. This is not an employer assessment or application. Substantial AI assistance was used for design, implementation, debugging and tests. It does not establish unaided user authorship, Google Analytics experience, Excel expertise, or selection readiness.

## Scope

- Python Flask serves `/analytics`, JSON at `/api/analytics?segment=all|starter|pro`, and cohort CSV at `/api/analytics/export.csv`.
- Standard-library SQLite computes metrics from a deterministic synthetic seed, rebuilt read-only on each request. No real user data, persistent analytics ingestion, API charge, new dependency, or new hosted service.
- Existing PostgreSQL ticket-demo routes are retained. SQLite analytics is explicitly separate from that persistent database.
- Twelve fictional signups, three cohorts, and event sequences include a late build and an out-of-order publish to test denominator and sequencing errors.
- SQL lives as the `QUERY` constant in `analytics.py`, using CTEs, joins, first-event aggregation, correlated existence checks and parameter binding. No arbitrary SQL execution endpoint.

## Metric contract

1. Signup -> first prompt -> first build at/after prompt -> first publish at/after build. Counts are unique users, not event volume.
2. Activation: ordered build within 48 hours of signup, divided by all signups in the chosen segment.
3. Day-7 retention: an activity in [7,8) days after signup. A user enters the denominator only after the full eight-day observation window. Immature cohorts show null, never 0%.
4. Credits are synthetic units summed across events, including an invalid funnel publish. They are not revenue or real API spend.
5. Snapshot: 2026-11-18 00:00 UTC. This is not a moving live dashboard.

Expected whole dataset: 12 signups, 10 prompts, 8 ordered builds, 5 ordered publishes, 7 activated (58.3%), 4/8 mature users retained (50%), 54 credit units. Cohort retention: 3/4, 1/4, and not mature. Plan retention: starter 3/4, pro 1/4. No causal conclusion about which plan is better can be drawn from this fictional sample.

## Tests and boundaries

`python test_analytics.py`: 12 checks for expected metrics, late activation, mature denominator, credit total, segment partition, invalid event order, duplicate events, day-7 boundaries, headers, input rejection, CSV scope and read-only storage. Initial local run 18 Nov: passed.

Local browser check: 12 flows across 320/390/1280 widths for actual values, segment switching, CSV download and rapid-switch stale-response handling. No overflow or page errors. All three full-page renders inspected. Hosted verification is recorded separately after deployment; local passes are not claimed as hosted evidence.

Security: segment allowlist and parameter binding; same-origin static assets, inherited CSP/no-store/security headers; textContent for dynamic labels; no uploads, tracking SDK, arbitrary query or secrets. This bounded demo does not implement persistent analytics, production authentication, experiment assignment, causal inference, advanced statistics, GA4, or a spreadsheet integration.

## Explain before using as skill evidence

Trace why an out-of-order publish is excluded; explain why the immature cohort is not 0%; calculate the stage-specific conversion denominators; explain why the starter/pro difference is not a valid causal experiment. The user needs to understand and explain these choices personally. No resume upgrade or automatic above-100-applicant exception follows from publishing this demo.
