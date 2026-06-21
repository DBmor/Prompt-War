from datetime import datetime, timezone
import requests
from flask import Blueprint, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from database import db
from models import User, UserPoints, Blog, Comment, Like, Article, ArticleRead, B2CResult, B2BResult, LoggedAction
from auth import role_required, add_points_to_ledger

routes_bp = Blueprint('routes', __name__)

# Cache for the discovered Gemini API URL to speed up subsequent requests
_GEMINI_ENDPOINT_CACHE = None

# ==========================================
# 1. ARTICLE & READING ENGINE ROUTES
# ==========================================

@routes_bp.route('/articles', methods=['GET'])
def get_articles():
    """Retrieve all available awareness articles."""
    articles = Article.query.all()
    return jsonify([{
        "id": art.id,
        "title": art.title,
        "content": art.content,
        "created_at": art.created_at.isoformat()
    } for art in articles]), 200


@routes_bp.route('/articles/<int:article_id>/start-read', methods=['POST'])
@login_required
def start_reading(article_id):
    """Mark the beginning of reading an article to track scroll depth / timer."""
    # Check if article exists
    article = Article.query.get_or_404(article_id)
    
    # Check if there is already an unfinished reading log for this article
    unfinished_read = ArticleRead.query.filter_by(
        user_id=current_user.id,
        article_id=article_id,
        completed_at=None
    ).first()
    
    if unfinished_read:
        return jsonify({
            "message": "Reading session already in progress",
            "started_at": unfinished_read.started_at.isoformat()
        }), 200

    # Create new reading session
    read_session = ArticleRead(
        user_id=current_user.id,
        article_id=article_id,
        started_at=datetime.now(timezone.utc),
        points_awarded=False
    )
    db.session.add(read_session)
    db.session.commit()
    
    return jsonify({
        "message": "Reading session started",
        "started_at": read_session.started_at.isoformat()
    }), 201


@routes_bp.route('/articles/<int:article_id>/complete-read', methods=['POST'])
@login_required
def complete_reading(article_id):
    """Mark article reading complete, enforcing minimum 30-second duration for points."""
    article = Article.query.get_or_404(article_id)
    
    # Find the active reading log
    read_record = ArticleRead.query.filter_by(
        user_id=current_user.id,
        article_id=article_id,
        completed_at=None
    ).first()
    
    if not read_record:
        return jsonify({"error": "No active reading session found for this article"}), 400

    now = datetime.now(timezone.utc)
    started_at = read_record.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
        
    elapsed_seconds = (now - started_at).total_seconds()
    
    # Enforce minimum 30-second timer to prevent farming
    if elapsed_seconds < 30.0:
        return jsonify({
            "error": "Minimum reading time not met. You must read for at least 30 seconds.",
            "elapsed_seconds": round(elapsed_seconds, 2),
            "remaining_seconds": round(30.0 - elapsed_seconds, 2)
        }), 400

    # Award points if they haven't been awarded yet for this read session
    points_gained = 0
    if not read_record.points_awarded:
        # Check if the user has already successfully earned points for reading THIS article before
        already_earned = ArticleRead.query.filter_by(
            user_id=current_user.id,
            article_id=article_id,
            points_awarded=True
        ).first()
        
        if not already_earned:
            read_record.points_awarded = True
            add_points_to_ledger(current_user, 'READ_ARTICLE', 10)
            points_gained = 10

    read_record.completed_at = now
    db.session.commit()
    
    return jsonify({
        "message": "Reading session successfully completed",
        "points_earned": points_gained,
        "total_points": current_user.total_points
    }), 200


# ==========================================
# 2. COMMUNITY BLOGGING PORTAL ROUTES
# ==========================================

@routes_bp.route('/blogs', methods=['POST'])
@login_required
def create_blog():
    """Create a new blog draft. Defaults to pending admin moderation."""
    data = request.get_json() or {}
    title = data.get('title')
    content = data.get('content')

    if not title or not content:
        return jsonify({"error": "Title and content are required fields"}), 400

    blog = Blog(
        author_id=current_user.id,
        title=title,
        content=content,
        status='pending'  # Flags is_approved = False conceptually
    )
    db.session.add(blog)
    db.session.commit()

    return jsonify({
        "message": "Blog draft submitted for review",
        "blog": {
            "id": blog.id,
            "title": blog.title,
            "status": blog.status,
            "created_at": blog.created_at.isoformat()
        }
    }), 201


