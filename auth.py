from functools import wraps
from flask import Blueprint, request, jsonify, abort
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
def register():
    """API endpoint to register a new user."""
    data = request.get_json() or {}
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'common') # Defaults to 'common'

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields: username, email, password"}), 400

    if role not in ['common', 'industrial', 'admin']:
        return jsonify({"error": "Invalid role specified. Must be 'common', 'industrial', or 'admin'"}), 400

    # Check if user already exists
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or Email already registered"}), 400

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
        }), 210  # Standard custom HTTP success status code
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to register user: {str(e)}"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """API endpoint to login a user."""
    if current_user.is_authenticated:
        return jsonify({"message": "Already authenticated"}), 200

    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter(User.username == username).first()
    
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

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
