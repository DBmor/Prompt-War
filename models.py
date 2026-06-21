from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

def get_utc_now():
    """Helper to return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

class User(db.Model, UserMixin):
    """User model for Common Users, Industrial Owners, and Admins."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='common')  # 'common', 'industrial', 'admin'
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    total_points = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    points_ledger = db.relationship('UserPoints', backref='user', lazy=True, cascade="all, delete-orphan")
    blogs = db.relationship('Blog', backref='author', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='user', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='user', lazy=True, cascade="all, delete-orphan")
    article_reads = db.relationship('ArticleRead', backref='user', lazy=True, cascade="all, delete-orphan")
    b2c_results = db.relationship('B2CResult', backref='user', lazy=True, cascade="all, delete-orphan")
    b2b_results = db.relationship('B2BResult', backref='user', lazy=True, cascade="all, delete-orphan")
    logged_actions = db.relationship('LoggedAction', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Hashes password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies the hashed password."""
        return check_password_hash(self.password_hash, password)

    def update_points(self):
        """Recalculates total points from the ledger and updates the cached total_points."""
        total = sum(ledger.points_earned for ledger in self.points_ledger)
        self.total_points = max(0, total)
        return self.total_points

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class UserPoints(db.Model):
    """Ledger table to track all points earned or spent to prevent manipulation."""
    __tablename__ = 'user_points'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # e.g., 'READ_ARTICLE', 'POST_BLOG', 'TAKE_ASSESSMENT', 'LEAVE_COMMENT'
    points_earned = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<UserPoints user_id={self.user_id} action={self.action_type} points={self.points_earned}>"


class Blog(db.Model):
    """Community blogging table supporting drafts, approval workflow, and rich markdown text."""
    __tablename__ = 'blogs'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown text
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    moderated_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    comments = db.relationship('Comment', backref='blog', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='blog', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Blog '{self.title}' by user_id={self.author_id} status={self.status}>"


class Comment(db.Model):
    """Comment model for blog posts."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blogs.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<Comment user_id={self.user_id} blog_id={self.blog_id}>"


class Like(db.Model):
    """Like model for blog posts, unique per user and blog."""
    __tablename__ = 'likes'
    __table_args__ = (
        db.UniqueConstraint('blog_id', 'user_id', name='unique_blog_user_like'),
    )

    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blogs.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<Like user_id={self.user_id} blog_id={self.blog_id}>"


class Article(db.Model):
    """Awareness article model."""
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    # Relationships
    reads = db.relationship('ArticleRead', backref='article', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Article '{self.title}'>"


class ArticleRead(db.Model):
    """Tracks scroll depth / reading time to prevent points farming."""
    __tablename__ = 'article_reads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)
    points_awarded = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<ArticleRead user_id={self.user_id} article_id={self.article_id} awarded={self.points_awarded}>"


class B2CResult(db.Model):
    """Calculated carbon footprint results for common users."""
    __tablename__ = 'b2c_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    diet_footprint = db.Column(db.Float, nullable=False, default=0.0)      # kg CO2e
    transport_footprint = db.Column(db.Float, nullable=False, default=0.0) # kg CO2e
    energy_footprint = db.Column(db.Float, nullable=False, default=0.0)    # kg CO2e
    total_footprint = db.Column(db.Float, nullable=False, default=0.0)     # kg CO2e
    recorded_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<B2CResult user_id={self.user_id} total={self.total_footprint}>"


class B2BResult(db.Model):
    """Calculated regulatory emission metrics for industrial owners (India CCTS context)."""
    __tablename__ = 'b2b_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    sector = db.Column(db.String(50), nullable=False)             # e.g., 'Steel', 'Cement'
    scope1 = db.Column(db.Float, nullable=False, default=0.0)      # tonnes CO2e
    scope2 = db.Column(db.Float, nullable=False, default=0.0)      # tonnes CO2e
    production_output = db.Column(db.Float, nullable=False, default=1.0) # e.g., tonnes of output
    emission_intensity = db.Column(db.Float, nullable=False, default=0.0) # (Scope1 + Scope2) / production_output
    regulatory_cap = db.Column(db.Float, nullable=False, default=0.0)     # cap limit intensity
    is_compliant = db.Column(db.Boolean, nullable=False, default=True)
    credits_earned = db.Column(db.Float, nullable=False, default=0.0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<B2BResult user_id={self.user_id} compliant={self.is_compliant} intensity={self.emission_intensity}>"


class LoggedAction(db.Model):
    """Tracks carbon offset actions logged by common users."""
    __tablename__ = 'logged_actions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False)      # 'transport', 'food', 'energy'
    action_name = db.Column(db.String(100), nullable=False)
    co2_saved = db.Column(db.Float, nullable=False)          # kg CO2e
    points_earned = db.Column(db.Integer, nullable=False)
    logged_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)

    def __repr__(self):
        return f"<LoggedAction user_id={self.user_id} category={self.category} name='{self.action_name}' co2={self.co2_saved}>"