@routes_bp.route('/blogs', methods=['GET'])
def get_approved_blogs():
    """Retrieve public feed of approved blog posts."""
    blogs = Blog.query.filter_by(status='approved').order_by(Blog.created_at.desc()).all()
    return jsonify([{
        "id": b.id,
        "title": b.title,
        "content": b.content,
        "author": b.author.username,
        "created_at": b.created_at.isoformat(),
        "likes_count": len(b.likes),
        "comments_count": len(b.comments),
        "comments": [{
            "author": c.user.username,
            "content": c.content,
            "created_at": c.created_at.isoformat()
        } for c in b.comments]
    } for b in blogs]), 200


@routes_bp.route('/blogs/<int:blog_id>/comments', methods=['POST'])
@login_required
def add_comment(blog_id):
    """Add comment to a blog and receive +5 points immediately."""
    blog = Blog.query.get_or_404(blog_id)
    
    # Only allow commenting on approved blogs or if it's the author/admin
    if blog.status != 'approved' and current_user.role != 'admin' and blog.author_id != current_user.id:
        return jsonify({"error": "Cannot comment on unapproved blog posts"}), 403
        
    data = request.get_json() or {}
    content = data.get('content')
    
    if not content or not content.strip():
        return jsonify({"error": "Comment content cannot be empty"}), 400

    comment = Comment(
        blog_id=blog.id,
        user_id=current_user.id,
        content=content
    )
    db.session.add(comment)
    
    # Award +5 points immediately to the commenter
    add_points_to_ledger(current_user, 'LEAVE_COMMENT', 5)
    db.session.commit()

    return jsonify({
        "message": "Comment posted successfully",
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "user": current_user.username,
            "created_at": comment.created_at.isoformat()
        },
        "points_earned": 5,
        "total_points": current_user.total_points
    }), 201


@routes_bp.route('/blogs/<int:blog_id>/like', methods=['POST'])
@login_required
def toggle_like(blog_id):
    """Toggle a like on a blog post."""
    blog = Blog.query.get_or_404(blog_id)
    
    existing_like = Like.query.filter_by(
        blog_id=blog.id,
        user_id=current_user.id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
        msg = "Blog unliked successfully"
    else:
        new_like = Like(
            blog_id=blog.id,
            user_id=current_user.id
        )
        db.session.add(new_like)
        db.session.commit()
        liked = True
        msg = "Blog liked successfully"

    return jsonify({
        "message": msg,
        "liked": liked,
        "likes_count": Like.query.filter_by(blog_id=blog.id).count()
    }), 200


# ==========================================
# 3. ADMIN WORKFLOW / MODERATION ROUTES
# ==========================================

@routes_bp.route('/admin/blogs/pending', methods=['GET'])
@role_required('admin')
def get_pending_blogs():
    """Retrieve all pending blogs for admin review."""
    blogs = Blog.query.filter_by(status='pending').order_by(Blog.created_at.asc()).all()
    return jsonify([{
        "id": b.id,
        "title": b.title,
        "content": b.content,
        "author": b.author.username,
        "created_at": b.created_at.isoformat()
    } for b in blogs]), 200


@routes_bp.route('/admin/blogs/<int:blog_id>/approve', methods=['POST'])
@role_required('admin')
def approve_blog(blog_id):
    """Approve a blog post, publishing it and awarding +100 points to its author."""
    blog = Blog.query.get_or_404(blog_id)
    
    if blog.status == 'approved':
        return jsonify({"message": "Blog is already approved"}), 200

    blog.status = 'approved'
    blog.moderated_at = datetime.now(timezone.utc)
    
    # Award points to the AUTHOR of the blog, not the admin
    author = User.query.get(blog.author_id)
    add_points_to_ledger(author, 'POST_BLOG', 100)
    db.session.commit()

    return jsonify({
        "message": "Blog approved and published successfully",
        "blog_id": blog.id,
        "author_points_updated": author.total_points
    }), 200


@routes_bp.route('/admin/blogs/<int:blog_id>/reject', methods=['POST'])
@role_required('admin')
def reject_blog(blog_id):
    """Reject a blog post draft."""
    blog = Blog.query.get_or_404(blog_id)
    
    if blog.status == 'rejected':
        return jsonify({"message": "Blog is already rejected"}), 200

    blog.status = 'rejected'
    blog.moderated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Blog draft rejected successfully",
        "blog_id": blog.id
    }), 200


