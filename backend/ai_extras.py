"""
ai_extras.py
All the bonus AI features beyond quiz generation.
Each function takes text (and optional config) and returns structured data.

Prompts are designed to always return clean JSON so the caller
can parse them without fragile text processing.
"""

import json
import re
from ai import call_ai


# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

STRICT_JSON_SYSTEM = """
You are QuizGenius AI.

IMPORTANT:
- Return ONLY valid JSON.
- Never return Markdown.
- Never use ```json.
- Never explain anything.
- Never add text before or after the JSON.
- The response must be directly parseable by json.loads().
"""


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return raw


def _parse(raw: str) -> dict | list:
    cleaned = _clean_json(raw)

    try:
        return json.loads(cleaned)
    except Exception as e:
        print("AI Response:")
        print(cleaned)
        raise ValueError(f"AI returned invalid JSON: {e}")


# ─────────────────────────────────────────────
# 1. FLASHCARDS
# ─────────────────────────────────────────────

def generate_flashcards(text: str, count: int = 10) -> list[dict]:
    """
    Returns: [{"front": "...", "back": "..."}, ...]
    """
    prompt = f"""
Generate {count} flashcards from the text below.
Each flashcard must have:
- "front": a question or key term (concise)
- "back": the answer or definition (1-3 sentences)

Return JSON: {{"flashcards": [{{"front":"...","back":"..."}}]}}

Text:
\"\"\"{text[:8000]}\"\"\"
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("flashcards", [])


# ─────────────────────────────────────────────
# 2. SUMMARY / KEY POINTS
# ─────────────────────────────────────────────

def generate_summary(text: str) -> dict:
    """
    Returns: {
      "summary": "...",
      "key_points": ["...", ...],
      "topics": ["...", ...]
    }
    """
    prompt = f"""
Analyse the text below and return:
- "summary": a 3-5 sentence plain-English summary
- "key_points": a list of 5-8 most important points (each a single sentence)
- "topics": a list of 3-6 main topic tags (short phrases)

Return JSON only.

Text:
\"\"\"{text[:8000]}\"\"\"
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    return _parse(raw)


# ─────────────────────────────────────────────
# 3. HINTS (per question)
# ─────────────────────────────────────────────

def generate_hints(questions: list[dict]) -> list[dict]:
    """
    Takes the stored questions list and returns a list of hints,
    one per question, without revealing the answer.

    Returns: [{"index": 0, "hint": "..."}, ...]
    """
    q_list = [
        {"index": i, "question": q["question"]}
        for i, q in enumerate(questions[:20])  # cap at 20
    ]
    prompt = f"""
For each question below, write a short hint that helps the student
think in the right direction WITHOUT giving away the answer.
Each hint must be 1 sentence.

Questions: {json.dumps(q_list)}

Return JSON: {{"hints": [{{"index": 0, "hint": "..."}}]}}
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("hints", [])


# ─────────────────────────────────────────────
# 4. EXPLAIN WRONG ANSWERS (deep mode)
# ─────────────────────────────────────────────

def explain_wrong_answers(breakdown: list[dict]) -> list[dict]:
    """
    Takes the breakdown from scorer and generates deeper explanations
    only for questions the user got wrong.

    Returns: [{"index": i, "deep_explanation": "..."}, ...]
    """
    wrong = [
        {"index": i, "question": b["question"],
         "your_answer": b["your_answer"], "correct_answer": b["correct_answer"]}
        for i, b in enumerate(breakdown) if not b["is_correct"] and b["your_answer"]
    ]
    if not wrong:
        return []

    prompt = f"""
For each item below, explain in 2-3 sentences WHY the user's answer is wrong
and WHY the correct answer is right. Be educational and friendly.

Items: {json.dumps(wrong)}

Return JSON: {{"explanations": [{{"index": 0, "deep_explanation": "..."}}]}}
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("explanations", [])


# ─────────────────────────────────────────────
# 5. INTERVIEW QUESTIONS
# ─────────────────────────────────────────────

def generate_interview_questions(text: str, count: int = 10) -> list[dict]:
    """
    Returns: [{"question": "...", "sample_answer": "...", "level": "junior|mid|senior"}, ...]
    """
    prompt = f"""
Generate {count} interview questions based on the text below.
Mix difficulty levels: junior, mid, senior.

Each item must have:
- "question": the interview question
- "sample_answer": a strong 2-4 sentence model answer
- "level": one of "junior", "mid", "senior"

Return JSON: {{"questions": [...]}}

Text:
\"\"\"{text[:25000]}\"\"\"
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("questions", [])


# ─────────────────────────────────────────────
# 6. CODING QUIZ
# ─────────────────────────────────────────────

def generate_coding_quiz(topic: str, language: str = "Python", count: int = 10) -> list[dict]:
    """
    topic: e.g. "Python OOP", "SQL joins", "React hooks"
    Returns: [{"question":"...","options":[],"answer":"...","explanation":"...","code_snippet":"..."}, ...]
    """
    prompt = f"""
Generate {count} {language} coding multiple-choice questions about: {topic}.

Each question must have:
- "question": the question text
- "code_snippet": optional short code block relevant to the question (empty string if not applicable)
- "options": 4 answer choices
- "answer": the correct option (must match one of options exactly)
- "explanation": why the answer is correct

Return JSON: {{"questions": [...]}}
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("questions", [])


# ─────────────────────────────────────────────
# 7. VOCABULARY QUIZ
# ─────────────────────────────────────────────

def generate_vocabulary_quiz(text: str, count: int = 10) -> list[dict]:
    """
    Returns MCQ vocabulary questions extracted from the text.
    Returns: [{"word":"...","question":"...","options":[],"answer":"...","example_sentence":"..."}, ...]
    """
    prompt = f"""
Extract {count} advanced or domain-specific vocabulary words from the text
and create a definition-matching MCQ for each.

Each item must have:
- "word": the vocabulary word
- "question": "What does '[word]' mean?" style question
- "options": 4 possible definitions
- "answer": the correct definition (must match one option exactly)
- "example_sentence": a sentence using the word in context

Return JSON: {{"questions": [...]}}

Text:
\"\"\"{text[:8000]}\"\"\"
"""
    raw = call_ai(STRICT_JSON_SYSTEM, prompt)
    data = _parse(raw)
    return data.get("questions", [])


# ─────────────────────────────────────────────
# 8. ADAPTIVE DIFFICULTY ENGINE
# ─────────────────────────────────────────────

def get_next_difficulty(history: list[bool], current: str = "medium") -> str:
    """
    history: list of booleans (True = correct) for the last N answers
    current: "easy" | "medium" | "hard"

    Rule:
    - 3 correct in a row → increase difficulty
    - 3 wrong in a row   → decrease difficulty
    - Otherwise          → stay the same
    """
    if len(history) < 3:
        return current

    last3 = history[-3:]
    levels = ["easy", "medium", "hard"]
    idx = levels.index(current) if current in levels else 1

    if all(last3):        # 3 correct — go harder
        return levels[min(idx + 1, 2)]
    elif not any(last3):  # 3 wrong — go easier
        return levels[max(idx - 1, 0)]
    return current
