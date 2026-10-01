import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename

from routes.auth import admin_required
from database.db import execute_query
from services.notification import send_notification
from config import Config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Metrics
    total = execute_query("SELECT COUNT(*) as count FROM reports", fetch_one=True)['count']
    new_issues = execute_query("SELECT COUNT(*) as count FROM reports WHERE status = 'REPORTED'", fetch_one=True)['count']
    pending_verif = execute_query("SELECT COUNT(*) as count FROM reports WHERE status = 'VERIFIED'", fetch_one=True)['count']
    in_progress = execute_query("SELECT COUNT(*) as count FROM reports WHERE status IN ('ASSIGNED', 'IN_PROGRESS')", fetch_one=True)['count']
    resolved = execute_query("SELECT COUNT(*) as count FROM reports WHERE status IN ('RESOLVED', 'CLOSED')", fetch_one=True)['count']
    critical = execute_query("SELECT COUNT(*) as count FROM reports WHERE priority = 'CRITICAL' AND status NOT IN ('RESOLVED', 'CLOSED')", fetch_one=True)['count']

    # Chart 1: Issues by Category
    cat_data = execute_query("SELECT category, COUNT(*) as count FROM reports GROUP BY category", fetch_all=True) or []
    chart_categories = [c['category'] for c in cat_data]
    chart_cat_counts = [c['count'] for c in cat_data]

    # Chart 2: Issues by Status
    status_data = execute_query("SELECT status, COUNT(*) as count FROM reports GROUP BY status", fetch_all=True) or []
    chart_statuses = [s['status'] for s in status_data]
    chart_status_counts = [s['count'] for s in status_data]

    # Chart 3: Issues Over Time (By date)
    time_data = execute_query(
        "SELECT DATE(created_at) as report_date, COUNT(*) as count FROM reports GROUP BY DATE(created_at) ORDER BY report_date DESC LIMIT 7",
        fetch_all=True
    ) or []
    time_data.reverse()
    chart_dates = [t['report_date'] for t in time_data]
    chart_date_counts = [t['count'] for t in time_data]

    # Chart 4: Priority Distribution
    pri_data = execute_query("SELECT priority, COUNT(*) as count FROM reports GROUP BY priority", fetch_all=True) or []
    chart_priorities = [p['priority'] for p in pri_data]
    chart_pri_counts = [p['count'] for p in pri_data]

    # Recent critical and unassigned issues
    urgent_reports_q = """
        SELECT r.*, u.name as citizen_name, d.name as department_name
        FROM reports r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE r.status NOT IN ('RESOLVED', 'CLOSED')
        ORDER BY CASE r.priority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            ELSE 4 END, r.created_at DESC
        LIMIT 6
    """
    urgent_reports = execute_query(urgent_reports_q, fetch_all=True) or []

    stats = {
        'total': total,
        'new_issues': new_issues,
        'pending_verification': pending_verif,
        'in_progress': in_progress,
        'resolved': resolved,
        'critical': critical
    }

    chart_payload = {
        'categories': chart_categories,
        'category_counts': chart_cat_counts,
        'statuses': chart_statuses,
        'status_counts': chart_status_counts,
        'dates': chart_dates,
        'date_counts': chart_date_counts,
        'priorities': chart_priorities,
        'priority_counts': chart_pri_counts
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        charts=chart_payload,
        urgent_reports=urgent_reports
    )

