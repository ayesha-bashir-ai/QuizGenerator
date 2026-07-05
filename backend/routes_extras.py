"""
routes_extras.py
All routes beyond the core quiz flow:
  - /api/flashcards
  - /api/summary
  - /api/hints
  - /api/explain-wrong
  - /api/interview-questions
  - /api/coding-quiz
  - /api/vocabulary-quiz
  - /api/adaptive-next
  - /api/export/pdf/<attempt_id>
  - /api/export/csv
  - /api/leaderboard
  - Admin routes under /api/admin/...
"""

import io
import csv
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from functools import wraps

from database import db
from models import User, Quiz, Attempt, Flashcard
from ai_extras import (
    generate_flashcards, generate_summary, generate_hints,
    explain_wrong_answers, generate_interview_questions,
    generate_coding_quiz, generate_vocabulary_quiz, get_next_difficulty,
)
from scorer import score_quiz

extras = Blueprint("extras", __name__)


# ─────────────────────────────────────────────
# Admin guard decorator
# ─────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"error": "admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# 1. FLASHCARDS
# ─────────────────────────────────────────────

@extras.route("/flashcards", methods=["POST"])
@login_required
def flashcards():
    data = request.get_json(force=True)
    text  = data.get("text", "").strip()
    count = int(data.get("count", 10))
    quiz_id = data.get("quiz_id")

    if not text:
        return jsonify({"error": "text is required"}), 400

    cards = generate_flashcards(text, count)

    # Optionally persist to DB if linked to a quiz
    if quiz_id:
        Flashcard.query.filter_by(quiz_id=quiz_id).delete()
        for c in cards:
            db.session.add(Flashcard(
                quiz_id=quiz_id,
                question=c.get("front", ""),
                answer=c.get("back", ""),
            ))
        db.session.commit()

    return jsonify({"flashcards": cards})


# ─────────────────────────────────────────────
# 2. SUMMARY + KEY POINTS
# ─────────────────────────────────────────────

@extras.route("/summary", methods=["POST"])
@login_required
def summary():
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    result = generate_summary(text)
    return jsonify(result)


# ─────────────────────────────────────────────
# 3. HINTS  (during a live quiz)
# ─────────────────────────────────────────────

@extras.route("/hints/<int:quiz_id>", methods=["GET"])
@login_required
def hints(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "quiz not found"}), 404

    questions = quiz.questions_json.get("questions", [])
    result = generate_hints(questions)
    return jsonify({"hints": result})


# ─────────────────────────────────────────────
# 4. EXPLAIN WRONG ANSWERS (post-quiz)
# ─────────────────────────────────────────────

@extras.route("/explain-wrong/<int:attempt_id>", methods=["GET"])
@login_required
def explain_wrong(attempt_id):
    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404

    quiz = attempt.quiz
    report = score_quiz(quiz.questions_json["questions"], attempt.answers_json)
    explanations = explain_wrong_answers(report["breakdown"])
    return jsonify({"explanations": explanations})


# ─────────────────────────────────────────────
# 5. INTERVIEW QUESTIONS
# ─────────────────────────────────────────────

@extras.route("/interview-questions", methods=["POST"])
@login_required
def interview_questions():
    data  = request.get_json(force=True)
    text  = data.get("text", "").strip()
    count = int(data.get("count", 10))
    if not text:
        return jsonify({"error": "text is required"}), 400

    questions = generate_interview_questions(text, count)
    return jsonify({"questions": questions})


# ─────────────────────────────────────────────
# 6. CODING QUIZ
# ─────────────────────────────────────────────

@extras.route("/coding-quiz", methods=["POST"])
@login_required
def coding_quiz():
    data     = request.get_json(force=True)
    topic    = data.get("topic", "").strip()
    language = data.get("language", "Python")
    count    = int(data.get("count", 10))
    if not topic:
        return jsonify({"error": "topic is required"}), 400

    questions = generate_coding_quiz(topic, language, count)
    return jsonify({"questions": questions})


# ─────────────────────────────────────────────
# 7. VOCABULARY QUIZ
# ─────────────────────────────────────────────

@extras.route("/vocabulary-quiz", methods=["POST"])
@login_required
def vocabulary_quiz():
    data  = request.get_json(force=True)
    text  = data.get("text", "").strip()
    count = int(data.get("count", 10))
    if not text:
        return jsonify({"error": "text is required"}), 400

    questions = generate_vocabulary_quiz(text, count)
    return jsonify({"questions": questions})


# ─────────────────────────────────────────────
# 8. ADAPTIVE DIFFICULTY
# ─────────────────────────────────────────────