# ==========================================
# 4. CARBON CALCULATORS ROUTES
# ==========================================

@routes_bp.route('/calculator/b2c', methods=['POST'])
@login_required
def calculate_b2c():
    """Calculate and log personal B2C carbon footprint (lifestyle)."""
    data = request.get_json() or {}
    
    # Check if legacy fields are passed (for test backward compatibility)
    if 'red_meat' in data or 'dairy' in data or 'local_food' in data:
        red_meat = float(data.get('red_meat', 0.0))
        dairy = float(data.get('dairy', 0.0))
        local_food = float(data.get('local_food', 0.0))
        other_food = float(data.get('other_food', 0.0))
        
        petrol_diesel_km = float(data.get('petrol_diesel_km', 0.0))
        ev_km = float(data.get('ev_km', 0.0))
        public_transit_km = float(data.get('public_transit_km', 0.0))
        
        monthly_kwh = float(data.get('monthly_kwh', 0.0))

        diet_footprint = ((red_meat * 27.0) + (dairy * 3.2) + (local_food * 0.5) + (other_food * 2.5)) * 52
        transport_footprint = (petrol_diesel_km * 0.18) + (ev_km * 0.05) + (public_transit_km * 0.03)
        energy_footprint = (monthly_kwh * 12) * 0.82
    else:
        # Card Selector Fields (New UI style)
        sex = str(data.get('sex', 'female')).lower()
        body_composition = str(data.get('body_composition', 'normal')).lower()
        dietary_preference = str(data.get('dietary_preference', 'vegan')).lower()
        
        transit_mode = str(data.get('transit_mode', 'walk_bicycle')).lower()
        fuel_type = str(data.get('fuel_type', 'petrol')).lower()
        monthly_distance = float(data.get('monthly_distance', 2000.0))
        
        monthly_kwh = float(data.get('monthly_kwh', 0.0))

        # Diet Model
        baseline_sex = 300.0 if sex == 'female' else 350.0
        comp_multipliers = {'underweight': 0.9, 'normal': 1.0, 'overweight': 1.1, 'obese': 1.25}
        comp_mult = comp_multipliers.get(body_composition, 1.0)
        diet_bases = {'vegan': 600.0, 'vegetarian': 1200.0, 'omnivore': 2200.0}
        diet_base = diet_bases.get(dietary_preference, 1200.0)
        
        diet_footprint = baseline_sex * comp_mult + diet_base

        # Transport Model
        if transit_mode == 'walk_bicycle':
            transport_footprint = 0.0
        elif transit_mode == 'public_transit':
            transport_footprint = monthly_distance * 12 * 0.03
        else: # private_vehicle
            fuel_factors = {'petrol': 0.18, 'diesel': 0.20, 'hybrid': 0.10, 'lpg': 0.14, 'electric': 0.05}
            fuel_fact = fuel_factors.get(fuel_type, 0.18)
            transport_footprint = monthly_distance * 12 * fuel_fact

        # Energy Model
        energy_footprint = (monthly_kwh * 12) * 0.82

    total_footprint = diet_footprint + transport_footprint + energy_footprint

    # Save to database
    result = B2CResult(
        user_id=current_user.id,
        diet_footprint=diet_footprint,
        transport_footprint=transport_footprint,
        energy_footprint=energy_footprint,
        total_footprint=total_footprint
    )
    db.session.add(result)
    
    # Award +50 points for completing lifestyle calculator
    add_points_to_ledger(current_user, 'TAKE_ASSESSMENT', 50)
    db.session.commit()

    return jsonify({
        "message": "B2C lifestyle assessment complete",
        "points_earned": 50,
        "total_points": current_user.total_points,
        "result": {
            "id": result.id,
            "diet_footprint": round(diet_footprint, 2),
            "transport_footprint": round(transport_footprint, 2),
            "energy_footprint": round(energy_footprint, 2),
            "total_footprint": round(total_footprint, 2),
            "recorded_at": result.recorded_at.isoformat()
        }
    }), 201


