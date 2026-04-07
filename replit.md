# Overview
Guide is a Montessori educational platform that bridges Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development by offering tailored resources and insights to educators and students.

# User Preferences
Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Frontend (React SPA)
- **Framework**: Vite + React + TypeScript + Tailwind CSS v4 in `/frontend`
- **Dev server**: Port 5173 (Vite), proxied through reverse proxy on port 5000
- **Design System**: Montessori earth-tone palette (sand, clay, sky, leaf, ink, paper) with Danish Eco-Design accents. Fonts: Inter (sans), Cormorant Garamond (serif headers). WCAG 2.1 AA accessible.
- **Routing**: React Router v7 with protected routes. Educators see sidebar with Dashboard, Lesson Planning, Companion, Great Stories, Imaginarium, PD Expert, Students, Planning Notes, Settings. Students see Learn + Settings.
- **Auth**: AuthContext with JWT token in localStorage, session validation via `/api/auth/session`.
- **API client**: `/frontend/src/lib/api.ts` — typed client for all 79 FastAPI endpoints.
- **Key directories**:
  - `frontend/src/pages/` — All page components (Login, Dashboard, LessonPlanning, Companion, etc.)
  - `frontend/src/components/` — Layout, ProtectedRoute, ChatInterface (reusable chat UI)
  - `frontend/src/contexts/` — AuthContext
  - `frontend/src/lib/` — API client

## Backend (FastAPI REST API)
- **Framework**: FastAPI on port 8000 via uvicorn
- **Modules**:
  - `api/main.py` — App with CORS, router wiring, health check
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
- **Reverse Proxy** (`proxy_server.js`): Port 5000, routes `/api/*` to FastAPI (8000), everything else to Vite (5173)
- **Adaptive Learning Server** (`adaptive/server.js`): Port 3000
- **Legacy Streamlit** (`app.py`): Port 8080 (being replaced by React SPA)
- **Database**: PostgreSQL with pgvector

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

## Python Libraries
- streamlit, fastapi, uvicorn
- openai, bcrypt, resend
- sqlalchemy, psycopg2
- pandas, reportlab, python-docx

## Curriculum Frameworks
- Australian Curriculum V9
- Montessori National Curriculum (2011)
