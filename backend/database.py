"""
database.py
Sets up the SQLAlchemy connection to the Neon Postgres database.

Important: Neon (serverless Postgres) auto-suspends the database when idle
and wakes it up on the next query. pool_pre_ping=True makes SQLAlchemy test
the connection before using it, so we don't get stale-connection errors
after the DB has been idle for a while.
"""

import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def init_db(app):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill in "
            "your Neon connection string."
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,  # recycle connections before Neon's idle timeout
    }

    db.init_app(app)
