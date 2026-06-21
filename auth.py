from functools import wraps
import re
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, abort, current_app
from flask_login import LoginManager, login_user, logout_user, current_user
from database import db
from models import User, UserPoints

# Initialize Flask-Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON 401 response instead of redirecting to login page for APIs."""
    return jsonify({"error": "Authentication required"}), 401

# Define authentication blueprint
auth_bp = Blueprint('auth', __name__)

# Rate-limiting and lockout settings (in-memory)
# Note: in-memory store resets on process restart. For multi-process deployments
# use a shared store (Redis) for production.
_FAILED_LOGINS = {}
MAX_FAILED_ATTEMPTS = 5
FAILED_WINDOW_SECONDS = 15 * 60  # 15 minutes
LOCKOUT_SECONDS = 15 * 60  # 15 minutes


def _get_client_identifier(username=None):
    """Return a stable identifier for rate-limiting: username (if provided) else client IP."""
    if username:
        return f"user:{username.lower()}"
    ip = request.remote_addr or 'unknown'
    return f"ip:{ip}"


def _is_locked(identifier):
    rec = _FAILED_LOGINS.get(identifier)
    if not rec:
        return False
    locked_until = rec.get('locked_until')
    if locked_until and time.time() < locked_until:
        return True
    return False


def _register_failure(identifier):
    rec = _FAILED_LOGINS.setdefault(identifier, {'count': 0, 'first': time.time(), 'locked_until': None})
    now = time.time()
    # reset window
    if now - rec['first'] > FAILED_WINDOW_SECONDS:
        rec['count'] = 0
        rec['first'] = now
        rec['locked_until'] = None
    rec['count'] += 1
    if rec['count'] >= MAX_FAILED_ATTEMPTS:
        rec['locked_until'] = now + LOCKOUT_SECONDS


def _reset_failures(identifier):
    if identifier in _FAILED_LOGINS:
        del _FAILED_LOGINS[identifier]


def require_same_origin(f):
    """Simple CSRF-like protection: ensure Origin or Referer matches host_url for unsafe methods."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE'):
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')
            host_url = request.host_url
            if origin:
                if not origin.startswith(host_url):
                    current_app.logger.warning('Potential CSRF: mismatched Origin')
                    return jsonify({'error': 'Invalid request origin.'}), 400
            elif referer:
                if not referer.startswith(host_url):
                    current_app.logger.warning('Potential CSRF: mismatched Referer')
                    return jsonify({'error': 'Invalid request origin.'}), 400
            else:
                # No Origin/Referer present for a state-changing request — reject.
                current_app.logger.warning('Potential CSRF: missing Origin/Referer')
                return jsonify({'error': 'Invalid request origin.'}), 400
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    """Decorator to restrict access to specific user roles.
    
    Usage:
        @app.route('/admin')
        @login_required
        @role_required('admin')
        def admin_dashboard():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401
            if current_user.role not in roles:
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/register', methods=['POST'])
@require_same_origin
def register():
    """API endpoint to register a new user.

    Changes:
    - Sanitize and validate inputs (username, email, password).
    - Enforce strong password policy per requirements.
    - Avoid exposing internal exception details in responses; log them at debug level.
    """
    data = request.get_json() or {}

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    role = data.get('role', 'common')  # Defaults to 'common'

    # Basic validations
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields: username, email, password"}), 400

    if role not in ['common', 'industrial', 'admin']:
        return jsonify({"error": "Invalid role specified."}), 400

    # Validate email format
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Invalid email address."}), 400

    # Enforce strong password policy
    def _valid_password(pw: str) -> bool:
        if len(pw) < 8:
            return False
        if not re.search(r"[A-Z]", pw):
            return False
        if not re.search(r"[a-z]", pw):
            return False
        if not re.search(r"[0-9]", pw):
            return False
        if not re.search(r"[^A-Za-z0-9]", pw):
            return False
        return True

    if not _valid_password(password):
        return jsonify({"error": "Password does not meet complexity requirements."}), 400

    # Prevent duplicate usernames/emails
    if User.query.filter((User.username == username) | (User.email == email)).first():
        # For registration it's acceptable to tell user the account exists, but avoid
        # exposing which field matched to reduce enumeration risk in other endpoints.
        return jsonify({"error": "Account with provided credentials already exists."}), 400

    try:
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role
            }
        }), 210
    except Exception as e:
        db.session.rollback()
        current_app.logger.debug('Registration error: %s', repr(e))
        return jsonify({"error": "Failed to register user."}), 500


@auth_bp.route('/login', methods=['POST'])
@require_same_origin
def login():
    """API endpoint to login a user.

    Changes:
    - Input sanitization
    - Rate limiting and temporary lockouts on repeated failures
    - Unified error message for invalid username/password to prevent enumeration
    - Avoid logging sensitive data
    """
    if current_user.is_authenticated:
        return jsonify({"message": "Already authenticated"}), 200

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    identifier = _get_client_identifier(username=username)
    ip_identifier = _get_client_identifier(username=None)

    # Check lockout by username or IP
    if _is_locked(identifier) or _is_locked(ip_identifier):
        return jsonify({"error": "Too many failed login attempts. Try again later."}), 429

    user = User.query.filter(User.username == username).first()

    # Don't reveal which of username/password failed — use a single message
    auth_ok = False
    if user and user.check_password(password):
        auth_ok = True

    if not auth_ok:
        # Register failure for both username and IP to mitigate brute force
        _register_failure(identifier)
        _register_failure(ip_identifier)
        return jsonify({"error": "Invalid username or password"}), 401

    # Successful login: reset failure counters
    _reset_failures(identifier)
    _reset_failures(ip_identifier)

    login_user(user)
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "total_points": user.total_points
        }
    }), 200


@auth_bp.route('/logout', methods=['POST', 'GET'])
@require_same_origin
def logout():
    """API endpoint to logout the current user."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Not logged in"}), 400
        
    logout_user()
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route('/me', methods=['GET'])
def get_current_user_profile():
    """Fetch profile details of currently logged in user."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
        
    # Always sync points before returning profile
    current_user.update_points()
    db.session.commit()

    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "total_points": current_user.total_points
    }), 200


def add_points_to_ledger(user, action_type, points):
    """Utility function to add points to a user's ledger and update cached total_points."""
    if user.role != 'common':
        return None
    ledger_entry = UserPoints(
        user_id=user.id,
        action_type=action_type,
        points_earned=points
    )
    db.session.add(ledger_entry)
    db.session.flush() # Sync ID
    user.update_points()
    db.session.commit()
    return ledger_entry
