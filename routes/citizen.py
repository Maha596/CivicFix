import os
import uuid
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename

from routes.auth import login_required
from database.db import execute_query
from services.ai_classifier import classify_civic_image
from services.priority import calculate_priority
from services.duplicate_detector import detect_duplicates, record_duplicate_links
from services.notification import send_notification, notify_admins, mark_notification_read, mark_all_read, get_user_notifications
from config import Config

citizen_bp = Blueprint('citizen', __name__)

def generate_complaint_id():
    """Generates sequential complaint ID format CIV-2026-XXXXX"""
    year = datetime.datetime.now().year
    res = execute_query("SELECT COUNT(*) as count FROM reports", fetch_one=True)
    count = (res['count'] if res else 0) + 1
    return f"CIV-{year}-{count:05d}"

@citizen_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    
    # Query summary metrics for current citizen
    total_q = "SELECT COUNT(*) as count FROM reports WHERE user_id = ?"
    total = execute_query(total_q, (user_id,), fetch_one=True)['count']

    pending_q = "SELECT COUNT(*) as count FROM reports WHERE user_id = ? AND status IN ('REPORTED', 'VERIFIED')"
    pending = execute_query(pending_q, (user_id,), fetch_one=True)['count']

    progress_q = "SELECT COUNT(*) as count FROM reports WHERE user_id = ? AND status IN ('ASSIGNED', 'IN_PROGRESS')"
    in_progress = execute_query(progress_q, (user_id,), fetch_one=True)['count']

    resolved_q = "SELECT COUNT(*) as count FROM reports WHERE user_id = ? AND status IN ('RESOLVED', 'CLOSED')"
    resolved = execute_query(resolved_q, (user_id,), fetch_one=True)['count']

    high_pri_q = "SELECT COUNT(*) as count FROM reports WHERE user_id = ? AND priority IN ('HIGH', 'CRITICAL')"
    high_priority = execute_query(high_pri_q, (user_id,), fetch_one=True)['count']

    # Recent complaints
    recent_reports_q = """
        SELECT r.*, d.name as department_name
        FROM reports r
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC
        LIMIT 6
    """
    recent_reports = execute_query(recent_reports_q, (user_id,), fetch_all=True) or []

    stats = {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'high_priority': high_priority
    }

    return render_template('citizen_dashboard.html', stats=stats, recent_reports=recent_reports)

@citizen_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_issue():
    if request.method == 'POST':
        user_id = session['user_id']
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        severity = request.form.get('severity', 'MEDIUM').strip().upper()
        landmark = request.form.get('landmark', '').strip()
        address = request.form.get('address', '').strip()
        lat_raw = request.form.get('latitude', '').strip()
        lon_raw = request.form.get('longitude', '').strip()

        # Latitude / Longitude parsing
        latitude = float(lat_raw) if lat_raw else None
        longitude = float(lon_raw) if lon_raw else None

        if not category or not description:
            flash('Please select an issue category and provide an accurate description.', 'danger')
            return render_template('report_issue.html', categories=Config.CATEGORIES)

        # Image processing
        image_file = request.files.get('image')
        image_rel_path = None
        ai_prediction = None
        ai_confidence = 0.0

        if image_file and image_file.filename:
            ext = image_file.filename.rsplit('.', 1)[-1].lower() if '.' in image_file.filename else ''
            if ext not in Config.ALLOWED_EXTENSIONS:
                flash(f'Invalid file format. Allowed extensions: {", ".join(Config.ALLOWED_EXTENSIONS)}', 'danger')
                return render_template('report_issue.html', categories=Config.CATEGORIES)

            fname = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            dest_dir = os.path.join(Config.UPLOAD_FOLDER, 'reports')
            os.makedirs(dest_dir, exist_ok=True)
            save_path = os.path.join(dest_dir, fname)
            image_file.save(save_path)
            image_rel_path = f"reports/{fname}"

            # Run AI classification
            classification = classify_civic_image(save_path, hint_filename=image_file.filename)
            ai_prediction = classification.get('predicted_category')
            ai_confidence = classification.get('confidence', 0.0)
        else:
            # If no image provided, assign manual category with standard confidence
            ai_prediction = category
            ai_confidence = 75.0

        # Intelligent Priority Calculation
        priority_data = calculate_priority(
            category=category,
            severity=severity,
            latitude=latitude,
            longitude=longitude,
            description=description,
            landmark=landmark
        )

        complaint_id = generate_complaint_id()

        # Duplicate Issue Detection
        dup_result = detect_duplicates(category, latitude, longitude, radius_meters=150)
        is_dup = 1 if dup_result['is_duplicate'] else 0
        dup_of = dup_result['matches'][0]['complaint_id'] if dup_result['matches'] else None

        # Insert into database
        insert_q = """
            INSERT INTO reports (
                complaint_id, user_id, category, description, image_path,
                latitude, longitude, address, landmark, severity,
                priority, priority_score, priority_reason, ai_prediction, ai_confidence,
                status, is_duplicate, duplicate_of
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REPORTED', ?, ?)
        """
        report_id = execute_query(
            insert_q,
            (
                complaint_id, user_id, category, description, image_rel_path,
                latitude, longitude, address, landmark, severity,
                priority_data['priority'], priority_data['score'], priority_data['explanation'],
                ai_prediction, ai_confidence, is_dup, dup_of
            ),
            commit=True
        )

        # Record duplicate links if detected
        if dup_result['matches']:
            record_duplicate_links(report_id, dup_result['matches'])

        # Record initial status update in history
        update_q = """
            INSERT INTO report_updates (report_id, status, remark, updated_by)
            VALUES (?, 'REPORTED', 'Civic complaint submitted by citizen via web portal.', ?)
        """
        execute_query(update_q, (report_id, user_id), commit=True)

        # Notify Citizen
        send_notification(
            user_id,
            f"Your complaint {complaint_id} ({category}) has been submitted and is queued for verification.",
            title="Complaint Filed Successfully",
            report_id=report_id
        )

        # Notify Administrators
        dup_note = f" (Potential duplicate of {dup_of})" if is_dup else ""
        notify_admins(
            f"New {priority_data['priority']} priority issue filed: {complaint_id} - {category}{dup_note}.",
            title="New Civic Report Received",
            report_id=report_id
        )

        flash(f'Report submitted successfully! Your tracking ID is {complaint_id}', 'success')
        return redirect(url_for('citizen.report_details', complaint_id=complaint_id))

    return render_template('report_issue.html', categories=Config.CATEGORIES)

