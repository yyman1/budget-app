from flask import Flask
from web.config import Config
from web.models import db


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    db.init_app(app)

    # Register blueprints
    from web.routes.dashboard import dashboard_bp
    from web.routes.transactions import transactions_bp
    from web.routes.budgets import budgets_bp
    from web.routes.categories import categories_bp
    from web.routes.accounts import accounts_bp
    from web.routes.imports import imports_bp
    from web.routes.obligations import obligations_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(budgets_bp, url_prefix="/budgets")
    app.register_blueprint(categories_bp, url_prefix="/categories")
    app.register_blueprint(accounts_bp, url_prefix="/accounts")
    app.register_blueprint(imports_bp, url_prefix="/import")
    app.register_blueprint(obligations_bp, url_prefix="/obligations")

    # Custom Jinja filters
    @app.template_filter("money")
    def money_filter(value, decimals=2):
        """Format a number as $1,234.56"""
        try:
            v = float(value)
            return f"${v:,.{decimals}f}"
        except (ValueError, TypeError):
            return "$0.00"

    # Create tables on first request
    with app.app_context():
        db.create_all()

    return app
