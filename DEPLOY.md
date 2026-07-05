# QuizGenius AI — Deployment Guide

## Local Development

```bash
# 1. Clone and set up backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in DATABASE_URL, OPENAI_API_KEY, SECRET_KEY

# 2. Run backend
python app.py                   # runs on http://localhost:5000

# 3. Open frontend
# Just open frontend/index.html in a browser
# (No build step needed — it's plain HTML/JS)
```

---

## Step 1 — Neon Database Setup

1. Go to https://neon.tech → Sign up (free)
2. Create a new **Project**
3. Copy the **Pooled connection string** from the dashboard
   (looks like `postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`)
4. Paste it into `.env` as `DATABASE_URL`
5. Tables are created automatically when the app first starts (`db.create_all()`)

---

## Step 2 — OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new key → copy it
3. Paste into `.env` as `OPENAI_API_KEY`
4. Recommended model: `gpt-4o-mini` (fast + cheap, good for quiz gen)

---

## Step 3 — Deploy Backend on Render

1. Push the whole repo to GitHub
2. Go to https://render.com → New → **Web Service**
3. Connect your GitHub repo
4. Set **Root Directory** → `backend`
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
7. Add environment variables in the Render dashboard:
   - `DATABASE_URL`   → your Neon connection string
   - `OPENAI_API_KEY` → your OpenAI key
   - `SECRET_KEY`     → any long random string (use Render's "Generate" button)
   - `MAX_UPLOAD_MB`  → `10`
8. Deploy → wait ~2 min → note your backend URL (e.g. `https://quizgenius-backend.onrender.com`)

---

## Step 4 — Update Frontend API URL

In `frontend/js/utils.js`, change:
```js
const API = "http://localhost:5000/api";
```
to:
```js
const API = "https://quizgenius-backend.onrender.com/api";
```

---

## Step 5 — Deploy Frontend on Vercel

1. Go to https://vercel.com → New Project → import your GitHub repo
2. Set **Root Directory** → `frontend`
3. **Framework Preset** → Other (no build step, it's static HTML)
4. Deploy → done

OR use Netlify:
- Drag-and-drop the `frontend/` folder to https://app.netlify.com/drop

---

## All API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Create account |
| POST | `/api/login` | Login |
| POST | `/api/logout` | Logout |

### Core Quiz
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload file or paste text |
| POST | `/api/generate-quiz` | Generate quiz from text |
| POST | `/api/submit` | Submit answers, get score |
| GET  | `/api/history` | All past attempts |
| GET  | `/api/results/<id>` | Single attempt result |

### AI Extras
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/flashcards` | Generate flashcards |
| POST | `/api/summary` | Summary + key points |
| GET  | `/api/hints/<quiz_id>` | Per-question hints |
| GET  | `/api/explain-wrong/<attempt_id>` | Deep wrong-answer explanations |
| POST | `/api/interview-questions` | Interview Q&A |
| POST | `/api/coding-quiz` | Coding MCQs |
| POST | `/api/vocabulary-quiz` | Vocabulary quiz |
| POST | `/api/adaptive-next` | Get next difficulty level |

### Leaderboard & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leaderboard` | Top 20 scores |
| GET | `/api/export/pdf/<attempt_id>` | Download result as HTML/PDF |
| GET | `/api/export/csv` | Download full history as CSV |
| GET | `/api/health` | Health check |

### Admin (admin users only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/admin/stats` | Platform statistics |
| GET    | `/api/admin/users` | All users |
| DELETE | `/api/admin/users/<id>` | Delete user |
| GET    | `/api/admin/quizzes` | All quizzes |
| DELETE | `/api/admin/quizzes/<id>` | Delete quiz |
| POST   | `/api/admin/promote/<id>` | Make user an admin |

---

## Making yourself an Admin

After registering your account, run this in the Neon SQL editor:

```sql
UPDATE users SET is_admin = true WHERE email = 'your@email.com';
```

---

## Complete Page List

| File | Description |
|------|-------------|
| `index.html` | Home / landing page |
| `login.html` | Login + register (tabbed) |
| `upload.html` | Upload file / paste text + quiz settings |
| `quiz.html` | Quiz-taking: timer, flags, progress, submit |
| `result.html` | Score + per-question review |
| `history.html` | All past quiz attempts |
| `dashboard.html` | Analytics charts + stats |
| `flashcards.html` | Flashcards, summary, interview questions |
| `leaderboard.html` | Top 20 global ranking |
| `admin.html` | Admin: users, quizzes, activity |
