"""
CivicFix - In-App Notification System
Generates and manages notifications for citizens and administrators
regarding complaint status transitions, assignments, and resolution confirmations.
"""

from database.db import execute_query

def send_notification(user_id, message, title="Complaint Update", report_id=None):
    """Inserts a notification record for a user."""
    query = """
        INSERT INTO notifications (user_id, report_id, title, message, is_read)
        VALUES (?, ?, ?, ?, 0)
    """
    return execute_query(query, (user_id, report_id, title, message), commit=True)

def notify_admins(message, title="New Civic Activity", report_id=None):
    """Sends notification to all administrators."""
    admin_users = execute_query("SELECT id FROM users WHERE role = 'admin'", fetch_all=True) or []
    for adm in admin_users:
        send_notification(adm['id'], message, title=title, report_id=report_id)

def get_user_notifications(user_id, limit=20):
    """Fetches latest notifications for a user."""
    query = """
        SELECT id, report_id, title, message, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """
    return execute_query(query, (user_id, limit), fetch_all=True) or []

def get_unread_count(user_id):
    """Returns count of unread notifications for navbar badge."""
    query = "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0"
    res = execute_query(query, (user_id,), fetch_one=True)
    return res['count'] if res else 0

def mark_notification_read(notification_id, user_id):
    """Marks single notification as read."""
    query = "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?"
    execute_query(query, (notification_id, user_id), commit=True)

def mark_all_read(user_id):
    """Marks all notifications as read for a user."""
    query = "UPDATE notifications SET is_read = 1 WHERE user_id = ?"
    execute_query(query, (user_id,), commit=True)
