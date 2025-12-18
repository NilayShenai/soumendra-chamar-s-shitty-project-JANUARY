from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import click
from dotenv import load_dotenv

load_dotenv()

# Global database instance
# Initialized in create_app to keep configuration flexible
# Avoids creating multiple db objects across modules
# Note: sqlite database stored in project root (hr.db)
db = SQLAlchemy()


def create_app(test_config=None):
    # Point Flask to shared template/static directories at repo root
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config.update(
        SECRET_KEY="change-me",  # replace with env secret in production
        SQLALCHEMY_DATABASE_URI="sqlite:///hr.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from . import models  # noqa: F401
    from .auth import bp as auth_bp
    from .routes import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        with app.app_context():
            db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("seed")
    def seed_command():
        """Seed database with sample data."""
        from .seed import seed_data

        with app.app_context():
            seed_data()
        click.echo("Database seeded with sample records.")

    return app
