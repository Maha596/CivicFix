import os
from flask import Flask, render_template, send_from_directory, session, redirect, url_for
from config import Config
from database.db import init_db, execute_query
from services.notification import get_unread_count

from routes.auth import auth_bp
from routes.citizen import citizen_bp
from routes.admin import admin_bp
from routes.reports import reports_api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'reports'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'resolutions'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'temp'), exist_ok=True)

    # Initialize database
    init_db()
    seed_initial_config_data()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_api_bp)

    # Context processors for global template access
    @app.context_processor
    def inject_global_data():
        unread = 0
        if 'user_id' in session:
            unread = get_unread_count(session['user_id'])
        return {
            'app_name': 'CivicFix',
            'unread_notifications': unread,
            'current_user': {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'role': session.get('user_role'),
                'email': session.get('user_email')
            } if 'user_id' in session else None,
            'CATEGORIES': Config.CATEGORIES,
            'PRIORITIES': Config.PRIORITIES,
            'STATUSES': Config.STATUSES
        }

    # Custom template filters
    @app.template_filter('priority_badge')
    def priority_badge_filter(priority):
        p = str(priority).upper()
        mapping = {
            'CRITICAL': 'badge-critical',
            'HIGH': 'badge-high',
            'MEDIUM': 'badge-medium',
            'LOW': 'badge-low'
        }
        return mapping.get(p, 'badge-secondary')

    @app.template_filter('status_badge')
    def status_badge_filter(status):
        s = str(status).upper()
        mapping = {
            'REPORTED': 'badge-reported',
            'VERIFIED': 'badge-verified',
            'ASSIGNED': 'badge-assigned',
            'IN_PROGRESS': 'badge-progress',
            'RESOLVED': 'badge-resolved',
            'REOPENED': 'badge-reopened',
            'REJECTED': 'badge-rejected',
            'CLOSED': 'badge-resolved'
        }
        return mapping.get(s, 'badge-secondary')

    # Serve uploaded media
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Landing page
    @app.route('/')
    def index():
        # Get live counter stats for home page hero
        total_reports = execute_query("SELECT COUNT(*) as c FROM reports", fetch_one=True)['c']
        resolved_reports = execute_query("SELECT COUNT(*) as c FROM reports WHERE status IN ('RESOLVED', 'CLOSED')", fetch_one=True)['c']
        active_reports = execute_query("SELECT COUNT(*) as c FROM reports WHERE status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED')", fetch_one=True)['c']

        # Get recent 3 resolved issues for showcase
        showcase = execute_query(
            """
            SELECT r.*, res.resolution_note, res.resolution_image
            FROM reports r
            JOIN resolutions res ON r.id = res.report_id
            WHERE r.status IN ('RESOLVED', 'CLOSED')
            ORDER BY r.updated_at DESC LIMIT 3
            """,
            fetch_all=True
        ) or []

        return render_template('index.html',
                               total_reports=total_reports,
                               resolved_reports=resolved_reports,
                               active_reports=active_reports,
                               showcase=showcase)

    @app.route('/about')
    def about():
        return render_template('about.html')

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template('errors/500.html', message="Uploaded image is too large (Maximum allowed size is 16MB)."), 413

    return app

def seed_initial_config_data():
    """Seeds default departments and categories if empty."""
    dept_count = execute_query("SELECT COUNT(*) as c FROM departments", fetch_one=True)['c']
    if dept_count == 0:
        for dept_name in Config.DEPARTMENTS:
            execute_query("INSERT INTO departments (name, description) VALUES (?, ?)",
                          (dept_name, f"Municipal department responsible for {dept_name.lower()} operations."),
                          commit=True)

    cat_count = execute_query("SELECT COUNT(*) as c FROM categories", fetch_one=True)['c']
    if cat_count == 0:
        mapping = {
            'Pothole': 'Road Maintenance',
            'Garbage': 'Sanitation',
            'Broken Streetlight': 'Electrical',
            'Water Leakage': 'Water Supply',
            'Damaged Road': 'Road Maintenance',
            'Drainage Issue': 'Drainage',
            'Fallen Tree': 'Horticulture / Parks',
            'Damaged Public Property': 'Public Works',
            'Other': 'Other'
        }
        for cat_name, dept_name in mapping.items():
            dept = execute_query("SELECT id FROM departments WHERE name = ?", (dept_name,), fetch_one=True)
            dept_id = dept['id'] if dept else None
            execute_query("INSERT INTO categories (name, default_department_id) VALUES (?, ?)",
                          (cat_name, dept_id), commit=True)

app = create_app()

if __name__ == '__main__':
    print("==================================================")
    print(" CivicFix Server Initializing...")
    print(" Access Web App: http://127.0.0.1:5000")
    print(" Administrator Portal: http://127.0.0.1:5000/admin/login")
    print("==================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
