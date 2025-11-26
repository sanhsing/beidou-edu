"""認證 API 路由"""
import sqlite3
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from utils import get_db, hash_password, verify_password, create_jwt, auth_required

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    db = get_db()
    pw_hash, salt = hash_password(password)
    
    try:
        db.execute("INSERT INTO users (username, email, password_hash, salt, display_name) VALUES (?, ?, ?, ?, ?)",
                   (username, email, pw_hash, salt, username))
        db.commit()
        logger.info(f"New user registered: {username}")
        return jsonify({'message': 'Registration successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 409

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username)).fetchone()
    
    if not user or not verify_password(password, user['password_hash'], user['salt']):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not user['is_active']:
        return jsonify({'error': 'Account is disabled'}), 403
    
    db.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), user['id']))
    db.commit()
    
    token = create_jwt({'user_id': user['id'], 'username': user['username'], 'role': user['role']})
    logger.info(f"User logged in: {username}")
    
    return jsonify({
        'token': token,
        'user': {'id': user['id'], 'username': user['username'], 'display_name': user['display_name'], 'role': user['role']}
    })

@bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    db = get_db()
    user = db.execute("SELECT id, username, email, display_name, role FROM users WHERE id = ?", (g.user_id,)).fetchone()
    return jsonify(dict(user))
