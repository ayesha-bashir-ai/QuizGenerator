"""
models.py
Database table definitions.
"""

from datetime import datetime
from flask_login import UserMixin
from database import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    quizzes = db.relationship(
        "Quiz",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )

    attempts = db.relationship(
        "Attempt",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    source_filename = db.Column(db.String(255))
    difficulty = db.Column(db.String(20), default="medium")
    question_type = db.Column(db.String(30), default="mcq")
    topic_tags = db.Column(db.String(255))

    questions_json = db.Column(db.JSON, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attempts = db.relationship(
        "Attempt",
        backref="quiz",
        lazy=True,
        cascade="all, delete-orphan"
    )

    flashcards = db.relationship(
        "Flashcard",
        backref="quiz",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)

    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("quizzes.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    answers_json = db.Column(db.JSON, nullable=False)

    score = db.Column(db.Float, nullable=False)

    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)

    time_taken_seconds = db.Column(db.Integer)

    attempted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Flashcard(db.Model):
    __tablename__ = "flashcards"

    id = db.Column(db.Integer, primary_key=True)

    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("quizzes.id"),
        nullable=False
    )

    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(1000), nullable=False)