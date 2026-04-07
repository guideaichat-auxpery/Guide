# Overview
Guide is a Montessori educational platform that bridges Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development by offering tailored resources and insights to educators and students.

# User Preferences
Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Frontend (React SPA)
- **Framework**: Vite + React + TypeScript + Tailwind CSS v4 in `/frontend`
- **Dev server**: Port 5000 (Vite), with proxy routing `/api/*` to FastAPI on port 8000
- **Production**: Static files built to `frontend/dist`, served by FastAPI with SPA fallback
- **Design System**: Montessori earth-tone palette (sand, clay, sky, leaf, ink, paper) with Danish Eco-Design accents. Fonts: Inter (sans), Cormorant Garamond (serif headers). WCAG 2.1 AA accessible.
- **Routing**: React Router v7 with protected routes. Educators see sidebar with Dashboard, Lesson Planning, Companion, Great Stories, Imaginarium, PD Expert, Students, Planning Notes, Settings. Students see Learn + Settings. Public pages: Login, Signup, Forgot/Reset Password, Join School, Contact, Privacy Policy.
- **Auth**: AuthContext with JWT token in localStorage, session validation via `/api/auth/session`.
- **API client**: `/frontend/src/lib/api.ts` — typed client for all FastAPI endpoints including FormData upload support. Base URL configurable via `VITE_API_URL` (defaults to `/api`).
- **Key directories**:
  - `frontend/src/pages/` — All page components (Login, Dashboard, LessonPlanning, Companion, etc.)
  - `frontend/src/components/` — Layout, ProtectedRoute, ChatInterface, RichTextEditor
  - `frontend/src/contexts/` — AuthContext
  - `frontend/src/lib/` — API client, types

## Backend (FastAPI REST API)
- **Framework**: FastAPI on port 8000 via uvicorn (dev), port 5000 in production
- **Static serving**: In production, FastAPI serves `frontend/dist` with SPA fallback for deep links
- **Modules**:
  - `api/main.py` — App with CORS (auto-detects Replit domains), router wiring, health check, static file serving
  - `api/db.py` — SQLAlchemy engine/session
  - `api/deps.py` — Auth dependencies (token-based via persistent_sessions table)
  - `api/routes/auth.py` — Login, signup, logout, session, password management, school join
  - `api/routes/users.py` — Profile CRUD, email change, account deletion
  - `api/routes/students.py` — Student CRUD, activities, learning journey, access management
  - `api/routes/schools.py` — School info, educator management
  - `api/routes/tools.py` — AI chat, lesson plan, great story, conversation management
  - `api/routes/notes.py` — Planning notes and stories CRUD
  - `api/routes/data.py` — Data export, audit logs, safety alerts
  - `api/routes/adaptive.py` — Adaptive learning proxy

## Infrastructure
- **Development**: Vite dev server on port 5000 (webview) proxies `/api/*` to FastAPI on 8000. Adaptive server on 3000.
- **Production/Deployment**: Single Autoscale deployment running `start_all.sh` — builds frontend, starts FastAPI on port 5000 (serves API + static frontend), adaptive server on 3000.
- **Adaptive Learning Server** (`adaptive/server.js`): Port 3000
- **Database**: PostgreSQL with pgvector

## Deployment
- **Target**: Autoscale
- **Build**: `cd frontend && npm install && npm run build`
- **Run**: `bash start_all.sh` (starts FastAPI on 5000 + Adaptive on 3000)
- **CORS**: Auto-detects `REPLIT_DEV_DOMAIN`, `REPLIT_DOMAINS`, `REPLIT_DEPLOYMENT_URL` for allowed origins
- **SPA fallback**: All non-API, non-file routes return `index.html` for client-side routing

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
