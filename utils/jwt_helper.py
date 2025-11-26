"""JWT 和密碼工具"""
import base64
import hmac
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app

# ===== 密碼 =====
def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hash_obj.hex(), salt

def verify_password(password, hash_value, salt):
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == hash_value

# ===== JWT =====
def create_jwt(payload):
    secret = current_app.config['SECRET_KEY']
    hours = current_app.config['JWT_EXPIRATION_HOURS']
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload['exp'] = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    payload_enc = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = hmac.new(secret.encode(), f"{header}.{payload_enc}".encode(), hashlib.sha256).hexdigest()
    return f"{header}.{payload_enc}.{signature}"

def verify_jwt(token):
    try:
        secret = current_app.config['SECRET_KEY']
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header, payload_enc, signature = parts
        expected_sig = hmac.new(secret.encode(), f"{header}.{payload_enc}".encode(), hashlib.sha256).hexdigest()
        if signature != expected_sig:
            return None
        payload_enc += '=' * (4 - len(payload_enc) % 4) if len(payload_enc) % 4 else ''
        payload = json.loads(base64.urlsafe_b64decode(payload_enc))
        if datetime.fromisoformat(payload['exp']) < datetime.utcnow():
            return None
        return payload
    except:
        return None

# ===== 裝飾器 =====
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        token = auth_header.split(' ')[1]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        g.user_id = payload['user_id']
        g.user_role = payload.get('role', 'student')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @auth_required
    def decorated(*args, **kwargs):
        if g.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated
