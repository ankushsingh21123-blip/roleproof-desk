#!/usr/bin/env python3
"""Loopback-only portfolio demo. No accounts, real data, external services or secrets."""
import json, os, sqlite3
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('ROLEPROOF_DB',str(ROOT/'roleproof.sqlite3')))
if not DB.is_absolute(): DB=ROOT/DB
PORT=int(os.environ.get('ROLEPROOF_PORT','8765'))
STATUSES={'Open','In progress','Resolved'}
CATEGORIES={'Account','Billing','Product','Other'}
PRIORITIES={'High','Medium','Low'}
def connect():
 c=sqlite3.connect(DB,timeout=5); c.row_factory=sqlite3.Row;return c

def now():return datetime.now(timezone.utc).isoformat()
def initialize():
 with connect() as c:
  c.execute('PRAGMA journal_mode=WAL')
  c.execute('CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,category TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)')
  if not c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]:
   examples=[('Unable to update workspace name','Fictional example: saving a new workspace name leaves the previous value visible.','Account','High','Open'),('Invoice download returns an empty file','Fictional example: the sample billing export downloads without any content.','Billing','High','In progress'),('Keyboard focus skips the save button','Fictional example: keyboard navigation jumps from the input to the footer.','Product','Medium','Open'),('Add CSV export for the activity list','Fictional example: export a filtered set of activity rows for offline review.','Product','Low','Open'),('Clarify the demo data notice','Fictional example: the notice now clearly labels all records as synthetic.','Other','Low','Resolved')]
   c.executemany('INSERT INTO tickets(title,description,category,priority,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',[(*e,now(),now()) for e in examples])
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'dist'),**kw)
 def log_message(self,*a):pass
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
  self.send_header('Cache-Control','no-store');super().end_headers()
 def reply(self,status,data):
  b=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def safe_host(self):
  host=self.headers.get('Host','');return host in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
 def gate(self):
  if not self.safe_host():self.reply(403,{'error':'Only the configured loopback host is allowed.'});return False
  if self.headers.get('Origin') not in {None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}:self.reply(403,{'error':'Cross-origin requests are not allowed.'});return False
  return True
 def body(self):
  if self.headers.get('X-RoleProof-Client')!='desk':raise ValueError('Missing client header.')
  if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON content type required.')
  try:n=int(self.headers.get('Content-Length','0'))
  except ValueError:raise ValueError('Invalid request size.')
  if not 0<n<=8192:raise ValueError('Request body must be between 1 and 8192 bytes.')
  try:v=json.loads(self.rfile.read(n))
  except (ValueError,UnicodeDecodeError):raise ValueError('Invalid JSON.')
  if not isinstance(v,dict):raise ValueError('JSON object required.')
  return v
 def do_GET(self):
  if not self.gate():return
  path=urlparse(self.path).path
  if path=='/api/health':self.reply(200,{'status':'ok','mode':'local-synthetic-demo'});return
  if path=='/api/tickets':
   with connect() as c:rows=[dict(r) for r in c.execute("SELECT * FROM tickets ORDER BY CASE status WHEN 'Resolved' THEN 1 ELSE 0 END, CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,id DESC")]
   self.reply(200,{'tickets':rows});return
  if path.startswith('/api/'):self.reply(404,{'error':'Route not found.'});return
  if path=='/' or path.startswith('/assets/') or path=='/index.html':super().do_GET()
  else:self.reply(404,{'error':'Not found.'})
 def do_POST(self):
  if not self.gate():return
  if urlparse(self.path).path!='/api/tickets':self.reply(404,{'error':'Route not found.'});return
  try:
   v=self.body()
   if set(v)!={'title','description','category','priority'}:raise ValueError('Expected title, description, category and priority only.')
   if not all(isinstance(x,str) for x in v.values()):raise ValueError('Fields must be strings.')
   title=v['title'].strip();description=v['description'].strip()
   if not 3<=len(title)<=120 or not 5<=len(description)<=2000:raise ValueError('Title must be 3-120 characters and description 5-2000.')
   if v['category'] not in CATEGORIES or v['priority'] not in PRIORITIES:raise ValueError('Invalid category or priority.')
   with connect() as c:
    cur=c.execute("INSERT INTO tickets(title,description,category,priority,status,created_at,updated_at) VALUES(?,?,?,?,'Open',?,?)",(title,description,v['category'],v['priority'],now(),now()))
    row=dict(c.execute('SELECT * FROM tickets WHERE id=?',(cur.lastrowid,)).fetchone())
   self.reply(201,{'ticket':row})
  except ValueError as e:self.reply(400,{'error':str(e)})
 def do_PATCH(self):
  if not self.gate():return
  path=urlparse(self.path).path
  try:
   parts=path.split('/')
   if len(parts)!=4 or parts[1:3]!=['api','tickets'] or not parts[3].isdigit():self.reply(404,{'error':'Route not found.'});return
   ticket_id=int(parts[3]);v=self.body()
   if set(v)!={'status','version'} or not isinstance(v['status'],str) or v['status'] not in STATUSES or type(v['version']) is not int or v['version']<1:raise ValueError('Valid status and positive integer version required.')
   with connect() as c:
    cur=c.execute('UPDATE tickets SET status=?,version=version+1,updated_at=? WHERE id=? AND version=?',(v['status'],now(),ticket_id,v['version']))
    row=c.execute('SELECT * FROM tickets WHERE id=?',(ticket_id,)).fetchone()
    if row is None:self.reply(404,{'error':'Ticket not found.'});return
    if cur.rowcount==0:self.reply(409,{'error':'This ticket changed. Refresh before updating.'});return
   self.reply(200,{'ticket':dict(row)})
  except ValueError as e:self.reply(400,{'error':str(e)})
 def unsupported(self):
  if self.gate():self.reply(405,{'error':'Method not allowed.'})
 do_OPTIONS=unsupported
 do_PUT=unsupported
 do_DELETE=unsupported
if __name__=='__main__':
 if not (ROOT/'dist'/'index.html').is_file():raise SystemExit('Build the frontend first: npm ci && npm run build')
 initialize(); server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler);server.daemon_threads=True
 print(f'RoleProof Desk local demo: http://127.0.0.1:{PORT}',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