@routes_bp.route('/calculator/b2b', methods=['POST'])
@login_required
def calculate_b2b():
    """Calculate and log India CCTS compliance B2B carbon intensity footprint."""
    data = request.get_json() or {}
    
    company_name = data.get('company_name')
    sector = data.get('sector')
    production_output = float(data.get('production_output', 0.0))

    if not company_name or not sector or production_output <= 0.0:
        return jsonify({"error": "Missing required fields or invalid production output"}), 400

    coal_tonnes = float(data.get('coal_tonnes', 0.0))
    diesel_liters = float(data.get('diesel_liters', 0.0))
    process_emissions = float(data.get('process_emissions', 0.0))
    grid_kwh = float(data.get('grid_kwh', 0.0))

    # Calculations (outputting tonnes of CO2e)
    scope1 = (coal_tonnes * 2.42) + (diesel_liters * 0.00268) + process_emissions
    scope2 = (grid_kwh * 0.00082) # 0.82 kg/kWh grid intensity converted to tonnes (divided by 1000)
    
    total_emissions = scope1 + scope2
    emission_intensity = total_emissions / production_output

    # Indian sector caps
    caps = {
        'steel': 2.1,
        'cement': 0.65,
        'power': 0.8,
        'other': 1.5
    }
    cap = caps.get(sector.lower(), 1.5)
    is_compliant = (emission_intensity <= cap)
    
    credits_earned = 0.0
    if is_compliant:
        credits_earned = (cap - emission_intensity) * production_output

    result = B2BResult(
        user_id=current_user.id,
        company_name=company_name,
        sector=sector,
        scope1=scope1,
        scope2=scope2,
        production_output=production_output,
        emission_intensity=emission_intensity,
        regulatory_cap=cap,
        is_compliant=is_compliant,
        credits_earned=credits_earned
    )
    db.session.add(result)
    
    # Award +50 points for completing compliance calculator
    add_points_to_ledger(current_user, 'TAKE_ASSESSMENT', 50)
    db.session.commit()

    return jsonify({
        "message": "B2B compliance assessment complete",
        "points_earned": 50,
        "total_points": current_user.total_points,
        "result": {
            "id": result.id,
            "company_name": company_name,
            "sector": sector,
            "scope1": round(scope1, 2),
            "scope2": round(scope2, 4),
            "total_emissions": round(total_emissions, 2),
            "emission_intensity": round(emission_intensity, 4),
            "regulatory_cap": cap,
            "is_compliant": is_compliant,
            "compliance_status": "Compliant" if is_compliant else "Non-Compliant - Subject to NGT / CCTS Penalties",
            "credits_earned": round(credits_earned, 2),
            "recorded_at": result.recorded_at.isoformat()
        }
    }), 201


@routes_bp.route('/calculator/history', methods=['GET'])
@login_required
def get_calculator_history():
    """Retrieve calculation history for the logged-in user."""
    b2c_history = B2CResult.query.filter_by(user_id=current_user.id).order_by(B2CResult.recorded_at.desc()).all()
    b2b_history = B2BResult.query.filter_by(user_id=current_user.id).order_by(B2BResult.recorded_at.desc()).all()
    
    return jsonify({
        "b2c": [{
            "id": r.id,
            "diet_footprint": round(r.diet_footprint, 2),
            "transport_footprint": round(r.transport_footprint, 2),
            "energy_footprint": round(r.energy_footprint, 2),
            "total_footprint": round(r.total_footprint, 2),
            "recorded_at": r.recorded_at.isoformat()
        } for r in b2c_history],
        "b2b": [{
            "id": r.id,
            "company_name": r.company_name,
            "sector": r.sector,
            "scope1": round(r.scope1, 2),
            "scope2": round(r.scope2, 4),
            "production_output": round(r.production_output, 2),
            "emission_intensity": round(r.emission_intensity, 4),
            "regulatory_cap": r.regulatory_cap,
            "is_compliant": r.is_compliant,
            "compliance_status": "Compliant" if r.is_compliant else "Non-Compliant - Subject to NGT / CCTS Penalties",
            "credits_earned": round(r.credits_earned, 2),
            "recorded_at": r.recorded_at.isoformat()
        } for r in b2b_history]
    }), 200


