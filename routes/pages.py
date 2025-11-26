"""頁面路由"""
from flask import Blueprint, send_from_directory

bp = Blueprint('pages', __name__)

@bp.route('/')
def index():
    return send_from_directory('static', 'index.html')

@bp.route('/concepts')
def concepts_page():
    return send_from_directory('static', 'concepts.html')

@bp.route('/questions')
def questions_page():
    return send_from_directory('static', 'questions.html')

@bp.route('/dashboard')
def dashboard_page():
    return send_from_directory('static', 'dashboard.html')

@bp.route('/mindmap')
def mindmap_page():
    return send_from_directory('static', 'mindmap.html')
