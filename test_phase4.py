import unittest
from flask import Flask
from database import db
from models import User, B2CResult, B2BResult
from auth import auth_bp, login_manager
from routes import routes_bp

class TestPhase4(unittest.TestCase):
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

        # Seed test users
        self.owner = User(username="owner", email="owner@test.com", role="common")
        self.owner.set_password("pass")
        
        self.non_owner = User(username="stranger", email="stranger@test.com", role="common")
        self.non_owner.set_password("pass")

        self.admin = User(username="admin", email="admin@test.com", role="admin")
        self.admin.set_password("pass")
        
        db.session.add_all([self.owner, self.non_owner, self.admin])
        db.session.commit()

        # Seed B2C and B2B results owned by self.owner
        self.b2c_transport_highest = B2CResult(
            user_id=self.owner.id,
            diet_footprint=100.0,
            transport_footprint=500.0,
            energy_footprint=200.0,
            total_footprint=800.0
        )
        self.b2c_diet_highest = B2CResult(
            user_id=self.owner.id,
            diet_footprint=1000.0,
            transport_footprint=150.0,
            energy_footprint=300.0,
            total_footprint=1450.0
        )
        self.b2c_energy_highest = B2CResult(
            user_id=self.owner.id,
            diet_footprint=100.0,
            transport_footprint=200.0,
            energy_footprint=900.0,
            total_footprint=1200.0
        )

        self.b2b_cement = B2BResult(
            user_id=self.owner.id,
            company_name="Alpha Cement",
            sector="Cement",
            scope1=450.0,
            scope2=80.0,
            production_output=1000.0,
            emission_intensity=0.53,
            regulatory_cap=0.65,
            is_compliant=True,
            credits_earned=120.0
        )

        db.session.add_all([
            self.b2c_transport_highest, 
            self.b2c_diet_highest, 
            self.b2c_energy_highest,
            self.b2b_cement
        ])
        db.session.commit()

    def tearDown(self):
        """Clean up database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_b2c_analytics_access_control_and_structure(self):
        """Test B2C analytics structure and user permissions."""
        # 1. Anonymous Access -> Blocked
        res = self.client.get(f'/api/analytics/b2c/{self.b2c_transport_highest.id}')
        self.assertEqual(res.status_code, 401)

        # 2. Non-owner Access -> 403 Forbidden
        self.client.post('/api/auth/login', json={"username": "stranger", "password": "pass"})
        res = self.client.get(f'/api/analytics/b2c/{self.b2c_transport_highest.id}')
        self.assertEqual(res.status_code, 403)
        self.client.post('/api/auth/logout')

        # 3. Owner Access -> 200 OK
        self.client.post('/api/auth/login', json={"username": "owner", "password": "pass"})
        res = self.client.get(f'/api/analytics/b2c/{self.b2c_transport_highest.id}')
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertEqual(data['total_footprint'], 800.0)
        self.assertEqual(data['comparative_trend']['user_actual'], 800.0)
        self.assertEqual(data['comparative_trend']['global_sustainable_average'], 2000.0)
        self.assertEqual(data['comparative_trend']['national_indian_baseline'], 1900.0)
        self.assertEqual(data['categorical_breakdown']['Transport'], 500.0)
        self.client.post('/api/auth/logout')

        # 4. Admin Access -> 200 OK
        self.client.post('/api/auth/login', json={"username": "admin", "password": "pass"})
        res = self.client.get(f'/api/analytics/b2c/{self.b2c_transport_highest.id}')
        self.assertEqual(res.status_code, 200)

    def test_b2b_analytics_structure(self):
        """Test B2B analytics response formats."""
        self.client.post('/api/auth/login', json={"username": "owner", "password": "pass"})
        res = self.client.get(f'/api/analytics/b2b/{self.b2b_cement.id}')
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertEqual(data['company_name'], "Alpha Cement")
        self.assertEqual(data['sector'], "Cement")
        self.assertEqual(data['intensity_vs_cap']['user_intensity'], 0.53)
        self.assertEqual(data['intensity_vs_cap']['regulatory_cap'], 0.65)
        self.assertEqual(data['scopes_breakdown']['Scope 1 (Direct)'], 450.0)
        self.assertEqual(data['scopes_breakdown']['Scope 2 (Indirect)'], 80.0)

    def test_b2c_dynamic_mitigation_engine(self):
        """Test dynamic mitigation recommendations depend on highest emitter."""
        self.client.post('/api/auth/login', json={"username": "owner", "password": "pass"})

        # Case A: Transport is highest emitter
        res = self.client.get(f'/api/calculator/b2c/{self.b2c_transport_highest.id}/mitigation')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['highest_emitting_category'], 'Transport')
        self.assertIn("Electric Vehicle", data['recommendations']['hard'])

        # Case B: Diet is highest emitter
        res = self.client.get(f'/api/calculator/b2c/{self.b2c_diet_highest.id}/mitigation')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['highest_emitting_category'], 'Diet & Food')
        self.assertIn("plant-based diet", data['recommendations']['medium'])

        # Case C: Energy is highest emitter
        res = self.client.get(f'/api/calculator/b2c/{self.b2c_energy_highest.id}/mitigation')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['highest_emitting_category'], 'Heating & Energy')
        self.assertIn("solar array", data['recommendations']['hard'])

    def test_b2b_mitigation_suggestions(self):
        """Test B2B mitigation endpoints return industrial compliance suggestions."""
        self.client.post('/api/auth/login', json={"username": "owner", "password": "pass"})
        res = self.client.get(f'/api/calculator/b2b/{self.b2b_cement.id}/mitigation')
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertEqual(data['company_name'], "Alpha Cement")
        self.assertEqual(data['recommendations']['category'], "Industrial B2B")
        self.assertIn("Green Hydrogen", data['recommendations']['hard'])

if __name__ == '__main__':
    unittest.main()
