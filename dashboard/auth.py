import sqlite3
import os
import hashlib
import secrets
from functools import wraps
from flask import session, redirect, url_for, flash, request

# Create auth database if it doesn't exist
def init_auth_db():
    os.makedirs('dashboard', exist_ok=True)
    conn = sqlite3.connect('dashboard/auth.db')
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        email TEXT UNIQUE,
        is_admin BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if admin user exists, create default if not
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        # Create default admin user (username: admin, password: admin123)
        salt = secrets.token_hex(16)
        password = "admin123"
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, email, is_admin) VALUES (?, ?, ?, ?, ?)",
            ("admin", password_hash, salt, "admin@example.com", True)
        )
    
    conn.commit()
    conn.close()

# User authentication functions
def verify_password(username, password):
    conn = sqlite3.connect('dashboard/auth.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    stored_hash, salt = result
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    
    return password_hash == stored_hash

def create_user(username, password, email=None, is_admin=False):
    conn = sqlite3.connect('dashboard/auth.db')
    cursor = conn.cursor()
    
    try:
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, email, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, salt, email, is_admin)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_user(username):
    conn = sqlite3.connect('dashboard/auth.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, email, is_admin FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'is_admin': bool(user[3])
        }
    return None

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if not session.get('is_admin', False):
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
