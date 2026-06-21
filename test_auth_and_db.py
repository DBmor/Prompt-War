import unittest
from flask import Flask, jsonify
from flask_login import login_required
from database import db
from config import Config
from models import User, UserPoints, Blog, Comment, Like, Article, ArticleRead, B2CResult, B2BResult
from auth import auth_bp, login_manager, role_required, add_points_to_ledger

class TestAuthAndDB(unittest.TestCase):
    def setUp(self):
        """Set up test Flask application with SQLite in-memory database."""
        self.app = Flask(__name__)
        
        # Configure app for testing with in-memory database
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        # Initialize DB and LoginManager
        db.init_app(self.app)
        login_manager.init_app(self.app)
        
        # Register auth blueprint
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')

        # Add test routes to test decorators
        @self.app.route('/test/common-only')
        @role_required('common')
        def common_only_route():
            return jsonify({"status": "ok"}), 200

        @self.app.route('/test/industrial-only')
        @role_required('industrial')
        def industrial_only_route():
            return jsonify({"status": "ok"}), 200

        @self.app.route('/test/admin-only')
        @role_required('admin')
        def admin_only_route():
            return jsonify({"status": "ok"}), 200

        @self.app.route('/test/any-user')
        @role_required('common', 'industrial')
        def any_user_route():
            return jsonify({"status": "ok"}), 200

        # Create tables within app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up database and app context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation_and_auth(self):
        """Test user registration, login, logout, and password hashing."""
        # 1. Register users via post request
        res = self.client.post('/api/auth/register', json={
            "username": "testcommon",
            "email": "common@test.com",
            "password": "Password123",
            "role": "common"
        })
        self.assertEqual(res.status_code, 210)
        self.assertIn("User registered successfully", res.get_json()['message'])

        res = self.client.post('/api/auth/register', json={
            "username": "testadmin",
            "email": "admin@test.com",
            "password": "AdminPassword",
            "role": "admin"
        })
        self.assertEqual(res.status_code, 210)

        # 2. Test registration validations
        # Duplicate check
        res = self.client.post('/api/auth/register', json={
            "username": "testcommon",
            "email": "other@test.com",
            "password": "Password123",
            "role": "common"
        })
        self.assertEqual(res.status_code, 400)

        # Invalid role
        res = self.client.post('/api/auth/register', json={
            "username": "tester",
            "email": "tester@test.com",
            "password": "Password123",
            "role": "superadmin"
        })
        self.assertEqual(res.status_code, 400)

        # 3. Test password hashing
        user = User.query.filter_by(username="testcommon").first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "Password123")
        self.assertTrue(user.check_password("Password123"))
        self.assertFalse(user.check_password("WrongPassword"))

        # 4. Test login routes
        # Fail login
        res = self.client.post('/api/auth/login', json={
            "username": "testcommon",
            "password": "wrongpassword"
        })
        self.assertEqual(res.status_code, 401)

        # Success login
        res = self.client.post('/api/auth/login', json={
            "username": "testcommon",
            "password": "Password123"
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("Login successful", res.get_json()['message'])

        # Test profile fetch
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['role'], 'common')

        # Logout
        res = self.client.post('/api/auth/logout')
        self.assertEqual(res.status_code, 200)

        # Profile fetch after logout
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)

    def test_role_based_authorization(self):
        """Test that @role_required decorator functions properly for different tiers."""
        # Setup users
        common = User(username="common", email="common@test.com", role="common")
        common.set_password("pass")
        admin = User(username="admin", email="admin@test.com", role="admin")
        admin.set_password("pass")
        industrial = User(username="industrial", email="ind@test.com", role="industrial")
        industrial.set_password("pass")

        db.session.add_all([common, admin, industrial])
        db.session.commit()

        # 1. Anonymous Access (expect 401)
        self.assertEqual(self.client.get('/test/common-only').status_code, 401)
        self.assertEqual(self.client.get('/test/industrial-only').status_code, 401)
        self.assertEqual(self.client.get('/test/admin-only').status_code, 401)

        # 2. Common User Access
        self.client.post('/api/auth/login', json={"username": "common", "password": "pass"})
        self.assertEqual(self.client.get('/test/common-only').status_code, 200)
        self.assertEqual(self.client.get('/test/industrial-only').status_code, 403)
        self.assertEqual(self.client.get('/test/admin-only').status_code, 403)
        self.assertEqual(self.client.get('/test/any-user').status_code, 200)
        self.client.post('/api/auth/logout')

        # 3. Industrial Owner Access
        self.client.post('/api/auth/login', json={"username": "industrial", "password": "pass"})
        self.assertEqual(self.client.get('/test/common-only').status_code, 403)
        self.assertEqual(self.client.get('/test/industrial-only').status_code, 200)
        self.assertEqual(self.client.get('/test/admin-only').status_code, 403)
        self.assertEqual(self.client.get('/test/any-user').status_code, 200)
        self.client.post('/api/auth/logout')

        # 4. Admin Access
        self.client.post('/api/auth/login', json={"username": "admin", "password": "pass"})
        self.assertEqual(self.client.get('/test/common-only').status_code, 403)
        self.assertEqual(self.client.get('/test/industrial-only').status_code, 403)
        self.assertEqual(self.client.get('/test/admin-only').status_code, 200)
        self.assertEqual(self.client.get('/test/any-user').status_code, 403)
        self.client.post('/api/auth/logout')

    def test_points_ledger_and_gamification(self):
        """Test points ledger operations, and points tallying."""
        user = User(username="player", email="player@test.com", role="common")
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

        # Check starting points
        self.assertEqual(user.total_points, 0)

        # 1. Earn points for reading
        add_points_to_ledger(user, 'READ_ARTICLE', 10)
        self.assertEqual(user.total_points, 10)

        # 2. Earn points for calculator
        add_points_to_ledger(user, 'TAKE_ASSESSMENT', 50)
        self.assertEqual(user.total_points, 60)

        # Verify database record count
        records = UserPoints.query.filter_by(user_id=user.id).all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].points_earned, 10)
        self.assertEqual(records[1].points_earned, 50)

    def test_carbon_calculators_and_blogs(self):
        """Test other models (Blog, Article, ArticleRead, B2CResult, B2BResult)."""
        user = User(username="author", email="author@test.com", role="common")
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

        # 1. Blog, Comment, Like
        blog = Blog(author_id=user.id, title="How to save energy", content="# Save Energy\nReduce heat.", status="pending")
        db.session.add(blog)
        db.session.commit()

        comment = Comment(blog_id=blog.id, user_id=user.id, content="Great tips!")
        like = Like(blog_id=blog.id, user_id=user.id)
        db.session.add_all([comment, like])
        db.session.commit()

        self.assertEqual(len(blog.comments), 1)
        self.assertEqual(len(blog.likes), 1)
        self.assertEqual(blog.comments[0].content, "Great tips!")

        # Double liking constraint check
        duplicate_like = Like(blog_id=blog.id, user_id=user.id)
        db.session.add(duplicate_like)
        with self.assertRaises(Exception):
            db.session.commit()
        db.session.rollback()

        # 2. Articles & Read times
        article = Article(title="Awareness 101", content="Article content goes here.")
        db.session.add(article)
        db.session.commit()

        read_record = ArticleRead(user_id=user.id, article_id=article.id)
        db.session.add(read_record)
        db.session.commit()
        self.assertFalse(read_record.points_awarded)

        # 3. B2C Calculations
        b2c = B2CResult(user_id=user.id, diet_footprint=120.5, transport_footprint=450.0, energy_footprint=300.2, total_footprint=870.7)
        db.session.add(b2c)
        db.session.commit()
        self.assertEqual(len(user.b2c_results), 1)
        self.assertAlmostEqual(user.b2c_results[0].total_footprint, 870.7)

        # 4. B2B Calculations
        b2b = B2BResult(
            user_id=user.id,
            company_name="Tech Steel Ltd",
            sector="Steel",
            scope1=500.0,
            scope2=150.0,
            production_output=200.0,
            emission_intensity=3.25,
            regulatory_cap=4.0,
            is_compliant=True,
            credits_earned=15.0
        )
        db.session.add(b2b)
        db.session.commit()
        self.assertEqual(len(user.b2b_results), 1)
        self.assertTrue(user.b2b_results[0].is_compliant)
        self.assertEqual(user.b2b_results[0].emission_intensity, 3.25)

if __name__ == '__main__':
    unittest.main()
