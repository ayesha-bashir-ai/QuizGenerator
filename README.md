# QuizGenius AI — Backend Skeleton

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in DATABASE_URL, OPENAI_API_KEY, SECRET_KEY
python app.py
```

Server runs at http://localhost:5000

## Quick test flow (using curl)

```bash
# 1. Register
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"password123"}'

# 2. Login (save the session cookie)
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"password123"}'

# 3. Paste text instead of uploading a file
curl -b cookies.txt -X POST http://localhost:5000/api/upload \
  -H "Content-Type: application/json" \
  -d '{"text":"Photosynthesis is the process plants use to convert sunlight into energy..."}'

# 4. Generate a quiz from that text
curl -b cookies.txt -X POST http://localhost:5000/api/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{"text":"Photosynthesis is the process plants use to convert sunlight into energy...","num_questions":5,"difficulty":"medium","question_type":"multiple-choice","title":"Photosynthesis Quiz"}'

# 5. Submit answers (use quiz_id from step 4 response)
curl -b cookies.txt -X POST http://localhost:5000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"quiz_id":1,"answers":{"0":"some answer"},"time_taken_seconds":120}'

# 6. View history
curl -b cookies.txt http://localhost:5000/api/history
```

## What's built so far

- Neon Postgres connection (`database.py`)
- Models: User, Quiz, Attempt, Flashcard (`models.py`)
- File parsing: PDF, DOCX, PPTX, TXT, MD (`parser.py`)
- OpenAI API wrapper (`ai.py`)
- Quiz generation with JSON validation + retry (`quiz_generator.py`)
- Auto-scoring logic (`scorer.py`)
- Full route set: register/login/logout, upload, generate-quiz, submit, history, results (`routes.py`)
- Rate limiting on AI routes, session auth, password hashing

## Not yet built (next steps)

- Frontend (upload.html, quiz.html, result.html, history.html, dashboard.html)
- Dashboard analytics endpoint + Chart.js charts
- Flashcards, adaptive difficulty, hints generation endpoints
- Admin panel routes
- PDF/CSV export
- Leaderboard endpoint
© 2025 QuizGenius AI · Built with Flask + OpenAI + Neon · 