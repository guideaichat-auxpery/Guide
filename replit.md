# Overview

Guide is a Streamlit-based cosmic curriculum companion designed to assist educators in bridging Montessori's Cosmic Education with contemporary curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development, offering tailored resources and insights to both educators and students.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## UI/UX Decisions
- **Framework**: Streamlit with a wide layout and dual-mode interface (educator and student).
- **Design System**: 
  - **Montessori Theme** (`static/css/montessori-theme.css`): Warm earth tones using Cormorant Garamond and Inter fonts with organic rounded corners, soft shadows, and smooth transitions for general interface elements.
  - **Danish Eco-Design Theme** (`static/css/danish-eco-theme.css`): Clean modernist educator dashboard with off-white background (#FAF9F6), muted forest green accent (#789A76), soft grey text (#2E2E2B), Inter typography, 16px rounded corners, generous whitespace, and card-based navigation. Features fixed header with "Guide by AUXPERY" wordmark, welcoming greeting, 3x2 grid of interactive feature cards (Lesson Planning, Student Dashboard, Montessori Companion, Planning Notes, Create Student, Great Stories), and account section. Fully responsive with WCAG 2.1 AA accessibility compliance. **Implementation Note**: Uses emoji icons (📚, 🌱, 👥, 📝, ➕, 📖) instead of custom SVG line icons as a pragmatic compromise - Streamlit's architecture makes truly interactive HTML divs with custom icons difficult while maintaining full accessibility (keyboard navigation, screen readers, focus states). CSS scoped to `.danish-dashboard-wrapper` to prevent cross-theme conflicts.

## Technical Implementations
- **Authentication**: Email/password for educators and username/password for students, with bcrypt hashing and session management, compliant with Australian Privacy Act 1988.
- **Session Management**: Enhanced Streamlit configuration with improved session stability and auto-recovery features. **Session timeout extended to 2 hours (7200 seconds)** to support student flow state during research and learning. Automatic conversation restoration on login to ensure continuity across sessions. **UX Improvements**: Visual save confirmations (toast notifications with ✓ icon) when messages save successfully, conversation restore notifications showing timestamp when previous chat auto-loads, and user-friendly error messages when database operations fail.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and an accessibility wizard. Session-based state management with PostgreSQL-backed persistence.
- **Backend**: Single-file Python application (`app.py`) for core logic, integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts.
  - **Student Research Assistant**: Year-level adaptive AI tutor with dual-mode responses. **Structure/Scaffold Mode** (triggered by keywords: structure, scaffold, plan, organize, outline) provides comprehensive essay breakdown with chunking, prompts, and detailed guidance. **Research Mode** (default) uses strict 3-part structure (Brief Answer, Further Research Directions, Reliable Sources). Temperature 0.3 for consistency, 1200 max tokens. **Enhanced Source Filtering** uses search-keyword approach: provides **3 alternative search phrasings** (direct/factual, alternative angle, broader/specific variation) students can type into search engines, then lists 3 stable homepage URLs where students use the site's search feature. **BBC Bitesize is low priority** - prioritizes Australian (ABC Education, Australian War Memorial) and international educational sources (Britannica, Khan Academy, National Geographic, Smithsonian). This prevents broken links and teaches research skills. Comprehensive academic keyword recognition across General Academic, Humanities & Social Sciences, STEM, Arts/Language, and Modern/Interdisciplinary topics, with trusted domain prioritization (.edu, .gov, .org, .com) and quality filters excluding unreliable sources (reddit, quora, fandom, etc.).
  - **Age-Appropriate Lesson Planning**: AI assistant provides developmental stage-specific prompts with strict curriculum framework rules and **highly detailed step-by-step instruction**. **Enhanced Detail Requirements**: Ages 3-6 receive 8-12 detailed steps with explicit body positioning, pacing, and common mistakes; Ages 6-9 receive 10-15 steps with educator prompts and student responses; Ages 9-12 receive 12-18 steps with facilitation strategies and troubleshooting; Ages 12-15 receive 15-25 steps with Socratic questioning and debate management. **All lesson plans end with 4-6 actionable "Suggestions for Further Refinement & Development"** covering adaptations, Montessori connections, curriculum alignment, community partnerships, resources, assessment, and cultural responsiveness. **Ages 12-15 (Years 7-9 / Cycle 4)**: Australian Curriculum V9 as primary framework with AC content descriptor codes, interpreted through Montessori Cosmic Education perspective. **Foundation - Year 6 (Cycles 1-3)**: Montessori curriculum as primary framework, Australian Curriculum referenced for alignment only with AC codes shown.
  - **Professional Development Expert**: A restricted-access, advanced PD coaching system with self-learning memory and comprehensive 6-section responses, implemented in Python for production readiness.
- **RAG System**: Semantic document retrieval using PostgreSQL pgvector and OpenAI embeddings, storing chunks from key educational texts. Retrieves top-3 relevant chunks based on user queries, supporting AC_V9-only, Montessori-only, or Blended retrieval modes.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, curriculum contexts, adaptive learning data, and RAG document chunks. In-memory session state. Lesson plan export to PDF and DOCX.
- **Adaptive Learning System (Node.js - Development Only)**: An Express.js server managing self-updating AI prompts, semantic logging, feedback, trending keywords, and subject calibration. Features a REST API for generation, feedback, and analytics, with an auto-refresh system for prompt updates.
- **Core Features**:
  - **Dual Interface**: Teacher and student modes for lesson planning, observation, and AI tutoring.
  - **Chat Conversation Management**: Sidebar-based system for creating, renaming, deleting, and reopening conversations with full message context persistence in PostgreSQL. **Auto-loads most recent conversation on login** to restore chat history after logout or session timeout, with visual notification showing restore timestamp (DD/MM/YYYY HH:MM). Auto-creates conversation records on first message to ensure thread persistence across all interfaces (student, companion, planning). **Real-time message persistence** saves every message immediately to database with visual confirmation (✓ toast notification). **Enhanced error handling** displays user-friendly warnings if save operations fail. Analytics tracked in backend only (not visible to users).
  - **Curriculum Integration**: Incorporates Australian Curriculum V9 and Montessori National Curriculum (2011), with AI responses rooted in Montessori's Cosmic Education.
  - **AI-Powered Tools**: Includes Great Story Creator, Planning Notes Workspace, Educator Observation Dashboard, Lesson Planning Assistant (with three modes), Big Picture Curriculum Mapping, Student Work Analysis, and an advanced Rubric Generator.
  - **Accessibility**: Universal Design for Learning interface.

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o-mini model for natural language generation. All AI outputs use British English spelling.

## Python Libraries
- **streamlit**: Web application framework.
- **pandas**: Data manipulation.
- **plotly.express & plotly.graph_objects**: Interactive visualizations.
- **openai**: Official OpenAI Python client.
- **datetime**: Date and time handling.
- **reportlab & python-docx**: PDF and DOCX export.

## Curriculum Frameworks
- **Australian Curriculum V9**: Official government education standards.
- **Montessori National Curriculum (2011)**: Official Montessori Australia Foundation framework.
- **Dr. Montessori's Own Handbook**: Foundational Montessori text.
- **The Absorbent Mind**: Foundational Montessori text.
- **The Montessori Method**: Seminal Montessori work on pedagogy.
- **Montessori Curriculum Australia**: Broader child-centered educational methodology.