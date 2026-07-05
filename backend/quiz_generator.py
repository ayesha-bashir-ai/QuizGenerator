"""
quiz_generator.py
Builds the prompt sent to the AI and validates/cleans the JSON it returns.

The AI is instructed to return ONLY JSON. Models occasionally wrap the
response in markdown code fences (```json ... ```) anyway, so we strip
those before parsing. We also validate the structure and raise a clear
error if a question is missing required fields, rather than silently
passing broken data to the frontend.
"""

import json
import re
from ai import call_ai

SYSTEM_PROMPT = """
You are QuizGenius AI.

Your job is to generate educational quizzes.

IMPORTANT RULES:
- Return ONLY valid JSON.
- Do NOT use Markdown.
- Do NOT wrap the JSON in ``` blocks.
- Do NOT explain anything.
- Do NOT add extra text before or after the JSON.
- The response MUST be directly parseable by json.loads().
"""


def build_user_prompt(text: str, num_questions: int, difficulty: str, question_type: str) -> str:
    # Trim very long input to stay within reasonable token limits.
    trimmed_text = text[:25000]

    return f"""
Generate {num_questions} {question_type} questions based on the text below.
Difficulty: {difficulty}

Each question object must have exactly these fields:
- "question": string
- "options": array of 4 strings (omit this field entirely if question_type is "short_answer" or "true_false"; for true_false use ["True", "False"])
- "answer": string (must exactly match one of the options, or be "True"/"False")
- "explanation": short string explaining why the answer is correct
- "topic": short string tag (1-3 words) describing the topic of this question

Return JSON in exactly this shape, with no other text:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "answer": "...",
      "explanation": "...",
      "topic": "..."
    }}
  ]
}}

Text to generate questions from:
\"\"\"
{trimmed_text}
\"\"\"
"""


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return raw


def _validate_questions(data: dict):
    if "questions" not in data or not isinstance(data["questions"], list):
        raise ValueError("AI response missing 'questions' array.")

    if len(data["questions"]) == 0:
        raise ValueError("AI returned zero questions.")

    required_fields = {"question", "answer", "explanation"}
    for i, q in enumerate(data["questions"]):
        missing = required_fields - q.keys()
        if missing:
            raise ValueError(f"Question {i} is missing fields: {missing}")


def generate_quiz(text: str, num_questions: int = 10, difficulty: str = "medium",
                   question_type: str = "multiple-choice") -> dict:
    """
    Returns a dict: {"questions": [...]}
    Retries once if the first response fails to parse/validate.
    """
    prompt = build_user_prompt(text, num_questions, difficulty, question_type)

    last_error = None
    for attempt in range(2):  # try twice before giving up
        raw_response = call_ai(SYSTEM_PROMPT, prompt)
        cleaned = _strip_code_fences(raw_response)

        try:
            data = json.loads(cleaned)
            _validate_questions(data)
            return data
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            continue

    raise RuntimeError(f"AI failed to return a valid quiz after retries: {last_error}")
