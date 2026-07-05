"""
app.py
Flask application entrypoint. Run with: python app.py
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from database import db, init_db
from models import User
from routes import api
from routes_extras import extras

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", 100)) * 1024 * 1024

    CORS(app, supports_credentials=True)
    init_db(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return {"error": "authentication required"}, 401

    # Rate limit AI-cost-incurring routes to prevent abuse
    limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day"])
    limiter.limit("20 per hour")(api)

    app.register_blueprint(api,    url_prefix="/api")
    app.register_blueprint(extras, url_prefix="/api")

    with app.app_context():
        db.create_all()

    @app.route("/api/health")
    def health():
        return {"status": "ok"}, 200

    return app


# gunicorn entry point: gunicorn "app:create_app()"
app = create_app()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
