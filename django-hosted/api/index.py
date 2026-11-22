"""AI-assisted Django HTTP layer for the synthetic RoleProof desk.
Storage is a direct scoped PostgreSQL RPC, not Django ORM or a Flask/Node proxy.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import re_path
from django.core.wsgi import get_wsgi_application

ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'rp_django_session'
LOCAL = os.environ.get('ROLEPROOF_LOCAL') == '1'
SECURITY = {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
}
class SecurityMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        try:
            if request.method in {'POST', 'PATCH'} and len(request.body) > 8192:
                response = JsonResponse({'error': 'Request exceeds 8192 bytes.'}, status=413)
            else:
                response = self.get_response(request)
        except RequestDataTooBig:
            response = JsonResponse({'error': 'Request exceeds 8192 bytes.'}, status=413)
        for key, value in SECURITY.items(): response[key] = value
        return response

if not settings.configured:
    settings.configure(
        DEBUG=False, SECRET_KEY=secrets.token_hex(32), ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver', '.vercel.app'],
        INSTALLED_APPS=[], MIDDLEWARE=[__name__ + '.SecurityMiddleware'],
        DATA_UPLOAD_MAX_MEMORY_SIZE=8192, DEFAULT_CHARSET='utf-8',
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'), USE_TZ=True,
    )

def rpc(action, token_hash, payload):
    from api.storage_config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY
    base = os.environ.get('SUPABASE_URL', SUPABASE_URL)
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', SUPABASE_PUBLISHABLE_KEY)
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co', base) or not key:
        raise RuntimeError('Storage not configured')
    req = Request(base + '/rest/v1/rpc/roleproof_rpc',
                  data=json.dumps(dict(action=action, token_hash=token_hash, payload=payload)).encode(),
                  headers={'Content-Type': 'application/json', 'apikey': key}, method='POST')
    with urlopen(req, timeout=12) as response: result = json.load(response)
    if result.get('status') not in {200, 201, 400, 401, 404, 409, 429, 503} or not isinstance(result.get('body'), dict):
        raise RuntimeError('Invalid storage response')
    return result

def api_view(request, path):
    method = request.method
    if method not in {'GET', 'POST', 'PATCH'}:
        response = JsonResponse({'error': 'Method not allowed.'}, status=405)
        response['Allow'] = 'GET, POST, PATCH'
        return response
    payload = {}
    if method != 'GET':
        expected = ('http' if LOCAL else 'https') + '://' + request.get_host()
        if request.headers.get('Origin') != expected:
            return JsonResponse({'error': 'Same-origin requests only.'}, status=403)
        if request.headers.get('X-RoleProof-Client') != 'desk' or request.content_type != 'application/json':
            return JsonResponse({'error': 'JSON and client header required.'}, status=400)
        try: payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'JSON object required.'}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({'error': 'JSON object required.'}, status=400)
    action = None
    if path == 'health' and method == 'GET': action = 'health'
    elif path == 'session' and method == 'POST':
        if payload: return JsonResponse({'error': 'Empty session object required.'}, status=400)
        action = 'session'
    elif path in {'tickets', 'metrics', 'export.csv'} and method == 'GET': action = 'list'
    elif path == 'tickets' and method == 'POST': action = 'create'
    elif re.fullmatch(r'tickets/[1-9][0-9]{0,14}', path) and method == 'PATCH':
        if set(payload) != {'status', 'version'}:
            return JsonResponse({'error': 'Expected status and version.'}, status=400)
        action = 'update'; payload['id'] = int(path.split('/')[1])
    if action is None: return JsonResponse({'error': 'Route not found.'}, status=404)
    token = request.COOKIES.get(COOKIE, '')
    valid = re.fullmatch(r'[a-f0-9]{64}', token)
    if not valid and action not in {'session', 'health'}:
        return JsonResponse({'error': 'Demo session expired. Reload to start a fresh workspace.'}, status=401)
    if not valid: token = secrets.token_hex(32)
    try:
        result = rpc(action, hashlib.sha256(('django:' + token).encode()).hexdigest(), payload)
        body, status = result['body'], result['status']
        if status == 200 and action == 'health':
            body = {**body, 'runtime': 'Python Django', 'backend': 'direct scoped PostgreSQL RPC, not Django ORM'}
        if status == 200 and path in {'metrics', 'export.csv'}:
            tickets = body.get('tickets', [])
            if path == 'metrics':
                body = {'total': len(tickets), 'by_status': {s: sum(t['status'] == s for t in tickets) for s in ['Open', 'In progress', 'Resolved']}, 'runtime': 'Python Django'}
            else:
                stream = io.StringIO(newline=''); writer = csv.writer(stream)
                writer.writerow(['id', 'title', 'category', 'priority', 'status', 'version'])
                for ticket in tickets:
                    values = [ticket[k] for k in ['id', 'title', 'category', 'priority', 'status', 'version']]
                    writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in values])
                response = HttpResponse(stream.getvalue(), content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = 'attachment; filename="synthetic-requests.csv"'
                return response
        response = JsonResponse(body, status=status)
        if action == 'session' and status in {200, 201}:
            ttl = max(0, min(604800, body['expires_at'] - int(time.time())))
            response.set_cookie(COOKIE, token, max_age=ttl, httponly=True, secure=not LOCAL, samesite='Strict')
        return response
    except Exception:
        return JsonResponse({'error': 'Demo storage unavailable. Please try again later.'}, status=503)

def home(request):
    if request.method != 'GET': return JsonResponse({'error': 'Method not allowed.'}, status=405)
    return HttpResponse((ROOT / 'static' / 'index.html').read_text(), content_type='text/html; charset=utf-8')

def asset(request, filename):
    if request.method != 'GET' or not re.fullmatch(r'[A-Za-z0-9_.-]+\.(js|css)', filename):
        return JsonResponse({'error': 'Not found.'}, status=404)
    file = ROOT / 'static' / 'assets' / filename
    if not file.is_file(): return JsonResponse({'error': 'Not found.'}, status=404)
    return FileResponse(file.open('rb'), content_type='text/javascript' if filename.endswith('.js') else 'text/css')

urlpatterns = [re_path(r'^api/(?P<path>.+)$', api_view), re_path(r'^$', home), re_path(r'^assets/(?P<filename>[^/]+)$', asset)]
app = get_wsgi_application()

application = app
