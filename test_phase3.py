import unittest
from flask import Flask
from database import db
from models import User, B2CResult, B2BResult
from auth import auth_bp, login_manager
from routes import routes_bp

class TestPhase3(unittest.TestCase):
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

        # Seed test user
        self.user = User(username="user", email="user@test.com", role="common")
        self.user.set_password("pass")
        db.session.add(self.user)
        db.session.commit()

        # Login user
        self.client.post('/api/auth/login', json={"username": "user", "password": "pass"})

    def tearDown(self):
        """Clean up database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_b2c_lifestyle_calculator(self):
        """Test B2C calculator arithmetic, database logging, and points accumulation."""
        payload = {
            "red_meat": 1.5,
            "dairy": 2.0,
            "local_food": 3.0,
            "other_food": 1.0,
            "petrol_diesel_km": 10000.0,
            "ev_km": 5000.0,
            "public_transit_km": 2000.0,
            "monthly_kwh": 250.0
        }
        res = self.client.post('/api/calculator/b2c', json=payload)
        self.assertEqual(res.status_code, 201)
        
        data = res.get_json()
        self.assertEqual(data['points_earned'], 50)
        self.assertEqual(data['total_points'], 50)
        
        result = data['result']
        # Diet footprint verification
        # ((1.5 * 27.0) + (2.0 * 3.2) + (3.0 * 0.5) + (1.0 * 2.5)) * 52
        # (40.5 + 6.4 + 1.5 + 2.5) * 52 = 50.9 * 52 = 2646.8
        self.assertAlmostEqual(result['diet_footprint'], 2646.8)
        
        # Transport footprint verification
        # (10000 * 0.18) + (5000 * 0.05) + (2000 * 0.03)
        # 1800 + 250 + 60 = 2110.0
        self.assertAlmostEqual(result['transport_footprint'], 2110.0)
        
        # Energy footprint verification
        # (250 * 12) * 0.82 = 2460.0
        self.assertAlmostEqual(result['energy_footprint'], 2460.0)
        
        # Total footprint verification
        # 2646.8 + 2110.0 + 2460.0 = 7216.8
        self.assertAlmostEqual(result['total_footprint'], 7216.8)

        # Verify DB entry exists
        db_result = B2CResult.query.first()
        self.assertIsNotNone(db_result)
        self.assertEqual(db_result.user_id, self.user.id)
        self.assertAlmostEqual(db_result.total_footprint, 7216.8)

    def test_b2b_industrial_calculator_compliant(self):
        """Test B2B compliance metrics for a compliant Cement plant."""
        payload = {
            "company_name": "Eco Cement Plant",
            "sector": "Cement",
            "production_output": 1000.0,
            "coal_tonnes": 100.0,
            "diesel_liters": 5000.0,
            "process_emissions": 50.0,
            "grid_kwh": 100000.0
        }
        res = self.client.post('/api/calculator/b2b', json=payload)
        self.assertEqual(res.status_code, 201)
        
        data = res.get_json()
        self.assertEqual(data['points_earned'], 50)
        
        result = data['result']
        # Scope 1: (100 * 2.42) + (5000 * 0.00268) + 50 = 242 + 13.4 + 50 = 305.4
        self.assertAlmostEqual(result['scope1'], 305.4)
        
        # Scope 2: 100000 * 0.00082 = 82.0
        self.assertAlmostEqual(result['scope2'], 82.0)
        
        # Total emissions: 305.4 + 82.0 = 387.4
        self.assertAlmostEqual(result['total_emissions'], 387.4)
        
        # Intensity: 387.4 / 1000 = 0.3874
        self.assertAlmostEqual(result['emission_intensity'], 0.3874)
        
        # Sector regulatory cap (Cement = 0.65)
        self.assertEqual(result['regulatory_cap'], 0.65)
        
        # Compliance state check
        self.assertTrue(result['is_compliant'])
        self.assertEqual(result['compliance_status'], "Compliant")
        
        # Credits earned: (0.65 - 0.3874) * 1000 = 262.6
        self.assertAlmostEqual(result['credits_earned'], 262.6)

        # Verify DB entry
        db_result = B2BResult.query.first()
        self.assertIsNotNone(db_result)
        self.assertEqual(db_result.is_compliant, True)
        self.assertAlmostEqual(db_result.credits_earned, 262.6)

    def test_b2b_industrial_calculator_non_compliant(self):
        """Test B2B compliance metrics for a non-compliant Steel plant."""
        payload = {
            "company_name": "Heavy Steel Foundry",
            "sector": "Steel",
            "production_output": 500.0,
            "coal_tonnes": 500.0,
            "diesel_liters": 10000.0,
            "process_emissions": 100.0,
            "grid_kwh": 200000.0
        }
        res = self.client.post('/api/calculator/b2b', json=payload)
        self.assertEqual(res.status_code, 201)
        
        data = res.get_json()
        result = data['result']
        
        # Scope 1: (500 * 2.42) + (10000 * 0.00268) + 100 = 1210 + 26.8 + 100 = 1336.8
        self.assertAlmostEqual(result['scope1'], 1336.8)
        
        # Scope 2: 200000 * 0.00082 = 164.0
        self.assertAlmostEqual(result['scope2'], 164.0)
        
        # Total emissions: 1336.8 + 164.0 = 1500.8
        self.assertAlmostEqual(result['total_emissions'], 1500.8)
        
        # Intensity: 1500.8 / 500 = 3.0016
        self.assertAlmostEqual(result['emission_intensity'], 3.0016)
        
        # Sector cap (Steel = 2.1)
        self.assertEqual(result['regulatory_cap'], 2.1)
        
        # Compliance state check: Steel intensity 3.0016 > cap 2.1 -> Non-compliant
        self.assertFalse(result['is_compliant'])
        self.assertEqual(result['compliance_status'], "Non-Compliant - Subject to NGT / CCTS Penalties")
        self.assertEqual(result['credits_earned'], 0.0)

    def test_calculator_history(self):
        """Test history retrieval endpoint."""
        # Submit 1 B2C and 1 B2B assessment
        self.client.post('/api/calculator/b2c', json={"monthly_kwh": 100.0})
        self.client.post('/api/calculator/b2b', json={
            "company_name": "Small Plant",
            "sector": "Other",
            "production_output": 10.0,
            "coal_tonnes": 2.0
        })

        # Fetch history
        res = self.client.get('/api/calculator/history')
        self.assertEqual(res.status_code, 200)
        
        data = res.get_json()
        self.assertEqual(len(data['b2c']), 1)
        self.assertEqual(len(data['b2b']), 1)
        self.assertEqual(data['b2b'][0]['company_name'], "Small Plant")

if __name__ == '__main__':
    unittest.main()