@extras.route("/adaptive-next", methods=["POST"])
@login_required
def adaptive_next():
    """
    Client sends running answer history and current difficulty.
    Server returns recommended next difficulty level.
    """
    data     = request.get_json(force=True)
    history  = data.get("history", [])   # list of booleans
    current  = data.get("current", "medium")

    next_diff = get_next_difficulty(history, current)
    return jsonify({"next_difficulty": next_diff, "changed": next_diff != current})


# ─────────────────────────────────────────────
# 9. LEADERBOARD
# ─────────────────────────────────────────────

@extras.route("/leaderboard", methods=["GET"])
@login_required
def leaderboard():
    """Top 20 by highest single-attempt score, then by fastest time."""
    rows = (
        db.session.query(Attempt, User)
        .join(User, Attempt.user_id == User.id)
        .order_by(Attempt.score.desc(), Attempt.time_taken_seconds.asc())
        .limit(20)
        .all()
    )
    return jsonify([
        {
            "rank":         i + 1,
            "username":     u.username,
            "quiz_title":   a.quiz.title,
            "score":        round(a.score, 1),
            "time_seconds": a.time_taken_seconds,
            "date":         a.attempted_at.isoformat(),
        }
        for i, (a, u) in enumerate(rows)
    ])


# ─────────────────────────────────────────────
# 10. EXPORT — PDF
# ─────────────────────────────────────────────

