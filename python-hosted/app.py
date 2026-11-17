"""AI-assisted synthetic Python portfolio extension. No assessed answers or real data.
Direct Python -> scoped PostgreSQL RPC. Not a proxy through the Node demo.
"""
import csv
import hashlib
import io
import json
import os
import re
import secrets
import time
from urllib.request import Request, urlopen
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
from analytics import analytics
app.register_blueprint(analytics)
app.config['MAX_CONTENT_LENGTH'] = 8192
COOKIE = 'rp_python_session'
SECURITY = {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
}

@app.after_request
def security(response):
    response.headers.update(SECURITY)
    return response


def rpc(action, token_hash, payload):
    """Only a publishable key, never database credentials or service-role access."""
    base = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co', base) or not key:
        raise RuntimeError('Storage not configured')
    req = Request(base + '/rest/v1/rpc/roleproof_rpc',
                  data=json.dumps(dict(action=action, token_hash=token_hash, payload=payload)).encode(),
                  headers={'Content-Type': 'application/json', 'apikey': key}, method='POST')
    with urlopen(req, timeout=12) as response:
        result = json.load(response)
    if result.get('status') not in {200, 201, 400, 401, 404, 409, 429, 503} or not isinstance(result.get('body'), dict):
        raise RuntimeError('Invalid storage response')
    return result


@app.route('/api/<path:path>', methods=['GET', 'POST', 'PATCH', 'DELETE', 'PUT', 'OPTIONS'])
def api(path):
    method = request.method
    if method not in {'GET', 'POST', 'PATCH'}:
        return jsonify(error='Method not allowed.'), 405
    if method != 'GET':
        scheme = 'http' if app.config.get('TESTING') else 'https'
        if request.headers.get('Origin') != scheme + '://' + request.host:
            return jsonify(error='Same-origin requests only.'), 403
        if request.headers.get('X-RoleProof-Client') != 'desk' or request.mimetype != 'application/json':
            return jsonify(error='JSON and client header required.'), 400
    payload = {}
    if method != 'GET':
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error='JSON object required.'), 400
    action = None
    if path == 'health' and method == 'GET': action = 'health'
    elif path == 'session' and method == 'POST':
        if payload: return jsonify(error='Empty session object required.'), 400
        action = 'session'
    elif path in {'tickets', 'metrics', 'export.csv'} and method == 'GET': action = 'list'
    elif path == 'tickets' and method == 'POST': action = 'create'
    elif re.fullmatch(r'tickets/[1-9][0-9]{0,14}', path) and method == 'PATCH':
        if set(payload) != {'status', 'version'}:
            return jsonify(error='Expected status and version.'), 400
        action = 'update'
        payload['id'] = int(path.split('/')[1])
    if action is None: return jsonify(error='Route not found.'), 404
    token = request.cookies.get(COOKIE, '')
    valid = re.fullmatch(r'[a-f0-9]{64}', token)
    if not valid and action not in {'session', 'health'}:
        return jsonify(error='Demo session expired. Reload to start a fresh workspace.'), 401
    if not valid: token = secrets.token_hex(32)
    try:
        result = rpc(action, hashlib.sha256(token.encode()).hexdigest(), payload)
        body, status = result['body'], result['status']
        if status == 200 and action == 'health':
            body = {**body, 'runtime': 'Python Flask', 'backend': 'direct scoped PostgreSQL RPC'}
        if status == 200 and path in {'metrics', 'export.csv'}:
            tickets = body.get('tickets', [])
            if path == 'metrics':
                body = {'total': len(tickets), 'by_status': {s: sum(t['status'] == s for t in tickets) for s in ['Open', 'In progress', 'Resolved']}, 'runtime': 'Python Flask'}
            else:
                stream = io.StringIO(newline='')
                writer = csv.writer(stream)
                writer.writerow(['id', 'title', 'category', 'priority', 'status', 'version'])
                for ticket in tickets:
                    values = [ticket[k] for k in ['id', 'title', 'category', 'priority', 'status', 'version']]
                    # Spreadsheet formula injection protection for all user-controlled strings.
                    writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in values])
                response = make_response(stream.getvalue(), 200)
                response.headers.update({'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename="synthetic-requests.csv"'})
                return response
        response = make_response(jsonify(body), status)
        if action == 'session' and status in {200, 201}:
            ttl = max(0, min(604800, body['expires_at'] - int(time.time())))
            response.set_cookie(COOKIE, token, max_age=ttl, httponly=True, secure=not app.config.get('TESTING'), samesite='Strict')
        return response
    except Exception:
        return jsonify(error='Demo storage unavailable. Please try again later.'), 503


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.errorhandler(413)
def oversized(error):
    return jsonify(error='Request exceeds 8192 bytes.'), 413


@app.route('/assets/<path:filename>')
def assets(filename):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(js|css)', filename):
        return jsonify(error='Not found.'), 404
    return app.send_static_file('assets/' + filename)
