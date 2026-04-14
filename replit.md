# Overview
Guide is a Montessori educational platform that bridges Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development by offering tailored resources and insights to educators and students.

# User Preferences
Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Split Deployment Architecture
The application uses a split architecture:
- **Frontend**: Hosted on Replit as a Static deployment (`frontend/dist`)
- **Backend**: Designed to run on Render.com (FastAPI + Adaptive Learning Node.js server)
- **Database**: PostgreSQL — Replit PostgreSQL for development, Neon for production on Render

## Frontend (React SPA)
- **Framework**: Vite + React + TypeScript + Tailwind CSS v4 in `/frontend`
- **Dev server**: Port 5000 (Vite), with proxy routing `/api/*` to FastAPI on port 8000
- **Production**: Static files built to `frontend/dist`, served by Replit Static deployment with SPA fallback
- **Design System**: Montessori earth-tone palette (sand, clay, sky, leaf, ink, paper) with Danish Eco-Design accents. Fonts: Inter (sans), Cormorant Garamond (serif headers). WCAG 2.1 AA accessible.
- **Routing**: React Router v7 with protected routes. Educators see sidebar with Dashboard, Lesson Planning, Companion, Great Stories, Imaginarium, PD Expert, Students, Planning Notes, Settings. Students see Learn + Settings. Public pages: Login, Signup, Forgot/Reset Password, Join School, Contact, Privacy Policy.
- **Auth**: AuthContext with JWT token in localStorage, session validation via `/api/auth/session`.
- **API client**: `/frontend/src/lib/api.ts` — typed client for all FastAPI endpoints including FormData upload support. Base URL configurable via `VITE_API_URL` (defaults to `/api`). For Render deployment, set `VITE_API_URL=https://guide-api.onrender.com/api`.
- **Key directories**:
  - `frontend/src/pages/` — All page components (Login, Dashboard, LessonPlanning, Companion, etc.)
  - `frontend/src/components/` — Layout, ProtectedRoute, ChatInterface, RichTextEditor
  - `frontend/src/contexts/` — AuthContext
  - `frontend/src/lib/` — API client, types

## Backend (FastAPI REST API)
- **Framework**: FastAPI on port 8000 via uvicorn
- **Modules**:
  - `api/main.py` — App with CORS (auto-detects Replit domains + supports CORS_ORIGINS env var for Render), router wiring, health check
  - `api/db.py` — SQLAlchemy engine/session with Neon SSL support
  - `api/deps.py` — Auth dependencies (token-based via persistent_sessions table)
  - `api/routes/auth.py` — Login, signup, logout, session, password management, school join
  - `api/routes/users.py` — Profile CRUD, email change, account deletion
  - `api/routes/students.py` — Student CRUD, activities, learning journey, access management
  - `api/routes/schools.py` — School info, educator management
  - `api/routes/tools.py` — AI chat, lesson plan, great story, conversation management
  - `api/routes/notes.py` — Planning notes and stories CRUD
  - `api/routes/data.py` — Data export, audit logs, safety alerts
  - `api/routes/adaptive.py` — Adaptive learning proxy

## Adaptive Learning Server (Node.js)
- **Location**: `adaptive/server.js` on port 3000
- **KV Storage**: Uses PostgreSQL-backed KV store (`adaptive/pgKvStore.js`) instead of `@replit/database`
- **Table**: `kv_store` with `key` (text PK), `value` (jsonb), `created_at` columns

## Infrastructure

### Development (Replit)
- Vite dev server on port 5000 (webview) proxies `/api/*` to FastAPI on 8000
- Adaptive server on port 3000
- Replit PostgreSQL database

### Production (Render + Replit Static)
- Frontend: Replit Static deployment from `frontend/dist`
- Backend: Render Web Service running `render_start.sh` (FastAPI + Adaptive server)
- Database: Neon PostgreSQL (SSL required)
- `render.yaml` Blueprint file for one-click Render deployment

## Render + Neon Setup Guide
1. Create a Neon database at neon.tech (free tier)
2. Create a Render Web Service pointing at this repo
3. Set environment variables on Render:
   - `DATABASE_URL` — Neon connection string
   - `OPENAI_API_KEY` — OpenAI API key
   - `RESEND_API_KEY` — Resend email API key
   - `ADMIN_PASSWORD` — Admin account password
   - `CORS_ORIGINS` — Comma-separated allowed origins (e.g. `https://your-app.replit.app`)
4. Build the frontend with `VITE_API_URL=https://your-render-service.onrender.com/api npm run build`
5. Deploy frontend to Replit Static

## Deployment
- **Replit Static**: `frontend/dist` as public directory, SPA fallback enabled
- **Render**: `render.yaml` Blueprint, `render_start.sh` start script, `requirements-render.txt` for pip
- **CORS**: Auto-detects Replit domains + CORS_ORIGINS env var for cross-origin Render requests

## Authentication
- Email/password for educators, username/password for students
- bcrypt hashing, session tokens in persistent_sessions table
- Admin accounts: ben.d.noble@gmail.com, ben@hmswairoa.net
- PD Expert restricted to specific email addresses
- School invite system with shareable codes

## AI Integration
- OpenAI GPT-4o-mini with dynamic system prompts
- Features: Montessori Companion (15 topic cards), Lesson Planning (generate/align/differentiate), Great Stories, Imaginarium, PD Expert, Student Tutor
- Adaptive learning system with prompt weighting

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o-mini model

## Frontend (npm)
- react, react-dom, react-router-dom
- lucide-react (icons)
- tailwindcss, @tailwindcss/vite
- @tiptap/* (rich-text editor)

## Python Libraries
- fastapi, uvicorn
- openai, bcrypt, resend
- sqlalchemy, psycopg2
- pandas, reportlab, python-docx

## Curriculum Frameworks
- Australian Curriculum V9
- Montessori National Curriculum (2011)
