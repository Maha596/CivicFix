from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database.db import execute_query

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the administrator portal.', 'warning')
            return redirect(url_for('auth.admin_login', next=request.url))
        if session.get('user_role') != 'admin':
            flash('Unauthorized access: Administrator credentials required.', 'danger')
            return redirect(url_for('citizen.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not name or not email or not password:
            flash('All required fields must be filled.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        # Check existing email
        existing_user = execute_query("SELECT id FROM users WHERE email = ?", (email,), fetch_one=True)
        if existing_user:
            flash('An account with this email address already exists.', 'warning')
            return render_template('register.html', name=name, email=email, phone=phone)

        # Insert citizen
        pwd_hash = generate_password_hash(password)
        insert_query = """
            INSERT INTO users (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, 'citizen')
        """
        user_id = execute_query(insert_query, (name, email, phone, pwd_hash), commit=True)

        flash('Registration successful! Please sign in to continue.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html', email=email)

        user = execute_query("SELECT * FROM users WHERE email = ?", (email,), fetch_one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']

            flash(f"Welcome back, {user['name']}!", 'success')
            next_url = request.args.get('next')
            if user['role'] == 'admin':
                return redirect(next_url or url_for('admin.dashboard'))
            return redirect(next_url or url_for('citizen.dashboard'))
        else:
            flash('Invalid email address or password.', 'danger')

    return render_template('login.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('user_role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter administrator email and password.', 'danger')
            return render_template('admin_login.html', email=email)

        user = execute_query("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,), fetch_one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = 'admin'

            flash('Administrator authentication successful.', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin.dashboard'))
        else:
            flash('Invalid administrator credentials or unauthorized role.', 'danger')

    return render_template('admin_login.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = execute_query("SELECT * FROM users WHERE id = ?", (session['user_id'],), fetch_one=True)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name:
            flash('Name cannot be empty.', 'danger')
            return render_template('profile.html', user=user)

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return render_template('profile.html', user=user)
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('profile.html', user=user)
            
            pwd_hash = generate_password_hash(new_password)
            execute_query(
                "UPDATE users SET name = ?, phone = ?, password = ? WHERE id = ?",
                (name, phone, pwd_hash, session['user_id']),
                commit=True
            )
        else:
            execute_query(
                "UPDATE users SET name = ?, phone = ? WHERE id = ?",
                (name, phone, session['user_id']),
                commit=True
            )

        session['user_name'] = name
        flash('Profile updated successfully!', 'success')
        user = execute_query("SELECT * FROM users WHERE id = ?", (session['user_id'],), fetch_one=True)

    return render_template('profile.html', user=user)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))
