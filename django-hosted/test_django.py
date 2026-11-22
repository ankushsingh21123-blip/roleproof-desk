"""Django HTTP + actual local PostgreSQL (PGlite) checks; not hosted acceptance."""
import csv
import io
import json
from pathlib import Path
import subprocess
import unittest
from urllib.request import Request, urlopen
from django.test import Client
from api import index as target

class DjangoPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = subprocess.Popen(['node', 'test_pg_bridge.mjs'], cwd=Path(__file__).resolve().parent, stdout=subprocess.PIPE, text=True)
        assert cls.bridge.stdout.readline().strip() == 'READY'
        cls.original = target.urlopen
        def transport(req, timeout=12):
            return urlopen(Request('http://127.0.0.1:8795', data=req.data, headers={'Content-Type':'application/json'}, method='POST'), timeout=timeout)
        target.urlopen = transport
    @classmethod
    def tearDownClass(cls):
        target.urlopen = cls.original
        cls.bridge.terminate(); cls.bridge.wait(timeout=10); cls.bridge.stdout.close()
    def setUp(self): self.client = Client()
    def api(self, path, method='GET', data=None, client=None, **headers):
        h={'HTTP_ORIGIN':'http://testserver', 'HTTP_X_ROLEPROOF_CLIENT':'desk', **headers}
        return (client or self.client).generic(method, '/api/'+path, data=json.dumps(data) if data is not None else '', content_type='application/json', **h)
    def session(self, client=None):
        r=self.api('session','POST',{},client=client);self.assertEqual(r.status_code,201);return r
    def test_health(self):
        r=self.api('health');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['database'],'Supabase PostgreSQL');self.assertEqual(r.json()['runtime'],'Python Django')
    def test_requires_session(self):
        self.assertEqual(self.api('tickets').status_code,401)
        self.assertEqual(self.api('metrics').status_code,401)
    def test_cookie(self):
        r=self.session(); cookie=r.cookies[target.COOKIE]
        self.assertTrue(cookie['httponly']);self.assertEqual(cookie['samesite'],'Strict');self.assertTrue(cookie['max-age'])
    def test_roundtrip_persistence_isolation_stale_metrics_csv(self):
        self.session()
        r=self.api('tickets','POST',dict(title='=SYNTHETIC()',description='Fictional local fixture only',category='Product',priority='High'))
        self.assertEqual(r.status_code,201);ticket=r.json()['ticket']
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Resolved',version=1)).status_code,200)
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Open',version=1)).status_code,409)
        rows=self.api('tickets').json()['tickets']
        self.assertEqual(next(t for t in rows if t['id']==ticket['id'])['status'],'Resolved')
        self.assertEqual(self.api('metrics').json()['total'],6)
        self.assertEqual(self.api('metrics').json()['by_status']['Resolved'],2)
        exported=self.api('export.csv');self.assertEqual(exported.status_code,200)
        rows=list(csv.DictReader(io.StringIO(exported.content.decode())))
        self.assertEqual(next(t for t in rows if int(t['id'])==ticket['id'])['title'],"'=SYNTHETIC()")
        other=Client();self.session(other)
        self.assertEqual(self.api('tickets/'+str(ticket['id']),'PATCH',dict(status='Open',version=2),client=other).status_code,404)
        self.assertFalse(any(t['id']==ticket['id'] for t in self.api('tickets',client=other).json()['tickets']))
    def test_csrf(self):
        self.assertEqual(self.api('session','POST',{},HTTP_ORIGIN='https://evil.invalid').status_code,403)
    def test_client_header(self):
        self.assertEqual(self.api('session','POST',{},HTTP_X_ROLEPROOF_CLIENT='').status_code,400)
    def test_json_shapes(self):
        self.assertEqual(self.api('session','POST',[]).status_code,400)
        self.assertEqual(self.api('session','POST',{'unknown':1}).status_code,400)
        self.assertEqual(self.client.post('/api/session',data='{broken',content_type='application/json',HTTP_ORIGIN='http://testserver',HTTP_X_ROLEPROOF_CLIENT='desk').status_code,400)
    def test_bad_record(self):
        self.session()
        self.assertEqual(self.api('tickets','POST',{'title':'no'}).status_code,400)
        self.assertEqual(self.api('tickets/1','PATCH',{'status':'Open','version':True}).status_code,400)
    def test_oversize(self):
        self.assertEqual(self.api('tickets','POST',{'description':'x'*9000}).status_code,413)
    def test_routes(self):
        self.assertEqual(self.api('unknown').status_code,404)
        self.assertEqual(self.api('tickets','DELETE').status_code,405)
        self.assertEqual(self.client.get('/.env').status_code,404)
        self.assertEqual(self.client.get('/assets/../../api/index.py').status_code,404)
    def test_home_security_assets(self):
        r=self.client.get('/');self.assertEqual(r.status_code,200)
        self.assertIn('RoleProof Django',r.content.decode());self.assertEqual(r['X-Frame-Options'],'DENY')
        self.assertIn("frame-ancestors 'none'",r['Content-Security-Policy'])
        for path in (target.ROOT/'static/assets').glob('*'):
            asset=self.client.get('/assets/'+path.name);self.assertEqual(asset.status_code,200);asset.close()
    def test_error_redaction(self):
        original=target.urlopen
        try:
            def unavailable(*a,**k):raise RuntimeError('private exception secret')
            target.urlopen=unavailable;r=self.api('health');self.assertEqual(r.status_code,503)
            self.assertNotIn('secret',r.content.decode())
        finally:target.urlopen=original
    def test_production_cookie(self):
        old=target.LOCAL;target.LOCAL=False
        try:
            r=self.api('session','POST',{},HTTP_ORIGIN='https://testserver')
            self.assertEqual(r.status_code,201);self.assertTrue(r.cookies[target.COOKIE]['secure'])
        finally:target.LOCAL=old
    def test_unexpected_update_field(self):
        self.session();self.assertEqual(self.api('tickets/1','PATCH',{'status':'Open','version':1,'title':'wrong'}).status_code,400)
    def test_rejects_foreign_origin_even_with_valid_session(self):
        self.session();self.assertEqual(self.api('tickets','POST',{},HTTP_ORIGIN='https://evil.invalid').status_code,403)

if __name__=='__main__':unittest.main(verbosity=2)