@admin_bp.route('/reports')
@admin_required
def manage_reports():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    category_filter = request.args.get('category', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    department_filter = request.args.get('department', '').strip()

    query = """
        SELECT r.*, u.name as citizen_name, u.phone as citizen_phone, d.name as department_name
        FROM reports r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN departments d ON r.department_id = d.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (r.complaint_id LIKE ? OR r.description LIKE ? OR u.name LIKE ? OR r.landmark LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)

    if category_filter:
        query += " AND r.category = ?"
        params.append(category_filter)

    if priority_filter:
        query += " AND r.priority = ?"
        params.append(priority_filter)

    if department_filter:
        query += " AND r.department_id = ?"
        params.append(int(department_filter))

    query += " ORDER BY r.created_at DESC"
    reports = execute_query(query, tuple(params), fetch_all=True) or []

    departments = execute_query("SELECT * FROM departments ORDER BY name ASC", fetch_all=True) or []

    return render_template(
        'admin/manage_reports.html',
        reports=reports,
        departments=departments,
        categories=Config.CATEGORIES,
        statuses=Config.STATUSES,
        priorities=Config.PRIORITIES,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
        department_filter=department_filter
    )

@admin_bp.route('/reports/<int:report_id>/update-status', methods=['POST'])
@admin_required
def update_status(report_id):
    admin_id = session['user_id']
    new_status = request.form.get('status')
    remark = request.form.get('remark', '').strip()

    report = execute_query("SELECT * FROM reports WHERE id = ?", (report_id,), fetch_one=True)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('admin.manage_reports'))

    execute_query("UPDATE reports SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, report_id), commit=True)
    execute_query(
        "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, ?, ?, ?)",
        (report_id, new_status, remark or f"Status changed to {new_status} by administrator.", admin_id),
        commit=True
    )

    send_notification(
        report['user_id'],
        f"Your complaint {report['complaint_id']} status updated to {new_status}. {remark}".strip(),
        title="Complaint Status Updated",
        report_id=report_id
    )

    flash(f"Status for {report['complaint_id']} updated to {new_status}.", 'success')
    return redirect(request.referrer or url_for('admin.manage_reports'))

@admin_bp.route('/reports/<int:report_id>/assign', methods=['POST'])
@admin_required
def assign_department(report_id):
    admin_id = session['user_id']
    dept_id = request.form.get('department_id')
    remark = request.form.get('remark', '').strip()

    report = execute_query("SELECT * FROM reports WHERE id = ?", (report_id,), fetch_one=True)
    dept = execute_query("SELECT * FROM departments WHERE id = ?", (dept_id,), fetch_one=True)

    if not report or not dept:
        flash('Invalid report or department selection.', 'danger')
        return redirect(url_for('admin.manage_reports'))

    # Update department and transition status to ASSIGNED or IN_PROGRESS
    execute_query(
        "UPDATE reports SET department_id = ?, status = 'ASSIGNED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (dept_id, report_id),
        commit=True
    )
    assign_msg = f"Assigned to {dept['name']}. {remark}".strip()
    execute_query(
        "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'ASSIGNED', ?, ?)",
        (report_id, assign_msg, admin_id),
        commit=True
    )

    send_notification(
        report['user_id'],
        f"Your complaint {report['complaint_id']} has been assigned to the {dept['name']} department.",
        title="Department Assigned",
        report_id=report_id
    )

    flash(f"Complaint {report['complaint_id']} assigned to {dept['name']}.", 'success')
    return redirect(request.referrer or url_for('admin.manage_reports'))

@admin_bp.route('/reports/<int:report_id>/change-priority', methods=['POST'])
@admin_required
def change_priority(report_id):
    admin_id = session['user_id']
    new_priority = request.form.get('priority')
    remark = request.form.get('remark', '').strip()

    report = execute_query("SELECT * FROM reports WHERE id = ?", (report_id,), fetch_one=True)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('admin.manage_reports'))

    execute_query("UPDATE reports SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_priority, report_id), commit=True)
    execute_query(
        "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, ?, ?, ?)",
        (report_id, report['status'], f"Priority modified to {new_priority}. {remark}".strip(), admin_id),
        commit=True
    )

    flash(f"Priority for {report['complaint_id']} set to {new_priority}.", 'info')
    return redirect(request.referrer or url_for('admin.manage_reports'))

@admin_bp.route('/reports/<int:report_id>/resolve', methods=['POST'])
@admin_required
def resolve_report(report_id):
    admin_id = session['user_id']
    resolution_note = request.form.get('resolution_note', '').strip()
    image_file = request.files.get('resolution_image')

    report = execute_query("SELECT * FROM reports WHERE id = ?", (report_id,), fetch_one=True)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('admin.manage_reports'))

    if not resolution_note:
        flash('Please provide resolution remarks explaining the work completed.', 'danger')
        return redirect(request.referrer or url_for('admin.manage_reports'))

    rel_image_path = None
    if image_file and image_file.filename:
        fname = f"res_{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
        dest_dir = os.path.join(Config.UPLOAD_FOLDER, 'resolutions')
        os.makedirs(dest_dir, exist_ok=True)
        image_file.save(os.path.join(dest_dir, fname))
        rel_image_path = f"resolutions/{fname}"

    # Insert or update resolutions table
    res_check = execute_query("SELECT id FROM resolutions WHERE report_id = ?", (report_id,), fetch_one=True)
    if res_check:
        execute_query(
            "UPDATE resolutions SET resolution_image = ?, resolution_note = ?, resolved_by = ?, resolved_at = CURRENT_TIMESTAMP WHERE report_id = ?",
            (rel_image_path, resolution_note, admin_id, report_id),
            commit=True
        )
    else:
        execute_query(
            "INSERT INTO resolutions (report_id, resolution_image, resolution_note, resolved_by) VALUES (?, ?, ?, ?)",
            (report_id, rel_image_path, resolution_note, admin_id),
            commit=True
        )

    # Transition status to RESOLVED
    execute_query("UPDATE reports SET status = 'RESOLVED', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (report_id,), commit=True)
    execute_query(
        "INSERT INTO report_updates (report_id, status, remark, updated_by) VALUES (?, 'RESOLVED', ?, ?)",
        (report_id, f"Resolved by authority. {resolution_note}", admin_id),
        commit=True
    )

    send_notification(
        report['user_id'],
        f"Your complaint {report['complaint_id']} has been resolved! Please verify and confirm resolution.",
        title="Issue Resolved",
        report_id=report_id
    )

    flash(f"Complaint {report['complaint_id']} successfully resolved with evidence recorded.", 'success')
    return redirect(request.referrer or url_for('admin.manage_reports'))

@admin_bp.route('/departments', methods=['GET', 'POST'])
@admin_required
def departments():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if name:
            try:
                execute_query("INSERT INTO departments (name, description) VALUES (?, ?)", (name, description), commit=True)
                flash(f"Department '{name}' added successfully.", 'success')
            except Exception as e:
                flash(f"Failed to add department: {e}", 'danger')
        return redirect(url_for('admin.departments'))

    depts = execute_query(
        """
        SELECT d.*, COUNT(r.id) as total_reports,
               SUM(CASE WHEN r.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_reports
        FROM departments d
        LEFT JOIN reports r ON d.id = r.department_id
        GROUP BY d.id
        ORDER BY d.name ASC
        """,
        fetch_all=True
    ) or []

    return render_template('admin/departments.html', departments=depts)

@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id') or None
        priority = request.form.get('default_priority', 'MEDIUM')
        if name:
            try:
                execute_query(
                    "INSERT INTO categories (name, default_department_id, default_priority) VALUES (?, ?, ?)",
                    (name, dept_id, priority),
                    commit=True
                )
                flash(f"Category '{name}' created.", 'success')
            except Exception as e:
                flash(f"Error creating category: {e}", 'danger')
        return redirect(url_for('admin.categories'))

    cats = execute_query(
        """
        SELECT c.*, d.name as department_name, COUNT(r.id) as usage_count
        FROM categories c
        LEFT JOIN departments d ON c.default_department_id = d.id
        LEFT JOIN reports r ON c.name = r.category
        GROUP BY c.id
        ORDER BY c.name ASC
        """,
        fetch_all=True
    ) or []

    departments = execute_query("SELECT * FROM departments ORDER BY name ASC", fetch_all=True) or []
    return render_template('admin/categories.html', categories=cats, departments=departments)