# ==========================================
# 5. ANALYTICS & DYNAMIC MITIGATION ENGINE
# ==========================================

@routes_bp.route('/analytics/b2c/<int:result_id>', methods=['GET'])
@login_required
def get_b2c_analytics(result_id):
    """Retrieve formatted analytics data for a specific B2C result (lifestyle footprint)."""
    result = B2CResult.query.get_or_404(result_id)
    
    # Access Control Check
    if result.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "Access denied. You do not own this calculation."}), 403

    return jsonify({
        "result_id": result.id,
        "total_footprint": round(result.total_footprint, 2),
        "comparative_trend": {
            "user_actual": round(result.total_footprint, 2),
            "global_sustainable_average": 2000.0,  # 2 tonnes cap
            "national_indian_baseline": 1900.0      # 1.9 tonnes baseline
        },
        "categorical_breakdown": {
            "Diet & Food": round(result.diet_footprint, 2),
            "Transport": round(result.transport_footprint, 2),
            "Heating & Energy": round(result.energy_footprint, 2),
            "Household": 0.0,       # placeholder for UI consistency
            "Waste & Recycle": 0.0  # placeholder for UI consistency
        }
    }), 200


@routes_bp.route('/analytics/b2b/<int:result_id>', methods=['GET'])
@login_required
def get_b2b_analytics(result_id):
    """Retrieve formatted analytics data for a specific B2B result (industrial footprint)."""
    result = B2BResult.query.get_or_404(result_id)
    
    # Access Control Check
    if result.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "Access denied. You do not own this calculation."}), 403

    return jsonify({
        "result_id": result.id,
        "company_name": result.company_name,
        "sector": result.sector,
        "intensity_vs_cap": {
            "user_intensity": round(result.emission_intensity, 4),
            "regulatory_cap": result.regulatory_cap
        },
        "scopes_breakdown": {
            "Scope 1 (Direct)": round(result.scope1, 2),
            "Scope 2 (Indirect)": round(result.scope2, 4)
        }
    }), 200


@routes_bp.route('/calculator/b2c/<int:result_id>/mitigation', methods=['GET'])
@login_required
def get_b2c_mitigation(result_id):
    """Dynamically fetch easy, medium, and hard mitigation tasks based on highest B2C emission source."""
    result = B2CResult.query.get_or_404(result_id)
    
    if result.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "Access denied. You do not own this calculation."}), 403

    # Segment categories
    breakdown = {
        'Diet & Food': result.diet_footprint,
        'Transport': result.transport_footprint,
        'Heating & Energy': result.energy_footprint
    }
    
    # Identify highest emitting category
    highest_category = max(breakdown, key=breakdown.get)
    highest_emissions = breakdown[highest_category]

    strategies = {
        'Diet & Food': {
            "category": "Diet & Food",
            "easy": "Commit to \"Meatless Mondays\" to easily start cutting down red meat footprint.",
            "medium": "Shift to an entirely plant-based diet to drastically reduce methane output.",
            "hard": "Source 100% locally grown ingredients to eliminate global shipping emissions."
        },
        'Transport': {
            "category": "Transport",
            "easy": "Inflate tires correctly to optimize fuel efficiency and save 3-5% fuel.",
            "medium": "Carpool or use public transit 3x a week to reduce single-occupancy mileage.",
            "hard": "Transition fully to an Electric Vehicle (EV) to eliminate direct tailpipe emissions."
        },
        'Heating & Energy': {
            "category": "Heating & Energy",
            "easy": "Switch to low-energy LED bulbs to instantly cut lighting electricity usage.",
            "medium": "Install smart automated thermostats to optimize heating cycles.",
            "hard": "Install a rooftop solar array with grid-tied inverter to generate your own clean power."
        }
    }

    recommendation = strategies.get(highest_category)
    return jsonify({
        "result_id": result.id,
        "highest_emitting_category": highest_category,
        "highest_emitting_value": round(highest_emissions, 2),
        "recommendations": recommendation
    }), 200


