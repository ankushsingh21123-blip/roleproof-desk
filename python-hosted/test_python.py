"""Python API -> real local PostgreSQL(PGlite), no hosted result implied."""
import csv
import io
import json
import os
import subprocess
import unittest
from urllib.request import Request, urlopen
import app as target


class PythonPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = subprocess.Popen(['node', 'test_pg_bridge.mjs'], stdout=subprocess.PIPE, text=True)
        assert cls.bridge.stdout.readline().strip() == 'READY'
        cls.original_urlopen = target.urlopen
        def local_transport(req, timeout=12):
            return urlopen(Request('http://127.0.0.1:8795', data=req.data,
                                  headers={'Content-Type': 'application/json'}, method='POST'), timeout=timeout)
        target.urlopen = local_transport
        os.environ.update(SUPABASE_URL='https://localtest.supabase.co', SUPABASE_PUBLISHABLE_KEY='public-test-key')
        target.app.config['TESTING'] = True
    @classmethod
    def tearDownClass(cls):
        target.urlopen = cls.original_urlopen
        cls.bridge.terminate()
        cls.bridge.wait(timeout=10)
        cls.bridge.stdout.close()
    def setUp(self):
        self.client = target.app.test_client()
    def api(self, path, method='GET', data=None, client=None, **headers):
        h={'Origin':'http://localhost', 'X-RoleProof-Client':'desk', **headers}
        return (client or self.client).open('/api/'+path,method=method,json=data,headers=h)
    def session(self):
        r=self.api('session','POST',{})
        self.assertEqual(r.status_code,201)
        return r
    def test_health_actual_database(self):
        r=self.api('health');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['database'],'Supabase PostgreSQL')
        self.assertEqual(r.json['runtime'],'Python Flask')
    def test_auth_required(self):
        self.assertEqual(self.api('tickets').status_code,401)
        self.assertEqual(self.api('metrics').status_code,401)
    def test_cookie(self):
        cookie=self.session().headers['Set-Cookie']
        self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        self.assertIn('Max-Age=',cookie)
    def test_roundtrip_isolation_stale_metrics_csv(self):
        self.session()
        r=self.api('tickets','POST',dict(title='=SYNTHETIC()',description='Fictional local fixture only',category='Product',priority='High'))
        self.assertEqual(r.status_code,201);ticket=r.json['ticket']
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Resolved',version=1)).status_code,200)
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Open',version=1)).status_code,409)
        rows=self.api('tickets').json['tickets']
        self.assertEqual(next(t for t in rows if t['id']==ticket['id'])['status'],'Resolved')
        self.assertEqual(self.api('metrics').json['total'],6)
        self.assertEqual(self.api('metrics').json['by_status']['Resolved'],2)
        exported=self.api('export.csv');self.assertEqual(exported.status_code,200)
        rows=list(csv.DictReader(io.StringIO(exported.text)))
        self.assertEqual(next(t for t in rows if int(t['id'])==ticket['id'])['title'],"'=SYNTHETIC()")
        other=target.app.test_client()
        self.assertEqual(self.api('session','POST',{},client=other).status_code,201)
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Open',version=2),client=other).status_code,404)
        self.assertFalse(any(t['id']==ticket['id'] for t in self.api('tickets',client=other).json['tickets']))
    def test_csrf(self):
        self.assertEqual(self.api('session','POST',{},Origin='https://evil.invalid').status_code,403)
    def test_missing_client(self):
        self.assertEqual(self.api('session','POST',{},**{'X-RoleProof-Client':''}).status_code,400)
    def test_invalid_json(self):
        self.assertEqual(self.api('session','POST',[]).status_code,400)
        self.assertEqual(self.api('session','POST',{'unknown':1}).status_code,400)
    def test_bad_record(self):
        self.session()
        self.assertEqual(self.api('tickets','POST',{'title':'no'}).status_code,400)
        self.assertEqual(self.api('tickets/1','PATCH',{'status':'Open','version':True}).status_code,400)
    def test_oversize(self):
        self.session()
        self.assertEqual(self.api('tickets','POST',{'description':'x'*9000}).status_code,413)
    def test_routes(self):
        self.assertEqual(self.api('unknown').status_code,404)
        self.assertEqual(self.api('tickets','DELETE').status_code,405)
        self.assertEqual(self.client.get('/.env').status_code,404)
        self.assertEqual(self.client.get('/assets/../../app.py').status_code,404)
    def test_static_security(self):
        r=self.client.get('/');self.assertEqual(r.status_code,200)
        self.assertIn('RoleProof Python',r.text)
        self.assertEqual(r.headers['X-Frame-Options'],'DENY')
        self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy']);r.close()
    def test_backend_error_redacted(self):
        original=target.urlopen
        try:
            def unavailable(*a,**k): raise RuntimeError('private exception secret')
            target.urlopen=unavailable
            r=self.api('health');self.assertEqual(r.status_code,503)
            self.assertNotIn('secret',r.text)
        finally: target.urlopen=original
    def test_secure_production_cookie(self):
        target.app.config['TESTING']=False
        try:
            r=self.client.post('/api/session',json={},headers={'Origin':'https://localhost','X-RoleProof-Client':'desk'})
            self.assertEqual(r.status_code,201);self.assertIn('Secure;',r.headers['Set-Cookie'])
        finally: target.app.config['TESTING']=True

if __name__=='__main__': unittest.main(verbosity=2)
