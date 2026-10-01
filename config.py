import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'civicfix-super-secret-key-2026-btech-ai-ds')
    
    # SQLite default for instant portability; easily switched to MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'civicfix_db')
    
    USE_MYSQL = os.environ.get('USE_MYSQL', 'False').lower() in ('true', '1')
    
    SQLITE_PATH = os.path.join(BASE_DIR, 'civicfix.db')
    
    # Location Defaults - Coimbatore Municipal Region
    DEFAULT_CITY = "Coimbatore"
    DEFAULT_LATITUDE = 11.0168
    DEFAULT_LONGITUDE = 76.9558
    MUNICIPAL_CORP = "Coimbatore City Municipal Corporation (CCMC)"
    
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max image upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    CATEGORIES = [
        'Pothole',
        'Garbage',
        'Broken Streetlight',
        'Water Leakage',
        'Damaged Road',
        'Drainage Issue',
        'Fallen Tree',
        'Damaged Public Property',
        'Other'
    ]
    
    DEPARTMENTS = [
        'Road Maintenance',
        'Sanitation',
        'Electrical',
        'Water Supply',
        'Drainage',
        'Public Works',
        'Traffic & Safety',
        'Horticulture / Parks',
        'Other'
    ]
    
    PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    STATUSES = ['REPORTED', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REOPENED', 'REJECTED']
