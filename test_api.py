import importlib.util,json,os,socket,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parent
class API(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();s=socket.socket();s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1];s.close()
  env={**os.environ,'ROLEPROOF_PORT':str(cls.port),'ROLEPROOF_DB':str(Path(cls.tmp.name)/'test.sqlite3')}
  cls.process=subprocess.Popen([sys.executable,str(ROOT/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   try:
    with urlopen(f'http://127.0.0.1:{cls.port}/api/health',timeout=.3):break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('Server did not start')
 @classmethod
 def tearDownClass(cls):cls.process.terminate();cls.process.wait(timeout=5);cls.tmp.cleanup()
 def req(self,path,method='GET',data=None,extra=None,raw=None):
  headers={'Content-Type':'application/json','X-RoleProof-Client':'desk',**(extra or {})};body=raw if raw is not None else(json.dumps(data).encode() if data is not None else None)
  request=Request(f'http://127.0.0.1:{self.port}'+path,data=body,method=method,headers=headers)
  try:r=urlopen(request,timeout=3)
  except HTTPError as e:r=e
  with r:return r.status,r.read(),r.headers
 def create(self,**overrides):
  data={'title':'Synthetic API request','description':'Fictional automated verification.','category':'Product','priority':'High',**overrides}
  status,b,_=self.req('/api/tickets','POST',data);self.assertEqual(status,201);return json.loads(b)['ticket']
 def test_health(self):self.assertEqual(self.req('/api/health')[0],200)
 def test_seeded_list(self):self.assertGreaterEqual(len(json.loads(self.req('/api/tickets')[1])['tickets']),5)
 def test_create_persistence(self):
  t=self.create();ids=[x['id'] for x in json.loads(self.req('/api/tickets')[1])['tickets']];self.assertIn(t['id'],ids)
 def test_status_and_stale_write(self):
  t=self.create();data={'status':'Resolved','version':t['version']};self.assertEqual(self.req('/api/tickets/'+str(t['id']),'PATCH',data)[0],200);self.assertEqual(self.req('/api/tickets/'+str(t['id']),'PATCH',data)[0],409)
 def test_invalid_fields(self):
  for changes in [{'title':'x'},{'description':'x'},{'priority':'Urgent'},{'category':'Private'},{'extra':'x'},{'title':None}]:
   d={'title':'Valid sample','description':'Fictional content only','category':'Product','priority':'Low',**changes};self.assertEqual(self.req('/api/tickets','POST',d)[0],400)
 def test_invalid_patch(self):self.assertEqual(self.req('/api/tickets/1','PATCH',{'status':'Open','version':True})[0],400)
 def test_missing_ticket(self):self.assertEqual(self.req('/api/tickets/999999','PATCH',{'status':'Open','version':1})[0],404)
 def test_origin_and_host_rejection(self):
  self.assertEqual(self.req('/api/tickets','POST',{},extra={'Origin':'https://untrusted.invalid'})[0],403);self.assertEqual(self.req('/api/health',extra={'Host':'untrusted.invalid'})[0],403)
 def test_missing_client_header(self):self.assertEqual(self.req('/api/tickets','POST',{},extra={'X-RoleProof-Client':''})[0],400)
 def test_malformed_and_oversized(self):
  self.assertEqual(self.req('/api/tickets','POST',raw=b'{broken')[0],400);self.assertEqual(self.req('/api/tickets','POST',raw=b'x'*9000)[0],400)
 def test_sql_metacharacters_are_data(self):
  t=self.create(title="Sample '; DROP TABLE tickets; --");self.assertIn('DROP TABLE',t['title']);self.assertEqual(self.req('/api/tickets')[0],200)
 def test_unsupported_methods_are_json(self):
  for method in ['PUT','DELETE','OPTIONS']:
   status,b,h=self.req('/api/tickets',method,{});self.assertEqual(status,405);self.assertIn('application/json',h['Content-Type']);self.assertEqual(json.loads(b)['error'],'Method not allowed.')
 def test_security_headers_and_no_secret_paths(self):
  _,_,h=self.req('/');self.assertEqual(h['X-Content-Type-Options'],'nosniff');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
  for p in ['/.env','/server.py','/roleproof.sqlite3','/../server.py','/api/unknown']:self.assertEqual(self.req(p)[0],404)
if __name__=='__main__':unittest.main(verbosity=2)
