"""Integration tests against the actual local Workers/D1 runtime, not a mocked DB.
The runner owns and stops its local server. Never touches a remote deployment.
"""
import http.cookiejar,json,os,subprocess,time,unittest,tempfile,sys
from pathlib import Path
from urllib.request import Request,build_opener,HTTPCookieProcessor
from urllib.error import HTTPError
BASE=os.environ.get('WORKER_TEST_URL','http://127.0.0.1:8787')
ROOT=Path(__file__).resolve().parent
class Client:
 def __init__(self):self.jar=http.cookiejar.CookieJar();self.http=build_opener(HTTPCookieProcessor(self.jar))
 def request(self,path,method='GET',data=None,headers=None,raw=None):
  h={'Content-Type':'application/json','X-RoleProof-Client':'desk','Origin':BASE,**(headers or {})}
  payload=raw if raw is not None else(json.dumps(data).encode() if data is not None else None)
  try:r=self.http.open(Request(BASE+path,method=method,data=payload,headers=h),timeout=10)
  except HTTPError as e:r=e
  with r:
   b=r.read();return r.status,json.loads(b) if 'application/json' in r.headers.get('Content-Type','') else b,r.headers
 def start(self):return self.request('/api/session','POST',{})
 def create(self,**kwargs):return self.request('/api/tickets','POST',{'title':'Synthetic integration request','description':'Fictional verification only.','category':'Product','priority':'High',**kwargs})
class WorkersAPI(unittest.TestCase):
 def setUp(self):self.c=Client();self.assertIn(self.c.start()[0],[200,201])
 def test_health_reads_bound_database(self):
  s,v,_=self.c.request('/api/health');self.assertEqual(s,200);self.assertEqual(v['database'],'D1 SQLite')
 def test_seeded_list_and_cookie_flags(self):
  self.assertEqual(len(self.c.request('/api/tickets')[1]['tickets']),5)
  s,_,h=Client().start();self.assertEqual(s,201)
  self.assertIn('HttpOnly',h['Set-Cookie']);self.assertIn('SameSite=Strict',h['Set-Cookie']);self.assertIn('Max-Age=604800',h['Set-Cookie'])
 def test_session_reuse_is_idempotent(self):
  self.c.create();self.assertEqual(self.c.start()[0],200);self.assertEqual(len(self.c.request('/api/tickets')[1]['tickets']),6)
 def test_create_survives_new_http_client_with_same_cookie(self):
  s,t,_=self.c.create();self.assertEqual(s,201)
  other=Client();other.jar=self.c.jar;other.http=build_opener(HTTPCookieProcessor(other.jar))
  self.assertIn(t['ticket']['id'],[x['id'] for x in other.request('/api/tickets')[1]['tickets']])
 def test_sessions_cannot_read_or_modify_each_other(self):
  _,t,_=self.c.create();id=t['ticket']['id'];other=Client();other.start()
  self.assertNotIn(id,[x['id'] for x in other.request('/api/tickets')[1]['tickets']])
  self.assertEqual(other.request('/api/tickets/'+str(id),'PATCH',{'status':'Resolved','version':1})[0],404)
  self.assertNotIn('session_id',t['ticket'])
 def test_no_cookie_cannot_read_or_write(self):
  c=Client();self.assertEqual(c.request('/api/tickets')[0],401);self.assertEqual(c.create()[0],401)
 def test_forged_cookie_cannot_read_workspace(self):
  c=Client();self.assertEqual(c.request('/api/tickets',headers={'Cookie':'rp_session='+'a'*64})[0],401)
 def test_optimistic_concurrency(self):
  _,t,_=self.c.create();path='/api/tickets/'+str(t['ticket']['id'])
  self.assertEqual(self.c.request(path,'PATCH',{'status':'Resolved','version':1})[0],200)
  self.assertEqual(self.c.request(path,'PATCH',{'status':'Open','version':1})[0],409)
 def test_invalid_fields(self):
  for change in [{'title':'x'},{'description':'x'},{'title':None},{'priority':'Urgent'},{'category':'Secret'},{'extra':'x'}]:self.assertEqual(self.c.create(**change)[0],400)
 def test_invalid_patch(self):
  self.assertEqual(self.c.request('/api/tickets/1','PATCH',{'status':'Open','version':True})[0],400)
 def test_cross_origin_and_missing_origin_rejected(self):
  for origin in ['https://untrusted.invalid','null','']:
   self.assertEqual(self.c.request('/api/tickets','POST',{},headers={'Origin':origin})[0],403)
 def test_missing_client_header_and_content_type(self):
  self.assertEqual(self.c.request('/api/tickets','POST',{},headers={'X-RoleProof-Client':''})[0],400)
  self.assertEqual(self.c.request('/api/tickets','POST',{},headers={'Content-Type':'text/plain'})[0],400)
 def test_malformed_and_oversize(self):
  self.assertEqual(self.c.request('/api/tickets','POST',raw=b'{broken')[0],400)
  self.assertEqual(self.c.request('/api/tickets','POST',raw=b'x'*9000)[0],400)
 def test_database_metacharacters_are_data(self):
  s,t,_=self.c.create(title="Demo '; DROP TABLE tickets; --");self.assertEqual(s,201);self.assertIn('DROP TABLE',t['ticket']['title']);self.assertEqual(self.c.request('/api/tickets')[0],200)
 def test_unsupported_and_hidden_paths(self):
  for method in ['PUT','DELETE','OPTIONS']:self.assertEqual(self.c.request('/api/tickets',method,{})[0],405)
  for path in ['/.env','/schema.sql','/worker.mjs','/wrangler.jsonc','/api/unknown']:self.assertEqual(self.c.request(path)[0],404)
 def test_security_headers(self):
  for path in ['/','/api/tickets']:
   _,_,h=self.c.request(path);self.assertEqual(h['X-Content-Type-Options'],'nosniff');self.assertEqual(h['Cache-Control'],'no-store');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
 def test_rate_limit_is_bounded(self):
  statuses=[self.c.create()[0] for _ in range(21)];self.assertEqual(statuses[:20],[201]*20);self.assertEqual(statuses[20],429)
if __name__=='__main__':
 p=None;tmp=None;success=False
 try:
  if 'WORKER_TEST_URL' not in os.environ:
   tmp=tempfile.TemporaryDirectory(prefix='roleproof-worker-')
   subprocess.run(['npx','wrangler','d1','execute','roleproof-desk-demo','--local','--file','schema.sql','--persist-to',tmp.name],cwd=ROOT,check=True)
   log=open(ROOT/'worker-runtime.log','w')
   p=subprocess.Popen(['npx','wrangler','dev','--port','8787','--ip','127.0.0.1','--persist-to',tmp.name],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   for _ in range(120):
    try:
     if Client().request('/api/health')[0]==200:break
    except OSError:pass
    if p.poll() is not None:raise RuntimeError('Worker runtime failed; inspect worker-runtime.log')
    time.sleep(.25)
   else:raise RuntimeError('Worker did not become ready')
  success=unittest.main(verbosity=2,exit=False).result.wasSuccessful()
 finally:
  if p:
   import signal
   os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10);log.close()

  if tmp:tmp.cleanup()
 sys.exit(0 if success else 1)
