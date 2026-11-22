from wsgiref.simple_server import make_server
from api.index import app
print('RoleProof Django: http://127.0.0.1:8806', flush=True)
with make_server('127.0.0.1',8806,app) as server:server.serve_forever()
