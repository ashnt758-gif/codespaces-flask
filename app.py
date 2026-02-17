import os
from flask import Flask
from flask_login import LoginManager
from config import DevelopmentConfig
from models import db, User
from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp
import pytz
from datetime import datetime

def create_app(config_class=DevelopmentConfig):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register custom Jinja2 filters
    @app.template_filter('basename')
    def basename_filter(path):
        """Get basename of a file path"""
        return os.path.basename(path)
    
    @app.template_filter('to_ist')
    def to_ist_filter(dt):
        """Convert datetime to Asia/Kolkata timezone"""
        if dt is None:
            return ''
        
        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to Asia/Kolkata
        ist = pytz.timezone('Asia/Kolkata')
        return dt.astimezone(ist)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
