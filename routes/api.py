"""資料 API 路由"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from utils import get_db, auth_required

bp = Blueprint('api', __name__, url_prefix='/api')

# ===== 系統 =====
@bp.route('/health', methods=['GET'])
def health_check():
    db = get_db()
    try:
        db.execute("SELECT 1").fetchone()
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    except:
        return jsonify({'status': 'unhealthy'}), 500

@bp.route('/system/stats', methods=['GET'])
def system_stats():
    db = get_db()
    stats = {
        'concepts': db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
        'questions': db.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
        'links': db.execute("SELECT COUNT(*) FROM concept_links").fetchone()[0],
        'users': db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'subjects': db.execute("SELECT COUNT(*) FROM subjects").fetchone()[0],
    }
    by_level = db.execute("SELECT education_level, COUNT(*) as count FROM concepts GROUP BY education_level").fetchall()
    stats['by_level'] = {row['education_level']: row['count'] for row in by_level}
    return jsonify(stats)

# ===== 概念 =====
@bp.route('/concepts', methods=['GET'])
def get_concepts():
    level = request.args.get('level')
    grade = request.args.get('grade')
    subject = request.args.get('subject')
    
    db = get_db()
    query = "SELECT * FROM concepts WHERE 1=1"
    params = []
    if level:
        query += " AND education_level = ?"
        params.append(level)
    if grade:
        query += " AND grade = ?"
        params.append(int(grade))
    if subject:
        query += " AND subject_code = ?"
        params.append(subject)
    
    concepts = db.execute(query + " ORDER BY education_level, grade, subject_code", params).fetchall()
    return jsonify([dict(c) for c in concepts])

@bp.route('/concept/<int:id>', methods=['GET'])
def get_concept(id):
    db = get_db()
    concept = db.execute("SELECT * FROM concepts WHERE id = ?", (id,)).fetchone()
    if not concept:
        return jsonify({'error': 'Concept not found'}), 404
    return jsonify(dict(concept))

@bp.route('/concept/<int:id>/relations', methods=['GET'])
def get_concept_relations(id):
    db = get_db()
    prereqs = db.execute("SELECT c.*, cl.strength FROM concept_links cl JOIN concepts c ON cl.source_id = c.id WHERE cl.target_id = ?", (id,)).fetchall()
    derived = db.execute("SELECT c.*, cl.strength FROM concept_links cl JOIN concepts c ON cl.target_id = c.id WHERE cl.source_id = ?", (id,)).fetchall()
    return jsonify({'prerequisites': [dict(p) for p in prereqs], 'derived': [dict(d) for d in derived]})

# ===== 心智圖資料 =====
@bp.route('/mindmap/<subject>', methods=['GET'])
def get_mindmap_data(subject):
    db = get_db()
    concepts = db.execute("""
        SELECT id, title, education_level, grade, subject_code 
        FROM concepts WHERE subject_code = ? 
        ORDER BY education_level, grade
    """, (subject,)).fetchall()
    
    links = db.execute("""
        SELECT cl.source_id, cl.target_id, cl.strength
        FROM concept_links cl
        JOIN concepts c1 ON cl.source_id = c1.id
        JOIN concepts c2 ON cl.target_id = c2.id
        WHERE c1.subject_code = ? OR c2.subject_code = ?
    """, (subject, subject)).fetchall()
    
    return jsonify({
        'nodes': [dict(c) for c in concepts],
        'links': [dict(l) for l in links]
    })

# ===== 題目 =====
@bp.route('/questions', methods=['GET'])
def get_questions():
    concept_id = request.args.get('concept_id')
    limit = request.args.get('limit', 10, type=int)
    db = get_db()
    if concept_id:
        questions = db.execute("SELECT * FROM questions WHERE concept_id = ? AND is_active = 1 LIMIT ?", (concept_id, limit)).fetchall()
    else:
        questions = db.execute("SELECT * FROM questions WHERE is_active = 1 ORDER BY RANDOM() LIMIT ?", (limit,)).fetchall()
    return jsonify([dict(q) for q in questions])

# ===== 測驗 =====
@bp.route('/quiz/generate', methods=['POST'])
@auth_required
def generate_quiz():
    data = request.get_json() or {}
    subject = data.get('subject')
    count = min(data.get('count', 10), 50)
    
    db = get_db()
    query = 'SELECT q.*, c.subject_code FROM questions q LEFT JOIN concepts c ON q.concept_id = c.id'
    params, conditions = [], ['q.is_active = 1']
    if subject:
        conditions.append('c.subject_code = ?')
        params.append(subject)
    query += ' WHERE ' + ' AND '.join(conditions) + ' ORDER BY RANDOM() LIMIT ?'
    params.append(count)
    
    rows = db.execute(query, params).fetchall()
    session_id = str(uuid.uuid4())[:8]
    questions = [{'id': r['id'], 'content': r['content'], 'options': r['options'], 'difficulty': r['difficulty'], 'type': r['question_type']} for r in rows]
    return jsonify({'session_id': session_id, 'count': len(questions), 'questions': questions})

@bp.route('/quiz/submit', methods=['POST'])
@auth_required
def submit_quiz():
    data = request.get_json() or {}
    answers = data.get('answers', [])
    session_id = data.get('session_id')
    if not answers:
        return jsonify({'error': 'No answers provided'}), 400
    
    db = get_db()
    results, correct = [], 0
    for ans in answers:
        q_id, user_answer = ans.get('question_id'), ans.get('answer')
        row = db.execute('SELECT answer FROM questions WHERE id = ?', (q_id,)).fetchone()
        if row:
            is_correct = str(user_answer) == str(row['answer'])
            if is_correct:
                correct += 1
            results.append({'question_id': q_id, 'correct': is_correct, 'correct_answer': row['answer']})
    
    return jsonify({'session_id': session_id, 'total': len(answers), 'correct': correct, 'score': round(100 * correct / len(answers), 1) if answers else 0, 'results': results})

# ===== 學習進度 =====
@bp.route('/progress', methods=['GET'])
@auth_required
def get_progress():
    db = get_db()
    progress = db.execute("""
        SELECT lp.*, c.title, c.subject_code, c.education_level
        FROM learning_progress lp JOIN concepts c ON lp.concept_id = c.id
        WHERE lp.user_id = ? ORDER BY lp.updated_at DESC
    """, (g.user_id,)).fetchall()
    return jsonify([dict(p) for p in progress])

@bp.route('/progress/<int:concept_id>', methods=['POST'])
@auth_required
def update_progress(concept_id):
    data = request.get_json()
    status = data.get('status', 'in_progress')
    mastery = data.get('mastery_level', 0)
    
    db = get_db()
    db.execute("""
        INSERT INTO learning_progress (user_id, concept_id, status, mastery_level, last_studied, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, concept_id) DO UPDATE SET
            status = excluded.status, mastery_level = excluded.mastery_level,
            last_studied = excluded.last_studied, updated_at = excluded.updated_at
    """, (g.user_id, concept_id, status, mastery, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({'message': 'Progress updated'})

# ===== 科目 =====
@bp.route('/subjects', methods=['GET'])
def get_subjects():
    db = get_db()
    subjects = db.execute('''
        SELECT s.*, (SELECT COUNT(*) FROM concepts c WHERE c.subject_code = s.code) as concept_count
        FROM subjects s WHERE s.is_active = 1 ORDER BY s.id
    ''').fetchall()
    return jsonify([{'id': s['id'], 'code': s['code'], 'name': s['name'], 'concept_count': s['concept_count']} for s in subjects])