@citizen_bp.route('/my-reports')
@login_required
def my_reports():
    user_id = session['user_id']
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    category_filter = request.args.get('category', '').strip()
    priority_filter = request.args.get('priority', '').strip()

    query = """
        SELECT r.*, d.name as department_name
        FROM reports r
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE r.user_id = ?
    """
    params = [user_id]

    if search:
        query += " AND (r.complaint_id LIKE ? OR r.description LIKE ? OR r.landmark LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)

    if category_filter:
        query += " AND r.category = ?"
        params.append(category_filter)

    if priority_filter:
        query += " AND r.priority = ?"
        params.append(priority_filter)

    query += " ORDER BY r.created_at DESC"
    reports = execute_query(query, tuple(params), fetch_all=True) or []

    return render_template(
        'my_reports.html',
        reports=reports,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
        categories=Config.CATEGORIES,
        statuses=Config.STATUSES
    )

@citizen_bp.route('/reports/<complaint_id>')
def report_details(complaint_id):
    query = """
        SELECT r.*, u.name as citizen_name, u.email as citizen_email, u.phone as citizen_phone,
               d.name as department_name
        FROM reports r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE r.complaint_id = ?
    """
    report = execute_query(query, (complaint_id,), fetch_one=True)
    if not report:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('index'))

    # Fetch status history timeline
    timeline_q = """
        SELECT ru.*, u.name as updater_name, u.role as updater_role
        FROM report_updates ru
        JOIN users u ON ru.updated_by = u.id
        WHERE ru.report_id = ?
        ORDER BY ru.created_at ASC
    """
    timeline = execute_query(timeline_q, (report['id'],), fetch_all=True) or []

    # Fetch resolution evidence if resolved
    resolution = execute_query(
        """
        SELECT res.*, u.name as resolver_name
        FROM resolutions res
        JOIN users u ON res.resolved_by = u.id
        WHERE res.report_id = ?
        """,
        (report['id'],),
        fetch_one=True
    )

    # Fetch duplicate linkages
    dup_links_q = """
        SELECT dl.*, r.complaint_id as dup_complaint_id, r.category as dup_category, r.status as dup_status
        FROM duplicate_links dl
        JOIN reports r ON dl.possible_duplicate_id = r.id
        WHERE dl.report_id = ?
    """
    duplicate_links = execute_query(dup_links_q, (report['id'],), fetch_all=True) or []

    is_owner = ('user_id' in session and session['user_id'] == report['user_id'])
    is_admin = ('user_role' in session and session['user_role'] == 'admin')

    return render_template(
        'report_details.html',
        report=report,
        timeline=timeline,
        resolution=resolution,
        duplicate_links=duplicate_links,
        is_owner=is_owner,
        is_admin=is_admin
    )

@citizen_bp.route('/reports/<complaint_id>/confirm-resolution', methods=['POST'])
@login_required
def confirm_resolution(complaint_id):
    user_id = session['user_id']
    report = execute_query("SELECT * FROM reports WHERE complaint_id = ?", (complaint_id,), fetch_one=True)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('citizen.dashboard'))

    if report['user_id'] != user_id:
        flash('You can only confirm complaints submitted by your account.', 'danger')
        return redirect(url_for('citizen.report_details', complaint_id=complaint_id))

    action = request.form.get('action') # 'resolved' or 'reopen'
    citizen_note = request.form.get('note', '').strip()

    if action == 'resolved':
        execute_query("UPDATE reports SET status = 'RESOLVED' WHERE id = ?", (report['id'],), commit=True)
        execute_query(
            "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'RESOLVED', ?, ?)",
            (report['id'], f"Citizen confirmed issue resolved. {citizen_note}".strip(), user_id),
            commit=True
        )
        flash('Thank you for confirming the resolution!', 'success')
    elif action == 'reopen':
        execute_query("UPDATE reports SET status = 'REOPENED' WHERE id = ?", (report['id'],), commit=True)
        execute_query(
            "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'REOPENED', ?, ?)",
            (report['id'], f"Citizen stated issue still exists: {citizen_note}", user_id),
            commit=True
        )
        notify_admins(
            f"Citizen reported that issue {complaint_id} still exists. Status reverted to REOPENED.",
            title="Complaint Reopened",
            report_id=report['id']
        )
        flash('Complaint has been reopened. The department will review the issue again.', 'info')

    return redirect(url_for('citizen.report_details', complaint_id=complaint_id))

@citizen_bp.route('/nearby')
def nearby_issues():
    return render_template('nearby_map.html', categories=Config.CATEGORIES, statuses=Config.STATUSES)

@citizen_bp.route('/notifications')
@login_required
def notifications():
    user_id = session['user_id']
    notifs = get_user_notifications(user_id, limit=50)
    return render_template('notifications.html', notifications=notifs)

@citizen_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    mark_notification_read(notif_id, session['user_id'])
    return jsonify({'success': True})

@citizen_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_as_read():
    mark_all_read(session['user_id'])
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('citizen.notifications'))
