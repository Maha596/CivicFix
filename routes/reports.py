import os
import uuid
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename

from database.db import execute_query
from services.ai_classifier import classify_civic_image
from services.notification import get_unread_count
from config import Config

reports_api_bp = Blueprint('reports_api', __name__, url_prefix='/api')

@reports_api_bp.route('/classify-image', methods=['POST'])
def api_classify_image():
    """
    Asynchronous AJAX image classification endpoint.
    Called when a user drops or selects an image on the Report Issue page.
    Returns predicted category, confidence %, visual explanation, and alternatives.
    """
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file uploaded'}), 400

    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400

    # Save to temp directory in uploads
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'error': 'Unsupported image format'}), 400

    temp_fname = f"temp_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    temp_dir = os.path.join(Config.UPLOAD_FOLDER, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, temp_fname)
    file.save(temp_path)

    try:
        result = classify_civic_image(temp_path, hint_filename=file.filename)
        return jsonify({
            'success': True,
            'predicted_category': result['predicted_category'],
            'confidence': result['confidence'],
            'explanation': result['explanation'],
            'top_categories': result['top_categories']
        })
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@reports_api_bp.route('/nearby-issues')
def api_nearby_issues():
    """
    Returns active complaints with coordinates for Leaflet interactive map rendering.
    Excludes private citizen information for civic safety.
    """
    category = request.args.get('category')
    status = request.args.get('status')
    priority = request.args.get('priority')

    query = """
        SELECT r.id, r.complaint_id, r.category, r.description, r.latitude, r.longitude,
               r.priority, r.status, r.image_path, r.landmark, r.address, r.created_at,
               d.name as department_name
        FROM reports r
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL
    """
    params = []

    if category:
        query += " AND r.category = ?"
        params.append(category)

    if status:
        query += " AND r.status = ?"
        params.append(status)

    if priority:
        query += " AND r.priority = ?"
        params.append(priority)

    query += " ORDER BY r.created_at DESC LIMIT 200"
    reports = execute_query(query, tuple(params), fetch_all=True) or []

    # Map priority to hex color and visual badge
    color_map = {
        'CRITICAL': '#ef4444', # Red
        'HIGH': '#f97316',     # Orange
        'MEDIUM': '#eab308',   # Yellow
        'LOW': '#22c55e'       # Green
    }

    features = []
    for r in reports:
        features.append({
            'id': r['id'],
            'complaint_id': r['complaint_id'],
            'category': r['category'],
            'description': r['description'][:120] + ('...' if len(r['description']) > 120 else ''),
            'latitude': float(r['latitude']),
            'longitude': float(r['longitude']),
            'priority': r['priority'],
            'priority_color': color_map.get(r['priority'], '#64748b'),
            'status': r['status'],
            'landmark': r['landmark'] or 'N/A',
            'department': r['department_name'] or 'Pending Assignment',
            'created_at': str(r['created_at'])[:10],
            'image_url': f"/uploads/{r['image_path']}" if r['image_path'] else None
        })

    return jsonify({'success': True, 'count': len(features), 'data': features})

@reports_api_bp.route('/unread-count')
def api_unread_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    count = get_unread_count(session['user_id'])
    return jsonify({'count': count})
