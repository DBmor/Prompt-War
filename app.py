import os
from flask import Flask
from config import Config
from database import db
from auth import auth_bp, login_manager
from routes import routes_bp

def create_app():
    """Application factory for Carbon Footprint App."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(routes_bp, url_prefix='/api')

    # Serve the Single Page Application index file
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Create tables and seed data automatically on startup
    with app.app_context():
        db.create_all()
        
        # Seed initial articles if they are empty
        from models import Article, User
        if not Article.query.first():
            art1 = Article(
                title="Understanding Carbon Footprints & Greenhouse Gases",
                content="Greenhouse gases (GHGs) trap heat in the atmosphere, warming the planet. Carbon dioxide (CO2) from fossil fuel combustion is the primary driver of climate change. A personal carbon footprint comprises direct emissions (e.g., fuel used for transport) and indirect emissions (e.g., electricity consumed). Practical ways to cut down include transitioning to electric vehicles, shifting to energy-efficient LED lightbulbs, reducing consumption of red meat/dairy, and switching to solar power."
            )
            art2 = Article(
                title="The Shift to Solar Energy & Home Efficiency",
                content="Residential heating and cooling accounts for a significant slice of personal emissions. Switching standard home lights to LEDs saves electricity and cuts coal footprint in grids. Smart automated thermostats prevent excessive cooling when rooms are vacant. The ultimate household upgrade is rooftop solar: grid-tied inverters feed excess solar power back into the public grid, net-metering the carbon footprint down to zero."
            )
            art3 = Article(
                title="India's CCTS Framework & Industrial De-carbonization",
                content="India's Carbon Credit Trading Scheme (CCTS), governed by the Bureau of Energy Efficiency (BEE), sets sector-wide Carbon Emission Intensity targets. Under this compliance cap structure, plants in heavy sectors like Steel and Cement are monitored by their CO2 intensity per metric tonne of output. Enterprises exceeding the sector caps face severe NGT/CCTS penalties, while plants that beat targets earn Carbon Credit Certificates (CCCs) that can be traded."
            )
            db.session.add_all([art1, art2, art3])
            db.session.commit()

        # Seed an admin user if it doesn't exist for testing moderation
        if not User.query.filter_by(role='admin').first():
            admin_user = User(username='admin', email='admin@carbon.com', role='admin')
            admin_user.set_password('Admin123!')
            db.session.add(admin_user)
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