@extras.route("/export/pdf/<int:attempt_id>", methods=["GET"])
@login_required
def export_pdf(attempt_id):
    """
    Generates a clean HTML report and returns it as a downloadable file.
    The browser's native print → Save as PDF handles final conversion.
    For server-side PDF generation, install weasyprint and swap the
    send_file call below (commented out).
    """
    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404

    quiz   = attempt.quiz
    report = score_quiz(quiz.questions_json["questions"], attempt.answers_json)
    user   = current_user

    rows = ""
    for i, b in enumerate(report["breakdown"]):
        icon = "✅" if b["is_correct"] else ("❌" if b["your_answer"] else "⏭")
        rows += f"""
        <div class="qrow">
          <div class="qheader">
            <span class="qnum">Q{i+1}</span>
            <span class="qicon">{icon}</span>
          </div>
          <div class="qtext">{b['question']}</div>
          {"<div class='your-ans wrong'>Your answer: " + str(b['your_answer']) + "</div>" if b['your_answer'] and not b['is_correct'] else ""}
          {"<div class='correct-ans'>Correct: " + str(b['correct_answer']) + "</div>" if not b['is_correct'] else ""}
          {"<div class='explanation'>💡 " + b['explanation'] + "</div>" if b.get('explanation') else ""}
        </div>"""

    grade_color = {"A":"#22c55e","B":"#00d4b4","C":"#f5c542","D":"#f97316","F":"#f05252"}
    color = grade_color.get(report["grade"], "#8892b0")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<title>Quiz Result — {quiz.title}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#fff; color:#1a1a2e; max-width:800px; margin:0 auto; padding:40px 32px; }}
  .header {{ text-align:center; border-bottom:2px solid #e2e8f0; padding-bottom:24px; margin-bottom:32px; }}
  .brand {{ color:#7c5cfc; font-size:1.1rem; font-weight:700; margin-bottom:8px; }}
  h1 {{ font-size:1.6rem; margin:0 0 8px; }}
  .score-row {{ display:flex; justify-content:center; gap:32px; margin:24px 0; flex-wrap:wrap; }}
  .stat {{ text-align:center; }}
  .stat .val {{ font-size:2rem; font-weight:800; }}
  .stat .lbl {{ font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:.06em; }}
  .grade {{ font-size:3rem; font-weight:900; color:{color}; }}
  .pass-tag {{ display:inline-block; padding:4px 16px; border-radius:99px; font-size:.85rem; font-weight:700;
    background:{ '#dcfce7' if report['passed'] else '#fee2e2' };
    color:{ '#15803d' if report['passed'] else '#b91c1c' }; }}
  .qrow {{ border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin-bottom:12px; }}
  .qheader {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
  .qnum {{ font-size:.72rem; font-weight:700; color:#7c5cfc; background:#ede9fe; padding:2px 8px; border-radius:99px; }}
  .qicon {{ font-size:1.1rem; }}
  .qtext {{ font-size:.95rem; font-weight:600; margin-bottom:8px; }}
  .your-ans {{ font-size:.82rem; color:#b91c1c; margin-bottom:4px; }}
  .correct-ans {{ font-size:.82rem; color:#15803d; margin-bottom:4px; }}
  .explanation {{ font-size:.8rem; color:#475569; background:#f8fafc; padding:8px 12px; border-left:3px solid #7c5cfc; border-radius:0 4px 4px 0; margin-top:8px; }}
  .footer {{ text-align:center; margin-top:40px; color:#94a3b8; font-size:.78rem; border-top:1px solid #e2e8f0; padding-top:20px; }}
  @media print {{ body {{ padding:20px; }} }}
</style>
</head>
<body>
  <div class="header">
    <div class="brand">⚡ QuizGenius AI</div>
    <h1>{quiz.title}</h1>
    <div class="pass-tag">{"✅ PASSED" if report['passed'] else "❌ NOT PASSED"}</div>
    <div class="score-row">
      <div class="stat"><div class="val" style="color:{color}">{report['score_percentage']}%</div><div class="lbl">Score</div></div>
      <div class="stat"><div class="grade">{report['grade']}</div><div class="lbl">Grade</div></div>
      <div class="stat"><div class="val" style="color:#22c55e">{report['correct_count']}</div><div class="lbl">Correct</div></div>
      <div class="stat"><div class="val" style="color:#f05252">{report['wrong_count']}</div><div class="lbl">Wrong</div></div>
      <div class="stat"><div class="val" style="color:#f5c542">{report['skipped_count']}</div><div class="lbl">Skipped</div></div>
    </div>
    <p style="color:#64748b;font-size:.85rem;">
      Student: <strong>{user.username}</strong> &nbsp;|&nbsp;
      Date: <strong>{attempt.attempted_at.strftime('%d %b %Y, %H:%M')}</strong>
    </p>
  </div>

  <h2 style="margin-bottom:16px;font-size:1.1rem;">Question Review</h2>
  {rows}

  <div class="footer">Generated by QuizGenius AI · {datetime.utcnow().strftime('%Y-%m-%d')}</div>
</body>
</html>"""

    buf = io.BytesIO(html.encode("utf-8"))
    return send_file(
        buf,
        mimetype="text/html",
        as_attachment=True,
        download_name=f"quiz-result-{attempt_id}.html",
    )


# ─────────────────────────────────────────────
# 11. EXPORT — CSV
# ─────────────────────────────────────────────

@extras.route("/export/csv", methods=["GET"])
@login_required
def export_csv():
    """Downloads all of the current user's attempt history as a CSV."""
    attempts = (
        Attempt.query
        .filter_by(user_id=current_user.id)
        .order_by(Attempt.attempted_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Attempt ID", "Quiz Title", "Score %", "Correct",
        "Wrong", "Skipped", "Time (seconds)", "Date"
    ])
    for a in attempts:
        writer.writerow([
            a.id, a.quiz.title, round(a.score, 1),
            a.correct_count, a.wrong_count, a.skipped_count,
            a.time_taken_seconds or "",
            a.attempted_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=quiz-history.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


# ─────────────────────────────────────────────
# 12. ADMIN ROUTES
# ─────────────────────────────────────────────

@extras.route("/admin/stats", methods=["GET"])
@login_required
@admin_required
def admin_stats():
    total_users   = User.query.count()
    total_quizzes = Quiz.query.count()
    total_attempts = Attempt.query.count()
    avg_score = db.session.query(db.func.avg(Attempt.score)).scalar()

    recent_attempts = (
        db.session.query(Attempt, User, Quiz)
        .join(User, Attempt.user_id == User.id)
        .join(Quiz, Attempt.quiz_id == Quiz.id)
        .order_by(Attempt.attempted_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "total_users":    total_users,
        "total_quizzes":  total_quizzes,
        "total_attempts": total_attempts,
        "avg_score":      round(float(avg_score or 0), 1),
        "recent_attempts": [
            {
                "attempt_id": a.id,
                "username":   u.username,
                "quiz_title": q.title,
                "score":      round(a.score, 1),
                "date":       a.attempted_at.isoformat(),
            }
            for a, u, q in recent_attempts
        ],
    })


@extras.route("/admin/users", methods=["GET"])
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([
        {
            "id":         u.id,
            "username":   u.username,
            "email":      u.email,
            "is_admin":   u.is_admin,
            "quiz_count": len(u.quizzes),
            "joined":     u.created_at.isoformat(),
        }
        for u in users
    ])


@extras.route("/admin/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "cannot delete yourself"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"user {user_id} deleted"})


@extras.route("/admin/quizzes", methods=["GET"])
@login_required
@admin_required
def admin_quizzes():
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(100).all()
    return jsonify([
        {
            "id":         q.id,
            "title":      q.title,
            "owner":      q.owner.username,
            "difficulty": q.difficulty,
            "attempts":   len(q.attempts),
            "created":    q.created_at.isoformat(),
        }
        for q in quizzes
    ])


@extras.route("/admin/quizzes/<int:quiz_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "quiz not found"}), 404
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({"message": f"quiz {quiz_id} deleted"})


@extras.route("/admin/promote/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def admin_promote(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    user.is_admin = True
    db.session.commit()
    return jsonify({"message": f"{user.username} is now an admin"})
