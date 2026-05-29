from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.expenses import expenses_bp
    from app.routes.invoices import invoices_bp
    from app.routes.chat import chat_bp
    from app.routes.budgets import budgets_bp
    from app.routes.reports import reports_bp
    from app.routes.analyzer import analyzer_bp
    from app.routes.forecasting import forecasting_bp
    from app.routes.settings import settings_bp
    from app.routes.insights import insights_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(analyzer_bp)
    app.register_blueprint(forecasting_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(insights_bp)

    with app.app_context():
        db.create_all()
        from app.services.seed_service import seed_demo_data
        seed_demo_data()

    return app