@routes_bp.route('/calculator/b2b/<int:result_id>/mitigation', methods=['GET'])
@login_required
def get_b2b_mitigation(result_id):
    """Retrieve mitigation tasks for B2B industrial operations."""
    result = B2BResult.query.get_or_404(result_id)
    
    if result.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "Access denied. You do not own this calculation."}), 403

    return jsonify({
        "result_id": result.id,
        "company_name": result.company_name,
        "compliance_status": "Compliant" if result.is_compliant else "Non-Compliant - Subject to NGT / CCTS Penalties",
        "recommendations": {
            "category": "Industrial B2B",
            "easy": "Conduct an HVAC energy efficiency audit to identify heating and ventilation leakages.",
            "medium": "Implement waste heat recovery systems to recycle exhaust energy in boilers.",
            "hard": "Transition boilers to Green Hydrogen / Biomass fuel sources to completely decarbonize on-site combustion."
        }
    }), 200


@routes_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Retrieve top users sorted by total points for the leaderboard."""
    # Recalculate and sync cached points for all users first to keep it precise
    users = User.query.all()
    for u in users:
        u.update_points()
    db.session.commit()
    
    top_users = User.query.order_by(User.total_points.desc()).limit(10).all()
    return jsonify([{
        "username": u.username,
        "role": u.role,
        "total_points": u.total_points
    } for u in top_users]), 200


@routes_bp.route('/actions/log', methods=['POST'])
@login_required
def log_action():
    """Endpoint for common users to log a carbon-offsetting action."""
    if current_user.role != 'common':
        return jsonify({"error": "Access denied. Point actions are only available for common users."}), 403

    data = request.get_json() or {}
    category = data.get('category')
    action_name = data.get('action_name')
    co2_saved = data.get('co2_saved')
    points_earned = data.get('points_earned')

    if not category or not action_name or co2_saved is None or points_earned is None:
        return jsonify({"error": "Missing required fields: category, action_name, co2_saved, points_earned"}), 400

    if category not in ['transport', 'food', 'energy']:
        return jsonify({"error": "Invalid category. Must be 'transport', 'food', or 'energy'"}), 400

    try:
        co2_saved = float(co2_saved)
        points_earned = int(points_earned)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid data types for co2_saved or points_earned"}), 400

    action = LoggedAction(
        user_id=current_user.id,
        category=category,
        action_name=action_name,
        co2_saved=co2_saved,
        points_earned=points_earned
    )
    db.session.add(action)
    
    # Award points via the ledger
    add_points_to_ledger(current_user, f"LOG_ACTION_{category.upper()}", points_earned)
    db.session.commit()

    return jsonify({
        "message": "Action logged successfully",
        "points_earned": points_earned,
        "total_points": current_user.total_points,
        "action": {
            "id": action.id,
            "category": action.category,
            "action_name": action.action_name,
            "co2_saved": action.co2_saved,
            "points_earned": action.points_earned,
            "logged_at": action.logged_at.isoformat()
        }
    }), 201


@routes_bp.route('/actions/stats', methods=['GET'])
@login_required
def get_action_stats():
    """Retrieve action logging stats and carbon footprint metrics for the current user."""
    if current_user.role != 'common':
        return jsonify({"error": "Access denied. Stats are only available for common users."}), 403

    # Get baseline from the latest B2CResult
    last_b2c = B2CResult.query.filter_by(user_id=current_user.id).order_by(B2CResult.recorded_at.desc()).first()
    baseline = round(last_b2c.total_footprint, 2) if last_b2c else 0.0

    # Total offset logged
    total_offset = db.session.query(db.func.sum(LoggedAction.co2_saved)).filter_by(user_id=current_user.id).scalar() or 0.0
    total_offset = round(total_offset, 2)

    # Monthly progress (since start of current month)
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    monthly_offset = db.session.query(db.func.sum(LoggedAction.co2_saved)).filter(
        LoggedAction.user_id == current_user.id,
        LoggedAction.logged_at >= start_of_month
    ).scalar() or 0.0
    monthly_offset = round(monthly_offset, 2)

    # Milestones (e.g. 1 milestone for every 50 kg CO2 saved)
    milestones = int(total_offset // 50)

    # Get recent logged actions for display
    recent_actions = LoggedAction.query.filter_by(user_id=current_user.id).order_by(LoggedAction.logged_at.desc()).limit(5).all()
    actions_list = [{
        "id": a.id,
        "category": a.category,
        "action_name": a.action_name,
        "co2_saved": round(a.co2_saved, 2),
        "points_earned": a.points_earned,
        "logged_at": a.logged_at.isoformat()
    } for a in recent_actions]

    return jsonify({
        "baseline": baseline,
        "monthly_progress": monthly_offset,
        "total_offset": total_offset,
        "milestones": milestones,
        "recent_actions": actions_list
    }), 200


@routes_bp.route('/ai/coach', methods=['POST'])
@login_required
def ai_coach():
    """Endpoint for querying the Gemini AI Sustainability Coach."""
    global _GEMINI_ENDPOINT_CACHE
    data = request.get_json() or {}
    message = data.get('message')
    history = data.get('history', [])

    if not message or not message.strip():
        return jsonify({"error": "Message is required"}), 400

    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "Gemini API key is not configured on the server."}), 500

    # Format history and current message into Gemini contents format
    # Turn structure in history is: [{"role": "user"|"model", "text": "..."}]
    contents = []
    for turn in history:
        r = turn.get('role')
        txt = turn.get('text')
        if r in ['user', 'model'] and txt:
            contents.append({
                "role": r,
                "parts": [{"text": txt}]
            })
    
    # Append current message
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are a friendly, inspiring, and knowledgeable AI Sustainability Coach. "
                    "Your goal is to help the user reduce their carbon footprint, explain environmental science simply, "
                    "and provide personalized, actionable tips for green living (transport, food, energy). "
                    "Always refer to the user's role if helpful, and keep formatting clean using markdown. "
                    "Keep answers relatively concise, encouraging, and focused on practical tips."
                )
            }]
        }
    }

    # Attempt to call Gemini API, trying different model and API version configurations
    base_candidates = [
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    ]

    ordered_candidates = []
    if _GEMINI_ENDPOINT_CACHE and _GEMINI_ENDPOINT_CACHE in base_candidates:
        ordered_candidates.append(_GEMINI_ENDPOINT_CACHE)
    for c in base_candidates:
        if c not in ordered_candidates:
            ordered_candidates.append(c)

    success = False
    reply_text = ""
    last_error_msg = "Unknown error"
    last_status_code = 500

    for base_url in ordered_candidates:
        url = f"{base_url}?key={api_key}"
        try:
            # Short timeout per request to fail fast during discovery
            timeout_val = 10 if base_url != _GEMINI_ENDPOINT_CACHE else 30
            response = requests.post(url, headers=headers, json=payload, timeout=timeout_val)
            
            if response.status_code == 200:
                response_json = response.json()
                candidates_list = response_json.get('candidates', [])
                if candidates_list:
                    reply_text = candidates_list[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    if reply_text:
                        _GEMINI_ENDPOINT_CACHE = base_url  # Cache successful URL
                        success = True
                        break
                last_error_msg = "Empty or malformed response from Gemini."
                last_status_code = 500
            else:
                try:
                    res_json = response.json()
                    last_error_msg = res_json.get('error', {}).get('message', 'Failed to communicate with Gemini API')
                except Exception:
                    last_error_msg = response.text or 'Failed to communicate with Gemini API'
                last_status_code = response.status_code
        except requests.exceptions.RequestException as e:
            last_error_msg = f"Network error when calling Gemini API: {str(e)}"
            last_status_code = 500

    if not success:
        return jsonify({"error": f"Gemini API error: {last_error_msg}"}), last_status_code

    return jsonify({
        "reply": reply_text
    }), 200


