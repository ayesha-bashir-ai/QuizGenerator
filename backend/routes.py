"""
routes.py
All API endpoints, registered as a Blueprint in app.py.

Auth note: this uses simple session-based auth via flask-login for clarity.
Swap for JWT later if you want a fully stateless API (e.g. for a separate
mobile app).
"""

import os
import uuid
import bcrypt
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from database import db
from models import User, Quiz, Attempt, Flashcard
from parser import extract_text, allowed_file, UnsupportedFileType
from quiz_generator import generate_quiz
from scorer import score_quiz

api = Blueprint("api", __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------- AUTH ----------

@api.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or len(password) < 6:
        return jsonify({"error": "username, email and a password (6+ chars) are required"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "username or email already in use"}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "registered successfully", "user_id": user.id}), 201


@api.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({"error": "invalid email or password"}), 401

    login_user(user)
    return jsonify({"message": "logged in", "user_id": user.id, "username": user.username})


@api.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "logged out"})


# ---------- UPLOAD ----------

@api.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "no file selected"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "unsupported file type"}), 400

        # save with a unique name to avoid collisions
        ext = os.path.splitext(file.filename)[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, saved_name)
        file.save(filepath)

        try:
            text = extract_text(filepath)
        except (UnsupportedFileType, ValueError) as e:
            return jsonify({"error": str(e)}), 400
        finally:
            os.remove(filepath)  # don't keep raw files around longer than needed

        return jsonify({"text": text, "source_filename": file.filename})

    # fallback: raw pasted text
    data = request.get_json(silent=True) or {}
    pasted_text = data.get("text", "").strip()
    if not pasted_text:
        return jsonify({"error": "no file or text provided"}), 400

    return jsonify({"text": pasted_text, "source_filename": None})


# ---------- QUIZ GENERATION ----------

@api.route("/generate-quiz", methods=["POST"])
@login_required
def generate_quiz_route():
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    num_questions = int(data.get("num_questions", 10))
    difficulty = data.get("difficulty", "medium")
    question_type = data.get("question_type", "multiple-choice")
    source_filename = data.get("source_filename")
    title = data.get("title") or "Untitled Quiz"

    if not text:
        return jsonify({"error": "text is required"}), 400
    if num_questions < 1 or num_questions > 50:
        return jsonify({"error": "num_questions must be between 1 and 50"}), 400

    try:
        quiz_data = generate_quiz(text, num_questions, difficulty, question_type)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502  # AI/upstream failure

    quiz = Quiz(
        user_id=current_user.id,
        title=title,
        source_filename=source_filename,
        difficulty=difficulty,
        question_type=question_type,
        questions_json=quiz_data,
    )
    db.session.add(quiz)
    db.session.commit()

    # Strip correct answers before sending to frontend so users can't
    # inspect the network tab and see answers before submitting.
    public_questions = [
        {"qid": i, **{k: v for k, v in q.items() if k not in ("answer", "explanation")}}
        for i, q in enumerate(quiz_data["questions"])
    ]

    return jsonify({
        "quiz_id": quiz.id,
        "title": quiz.title,
        "questions": public_questions,
    }), 201


# ---------- SUBMIT / SCORING ----------

@api.route("/submit", methods=["POST"])
@login_required
def submit_quiz():
    data = request.get_json(force=True)
    quiz_id = data.get("quiz_id")
    user_answers = data.get("answers", {})  # {"0": "answer text", ...}
    time_taken = data.get("time_taken_seconds")

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "quiz not found"}), 404

    report = score_quiz(quiz.questions_json["questions"], user_answers)

    attempt = Attempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        answers_json=user_answers,
        score=report["score_percentage"],
        correct_count=report["correct_count"],
        wrong_count=report["wrong_count"],
        skipped_count=report["skipped_count"],
        time_taken_seconds=time_taken,
    )
    db.session.add(attempt)
    db.session.commit()

    report["attempt_id"] = attempt.id
    return jsonify(report)


# ---------- HISTORY / RESULTS ----------

@api.route("/history", methods=["GET"])
@login_required
def history():
    attempts = (
        Attempt.query.filter_by(user_id=current_user.id)
        .order_by(Attempt.attempted_at.desc())
        .all()
    )
    return jsonify([
        {
            "attempt_id": a.id,
            "quiz_id": a.quiz_id,
            "quiz_title": a.quiz.title,
            "score": a.score,
            "correct": a.correct_count,
            "wrong": a.wrong_count,
            "skipped": a.skipped_count,
            "attempted_at": a.attempted_at.isoformat(),
        }
        for a in attempts
    ])


@api.route("/history/<int:attempt_id>", methods=["DELETE"])
@login_required
def delete_history(attempt_id):
    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404
    db.session.delete(attempt)
    db.session.commit()
    return jsonify({"message": "attempt deleted"})


@api.route("/results/<int:attempt_id>", methods=["GET"])
@login_required
def get_result(attempt_id):
    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404

    quiz = attempt.quiz
    report = score_quiz(quiz.questions_json["questions"], attempt.answers_json)
    report["attempt_id"] = attempt.id
    report["quiz_title"] = quiz.title
    return jsonify(report)
