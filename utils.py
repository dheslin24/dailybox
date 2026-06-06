from functools import wraps

from flask import jsonify, redirect, render_template, session

from constants import ALLOWED_EXTENSIONS


def apology(message, code=400):
    """Renders message as an apology to user."""
    return render_template("apology.html", top=code, bottom=message, code=code)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("userid") is None:
            return redirect("/app/login")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("is_admin") == 0:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') != 1:
            return jsonify({'error': 'forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function


def golf_admin_required(f):
    """Passes for super admins, golf pool grant holders, or pool deputies."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') == 1:
            return f(*args, **kwargs)
        uid = session.get('userid')
        if uid:
            from db_accessor.db_accessor import db2
            if db2("SELECT 1 FROM golf_pool_grants WHERE user_id=%s", (uid,)):
                return f(*args, **kwargs)
            if db2("SELECT 1 FROM golf_pool_deputies WHERE user_id=%s", (uid,)):
                return f(*args, **kwargs)
        return jsonify({'error': 'forbidden'}), 403
    return decorated_function


def soccer_admin_required(f):
    """Passes for super admins, soccer pool grant holders, or pool deputies."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') == 1:
            return f(*args, **kwargs)
        uid = session.get('userid')
        if uid:
            from db_accessor.db_accessor import db2
            if db2("SELECT 1 FROM soccer_pool_grants WHERE user_id=%s", (uid,)):
                return f(*args, **kwargs)
            if db2("SELECT 1 FROM soccer_pool_deputies WHERE user_id=%s", (uid,)):
                return f(*args, **kwargs)
        return jsonify({'error': 'forbidden'}), 403
    return decorated_function


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
