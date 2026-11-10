"""Start browser-test server with a unique, disposable database."""
import os, runpy, signal, tempfile
from pathlib import Path
def stop(*_):raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop)
with tempfile.TemporaryDirectory(prefix='roleproof-e2e-') as directory:
 os.environ['ROLEPROOF_DB']=str(Path(directory)/'test.sqlite3')
 runpy.run_path(str(Path(__file__).with_name('server.py')),run_name='__main__')
