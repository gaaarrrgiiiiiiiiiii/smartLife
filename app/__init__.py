from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail
from .config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD,
)

# Initialize global extensions
db = SQLAlchemy()
mail = Mail()


def create_app():
    """App factory pattern to create and configure the Flask app."""
    app = Flask(__name__)
    CORS(app)

    # --- Core Config ---
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY

    # --- Mail Config ---
    app.config["MAIL_SERVER"] = MAIL_SERVER
    app.config["MAIL_PORT"] = MAIL_PORT
    app.config["MAIL_USE_TLS"] = MAIL_USE_TLS
    app.config["MAIL_USERNAME"] = MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = MAIL_PASSWORD

    # --- Initialize Extensions ---
    db.init_app(app)
    mail.init_app(app)

    # --- Register Blueprints ---
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .routes.profile import profile_bp
    app.register_blueprint(profile_bp)

    from .routes.news import news_bp
    app.register_blueprint(news_bp)

    from .routes.nav import threshold_bp
    app.register_blueprint(threshold_bp)

    from .routes.stocks import stocks_bp
    app.register_blueprint(stocks_bp)

   

    return app
