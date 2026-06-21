import unittest
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify
from database import db
from models import User, UserPoints, Blog, Comment, Like, Article, ArticleRead
from auth import auth_bp, login_manager, add_points_to_ledger
from routes import routes_bp

class TestPhase2(unittest.TestCase):
    def setUp(self):
        """Set up test Flask application with SQLite in-memory database."""
        self.app = Flask(__name__)
        
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)
        login_manager.init_app(self.app)
        
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')
        self.app.register_blueprint(routes_bp, url_prefix='/api')

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.client = self.app.test_client()

        # Seed initial data: Users
        self.common_user = User(username="common", email="common@test.com", role="common")
        self.common_user.set_password("pass")
        
        self.admin_user = User(username="admin", email="admin@test.com", role="admin")
        self.admin_user.set_password("pass")
        
        db.session.add_all([self.common_user, self.admin_user])
        db.session.commit()

        # Seed initial data: Articles
        self.article1 = Article(title="Save Water", content="Water is life. Save it.")
        self.article2 = Article(title="Solar Energy", content="Solar panels harvest sun rays.")
        db.session.add_all([self.article1, self.article2])
        db.session.commit()

    def tearDown(self):
        """Clean up database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_article_reading_timer_verification(self):
        """Test that user cannot farm points without reading for at least 30 seconds."""
        # 1. Login as common user
        self.client.post('/api/auth/login', json={"username": "common", "password": "pass"})

        # 2. Fetch list of articles
        res = self.client.get('/api/articles')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 2)

        # 3. Start reading Article 1
        res = self.client.post(f'/api/articles/{self.article1.id}/start-read')
        self.assertEqual(res.status_code, 201)
        self.assertIn("Reading session started", res.get_json()['message'])

        # 4. Attempt to complete read immediately (under 30s) -> expect failure
        res = self.client.post(f'/api/articles/{self.article1.id}/complete-read')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Minimum reading time not met", res.get_json()['error'])

        # 5. Simulate 35 seconds passing by adjusting started_at in database
        read_record = ArticleRead.query.filter_by(
            user_id=self.common_user.id,
            article_id=self.article1.id,
            completed_at=None
        ).first()
        self.assertIsNotNone(read_record)
        read_record.started_at = datetime.now(timezone.utc) - timedelta(seconds=35)
        db.session.commit()

        # 6. Complete read now -> expect success and +10 points
        res = self.client.post(f'/api/articles/{self.article1.id}/complete-read')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['points_earned'], 10)
        self.assertEqual(res.get_json()['total_points'], 10)

        # Verify points cache sync on the user model
        user = User.query.filter_by(username="common").first()
        self.assertEqual(user.total_points, 10)

        # 7. Attempt completing it again when no session is active -> expect 400
        res = self.client.post(f'/api/articles/{self.article1.id}/complete-read')
        self.assertEqual(res.status_code, 400)

    def test_community_blogging_and_admin_workflow(self):
        """Test blog posting, admin approval list, approval (+100 points), comments (+5 points), and likes."""
        # 1. Draft blog as common user
        self.client.post('/api/auth/login', json={"username": "common", "password": "pass"})
        
        res = self.client.post('/api/blogs', json={
            "title": "My Green Plan",
            "content": "Use less plastic, carry cloth bags."
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['blog']['status'], 'pending')
        blog_id = res.get_json()['blog']['id']

        # 2. Check that it is NOT in public feed
        res = self.client.get('/api/blogs')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 0) # Empty feed

        # Logout user
        self.client.post('/api/auth/logout')

        # 3. Check access control for admin endpoints (Common user / Anonymous should be blocked)
        res = self.client.get('/api/admin/blogs/pending')
        self.assertEqual(res.status_code, 401) # Unauthorized

        # Login as Admin
        self.client.post('/api/auth/login', json={"username": "admin", "password": "pass"})
        
        # Admin gets pending blog list
        res = self.client.get('/api/admin/blogs/pending')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 1)
        self.assertEqual(res.get_json()[0]['title'], "My Green Plan")

        # 4. Admin approves the blog
        res = self.client.post(f'/api/admin/blogs/{blog_id}/approve')
        self.assertEqual(res.status_code, 200)
        self.assertIn("approved and published", res.get_json()['message'])
        self.assertEqual(res.get_json()['author_points_updated'], 100)

        # 5. Check public feed again (now approved)
        res = self.client.get('/api/blogs')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 1)
        self.assertEqual(res.get_json()[0]['title'], "My Green Plan")

        # Logout Admin, login as Common user
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json={"username": "common", "password": "pass"})

        # Check common user has 100 points
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.get_json()['total_points'], 100)

        # 6. User Comments on blog -> gets +5 points
        res = self.client.post(f'/api/blogs/{blog_id}/comments', json={"content": "Inspiring post!"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['points_earned'], 5)
        self.assertEqual(res.get_json()['total_points'], 105)

        # 7. User Likes/Unlikes blog
        res = self.client.post(f'/api/blogs/{blog_id}/like')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['liked'])
        self.assertEqual(res.get_json()['likes_count'], 1)

        res = self.client.post(f'/api/blogs/{blog_id}/like')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()['liked'])
        self.assertEqual(res.get_json()['likes_count'], 0)

    def test_admin_reject_blog_workflow(self):
        """Test admin rejecting a blog draft."""
        # 1. Draft blog as common user
        self.client.post('/api/auth/login', json={"username": "common", "password": "pass"})
        res = self.client.post('/api/blogs', json={
            "title": "Spam Blog",
            "content": "Adware content here."
        })
        blog_id = res.get_json()['blog']['id']
        self.client.post('/api/auth/logout')

        # 2. Admin logs in and rejects it
        self.client.post('/api/auth/login', json={"username": "admin", "password": "pass"})
        res = self.client.post(f'/api/admin/blogs/{blog_id}/reject')
        self.assertEqual(res.status_code, 200)
        self.assertIn("rejected successfully", res.get_json()['message'])

        # Check blog is not approved
        blog = Blog.query.get(blog_id)
        self.assertEqual(blog.status, 'rejected')

        # Check author points not updated
        author = User.query.filter_by(username="common").first()
        self.assertEqual(author.total_points, 0)

if __name__ == '__main__':
    unittest.main()
