import csv
import io
import json
import unittest
from analytics import AS_OF, QUERY, compute, database
from app import app

class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING']=True
        self.client=app.test_client()
    def test_expected_full_funnel(self):
        d=compute()
        self.assertEqual([r['users'] for r in d['funnel']],[10,8,5])
        self.assertEqual([r['drop_off_users'] for r in d['funnel']],[2,2,3])
        self.assertEqual([r['conversion_from_previous_pct'] for r in d['funnel']],[83.3,80.0,62.5])
    def test_activation_excludes_late_build(self):
        d=compute();self.assertEqual((d['activated_48h'],d['activation_pct']),(7,58.3))
    def test_retention_denominator(self):
        d=compute();self.assertEqual((d['d7_eligible'],d['d7_returned'],d['d7_retention_pct']),(8,4,50.0))
        self.assertIsNone(d['cohorts'][-1]['retention_pct'])
    def test_credit_total(self):
        # 10 prompt + 8*4 build + 6*2 publish, including the invalid funnel publish.
        self.assertEqual(compute()['credits'],54)
    def test_segments_partition(self):
        a,b,c=compute(),compute('starter'),compute('pro')
        for k in ['total_users','activated_48h','d7_eligible','d7_returned','credits']:
            self.assertEqual(a[k],b[k]+c[k])
        self.assertEqual(b['d7_retention_pct'],75.0);self.assertEqual(c['d7_retention_pct'],25.0)
    def test_out_of_order_publish_excluded(self):
        db=database();r={r['user_id']:dict(r) for r in db.execute(QUERY,('all','all',AS_OF))};db.close()
        self.assertIsNone(r['u11']['published_at'])
    def test_repeat_events_do_not_inflate(self):
        db=database();db.execute('PRAGMA query_only=OFF');db.execute("INSERT INTO events VALUES(999,'u01','prompt','2026-11-05T00:00:00Z',0)")
        r=list(db.execute(QUERY,('all','all',AS_OF)));db.close()
        self.assertEqual(len(r),12);self.assertEqual(sum(x['prompted_at']is not None for x in r),10)
    def test_day7_boundary(self):
        db=database();db.execute('PRAGMA query_only=OFF');db.execute("DELETE FROM events WHERE name='return'")
        db.execute("INSERT INTO events VALUES(999,'u01','return','2026-11-11T00:00:00Z',0)")
        db.execute("INSERT INTO events VALUES(1000,'u02','return','2026-11-12T00:00:00Z',0)")
        r={r['user_id']:dict(r) for r in db.execute(QUERY,('all','all',AS_OF))};db.close()
        self.assertEqual(r['u01']['d7_returned'],1);self.assertEqual(r['u02']['d7_returned'],0)
    def test_endpoint_headers(self):
        r=self.client.get('/api/analytics');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['synthetic'],True);self.assertEqual(r.headers['Cache-Control'],'no-store')
        self.assertIn("default-src 'self'",r.headers['Content-Security-Policy'])
    def test_invalid_segment_and_injection(self):
        for q in ["' OR 1=1 --",'<script>','premium']:
            self.assertEqual(self.client.get('/api/analytics',query_string={'segment':q}).status_code,400)
        self.assertEqual(self.client.get('/api/analytics?sql=SELECT').status_code,400)
    def test_csv_scope(self):
        r=self.client.get('/api/analytics/export.csv?segment=pro');self.assertEqual(r.status_code,200)
        rows=list(csv.DictReader(io.StringIO(r.text)));self.assertEqual(len(rows),3)
        self.assertEqual(sum(int(r['users']) for r in rows),6)
        self.assertTrue(all(r['segment']=='pro' and r['synthetic']=='True' for r in rows))
    def test_readonly_and_static_routes(self):
        db=database()
        with self.assertRaises(Exception):db.execute("DELETE FROM events")
        db.close()
        for path in ['/analytics','/analytics.js','/analytics.css']:
            self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.post('/api/analytics').status_code,403) # existing same-origin protection

if __name__=='__main__':unittest.main(verbosity=2)
