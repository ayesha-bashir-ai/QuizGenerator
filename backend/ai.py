"""
ai.py

Wrapper around the Google Gemini API.

Responsibilities:
- Load Gemini API key from .env
- Create a single reusable Gemini client
- Send prompts to Gemini
- Return clean text responses
- Handle API/network errors gracefully
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = None


def get_client():
    """
    Returns a singleton Gemini client.
    """
    global _client

    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Please add it to your .env file."
            )

        _client = genai.Client(api_key=api_key)

    return _client


def call_ai(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    """
    Sends prompts to Gemini and returns plain text.
    """

    client = get_client()

    model = (
        model
        or os.getenv("GEMINI_MODEL")
        or "gemini-2.5-flash"
    )

    prompt = f"""{system_prompt}

{user_prompt}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            ),
        )

        if not response.text:
            raise RuntimeError("Empty response received from Gemini.")

        return response.text.strip()

    except Exception as e:
        raise RuntimeError(f"Gemini API Error: {e}")