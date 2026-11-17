"""Local PostgreSQL fixture, never a production entrypoint."""
import os
import subprocess
import atexit
import signal
import sys
from urllib.request import Request, urlopen
from app import app
import app as module
bridge=subprocess.Popen(['node','test_pg_bridge.mjs'],stdout=subprocess.PIPE,text=True)
assert bridge.stdout.readline().strip()=='READY'
def finish():
 bridge.terminate();bridge.wait(timeout=10);bridge.stdout.close()
atexit.register(finish)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
def transport(req, timeout=12):
 return urlopen(Request('http://127.0.0.1:8795',data=req.data,headers={'Content-Type':'application/json'},method='POST'),timeout=timeout)
module.urlopen=transport
os.environ.update(SUPABASE_URL='https://localtest.supabase.co',SUPABASE_PUBLISHABLE_KEY='public-test-key')
app.config['TESTING']=True
app.run(host='127.0.0.1',port=8796)
