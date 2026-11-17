"""Synthetic, AI-assisted SQL funnel proof. No real users, SDKs or tracking."""
import csv
import io
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Blueprint, jsonify, request, Response

analytics = Blueprint('analytics', __name__)
AS_OF = '2026-11-18T00:00:00Z'
SEGMENTS = ('all', 'starter', 'pro')
QUERY = """
WITH selected AS (
 SELECT user_id, plan, signed_up_at FROM users WHERE (? = 'all' OR plan = ?)
), prompt AS (
 SELECT user_id, MIN(occurred_at) AS at FROM events WHERE name='prompt' GROUP BY user_id
), built AS (
 SELECT e.user_id, MIN(e.occurred_at) AS at FROM events e
 JOIN prompt p ON e.user_id=p.user_id AND e.occurred_at>=p.at
 WHERE e.name='built' GROUP BY e.user_id
), published AS (
 SELECT e.user_id, MIN(e.occurred_at) AS at FROM events e
 JOIN built b ON e.user_id=b.user_id AND e.occurred_at>=b.at
 WHERE e.name='published' GROUP BY e.user_id
)
SELECT u.user_id,u.plan,u.signed_up_at,p.at AS prompted_at,b.at AS built_at,
 x.at AS published_at,
 CASE WHEN b.at IS NOT NULL AND julianday(b.at)-julianday(u.signed_up_at)<=2
 THEN 1 ELSE 0 END AS activated_48h,
 CASE WHEN julianday(?) - julianday(u.signed_up_at)>=8 THEN 1 ELSE 0 END AS d7_eligible,
 CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.user_id=u.user_id
 AND e.name IN ('prompt','built','published','return')
 AND julianday(e.occurred_at)-julianday(u.signed_up_at)>=7
 AND julianday(e.occurred_at)-julianday(u.signed_up_at)<8) THEN 1 ELSE 0 END AS d7_returned
FROM selected u LEFT JOIN prompt p ON u.user_id=p.user_id
LEFT JOIN built b ON u.user_id=b.user_id LEFT JOIN published x ON u.user_id=x.user_id
ORDER BY u.user_id
"""


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE users(user_id TEXT PRIMARY KEY,plan TEXT NOT NULL,signed_up_at TEXT NOT NULL);
    CREATE TABLE events(event_id INTEGER PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(user_id),name TEXT NOT NULL,occurred_at TEXT NOT NULL,credits INTEGER NOT NULL CHECK(credits>=0));''')
    db.execute('PRAGMA foreign_keys=ON')
    now = datetime(2026, 11, 18, tzinfo=timezone.utc)
    event_id = 0
    for i in range(1, 13):
        age = 14 if i <= 4 else 9 if i <= 8 else 3
        signup = now-timedelta(days=age)
        uid = 'u%02d' % i
        db.execute('INSERT INTO users VALUES(?,?,?)', (uid, 'starter' if i % 2 else 'pro', iso(signup)))
        timeline = []
        if i <= 10: timeline.append(('prompt', .1, 1))
        if i <= 7: timeline.append(('built', .5, 4))
        if i == 8: timeline.append(('built', 3, 4))  # built, but not within 48h
        if i <= 5: timeline.append(('published', 1, 2))
        if i == 11: timeline.append(('published', 1, 2))  # out-of-order noise, not funnel completion
        if i in (1, 2, 3, 5): timeline.append(('return', 7.5, 0))
        for name, day, credits in timeline:
            event_id += 1
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)', (event_id,uid,name,iso(signup+timedelta(days=day)),credits))
    db.commit()
    db.execute('PRAGMA query_only=ON')
    return db


def rate(n, d):
    return round(100*n/d, 1) if d else None


def compute(plan='all'):
    if plan not in SEGMENTS:
        raise ValueError('Unsupported segment')
    with database() as db:
        users = [dict(r) for r in db.execute(QUERY, (plan,plan,AS_OF))]
        names = ('prompted_at','built_at','published_at')
        funnel = [{'stage': n, 'users':sum(u[key] is not None for u in users)} for n,key in zip(('Prompted','Built','Published'),names)]
        previous = len(users)
        for row in funnel:
            row['conversion_from_previous_pct'] = rate(row['users'], previous)
            row['drop_off_users'] = previous-row['users']
            previous = row['users']
        eligible = sum(u['d7_eligible'] for u in users)
        retained = sum(u['d7_eligible'] and u['d7_returned'] for u in users)
        credit = db.execute('SELECT COALESCE(SUM(e.credits),0) FROM events e JOIN users u ON u.user_id=e.user_id WHERE (?=\'all\' OR u.plan=?)', (plan,plan)).fetchone()[0]
        cohorts = []
        for date in sorted(set(u['signed_up_at'][:10] for u in users)):
            group = [u for u in users if u['signed_up_at'][:10]==date]
            den = sum(u['d7_eligible'] for u in group)
            num = sum(u['d7_eligible'] and u['d7_returned'] for u in group)
            cohorts.append(dict(date=date,users=len(group),eligible=den,returned=num,retention_pct=rate(num,den)))
        activated = sum(u['activated_48h'] for u in users)
        return dict(as_of=AS_OF,synthetic=True,runtime='Python / SQLite',segment=plan,total_users=len(users),funnel=funnel,activated_48h=activated,activation_pct=rate(activated,len(users)),d7_eligible=eligible,d7_returned=retained,d7_retention_pct=rate(retained,eligible),credits=credit,cohorts=cohorts)


@analytics.get('/api/analytics')
def metrics():
    plan=request.args.get('segment','all')
    if set(request.args)-{'segment'} or plan not in SEGMENTS:
        return jsonify(error='Use segment all, starter or pro only.'),400
    return jsonify(compute(plan))


@analytics.get('/api/analytics/export.csv')
def export():
    plan=request.args.get('segment','all')
    if set(request.args)-{'segment'} or plan not in SEGMENTS:
        return jsonify(error='Use segment all, starter or pro only.'),400
    data=compute(plan)
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(['synthetic','segment','as_of','cohort','users','d7_eligible','d7_returned','d7_retention_pct'])
    for r in data['cohorts']:
        writer.writerow([True,plan,AS_OF,r['date'],r['users'],r['eligible'],r['returned'],r['retention_pct'] if r['retention_pct'] is not None else 'not mature'])
    return Response(stream.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="synthetic-cohorts.csv"'})


@analytics.get('/analytics')
def page():
    return Response(Path(__file__).with_name('analytics.html').read_text(),mimetype='text/html')


@analytics.get('/analytics.js')
def script():
    return Response(Path(__file__).with_name('analytics.js').read_text(),mimetype='text/javascript')


@analytics.get('/analytics.css')
def styles():
    return Response(Path(__file__).with_name('analytics.css').read_text(),mimetype='text/css')
