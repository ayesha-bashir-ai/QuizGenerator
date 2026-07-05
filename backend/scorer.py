"""
scorer.py
Compares submitted answers against the stored correct answers and
calculates score, grade, and pass/fail.
"""


def grade_letter(percentage: float) -> str:
    if percentage >= 90:
        return "A"
    if percentage >= 80:
        return "B"
    if percentage >= 70:
        return "C"
    if percentage >= 60:
        return "D"
    return "F"


def score_quiz(questions: list, user_answers: dict, passing_percentage: int = 60) -> dict:
    """
    questions: the list stored in Quiz.questions_json["questions"]
    user_answers: dict like {"0": "Artificial Intelligence", "1": None, ...}
                  keys are question index as string, value is the user's
                  selected answer (or None/missing if skipped)

    Returns a detailed report dict.
    """
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    breakdown = []

    for i, q in enumerate(questions):
        user_answer = user_answers.get(str(i))
        correct_answer = q["answer"]

        if user_answer is None or user_answer == "":
            skipped_count += 1
            is_correct = False
        elif str(user_answer).strip().lower() == str(correct_answer).strip().lower():
            correct_count += 1
            is_correct = True
        else:
            wrong_count += 1
            is_correct = False

        breakdown.append({
            "question": q["question"],
            "your_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "topic": q.get("topic", ""),
        })

    total = len(questions)
    percentage = round((correct_count / total) * 100, 2) if total else 0

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "skipped_count": skipped_count,
        "score_percentage": percentage,
        "grade": grade_letter(percentage),
        "passed": percentage >= passing_percentage,
        "breakdown": breakdown,
    }
