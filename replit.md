# Overview

Guide is a Streamlit-based cosmic curriculum companion designed to assist educators in bridging Montessori's Cosmic Education with contemporary curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development, offering tailored resources and insights to both educators and students.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## UI/UX Decisions
- **Framework**: Streamlit with a wide layout and dual-mode interface (educator and student).
- **Design System**: Montessori-inspired visual theme using warm earth tones, specific fonts (Cormorant Garamond, Inter), organic rounded corners, soft shadows, and smooth transitions, loaded via `static/css/montessori-theme.css`.

## Technical Implementations
- **Authentication**: Email/password for educators and username/password for students, with bcrypt hashing and session management, compliant with Australian Privacy Act 1988.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and an accessibility wizard. Session-based state management.
- **Backend**: Single-file Python application (`app.py`) for core logic, integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts.
  - **Student Research Assistant**: Year-level adaptive AI tutor with dual-mode responses. **Structure/Scaffold Mode** (triggered by keywords: structure, scaffold, plan, organize, outline) provides comprehensive essay breakdown with chunking, prompts, and detailed guidance. **Research Mode** (default) uses strict 3-part structure (Brief Answer, Further Research Directions, Reliable Sources). Temperature 0.3 for consistency, 1200 max tokens. **Enhanced Source Filtering** includes comprehensive academic keyword recognition across General Academic, Humanities & Social Sciences, STEM, Arts/Language, and Modern/Interdisciplinary topics, with trusted domain prioritization (.edu, .gov, .org) and quality filters excluding unreliable sources (reddit, quora, fandom, etc.).
  - **Age-Appropriate Lesson Planning**: AI assistant provides developmental stage-specific prompts for lesson planning.
  - **Professional Development Expert**: A restricted-access, advanced PD coaching system with self-learning memory and comprehensive 6-section responses, implemented in Python for production readiness.
- **RAG System**: Semantic document retrieval using PostgreSQL pgvector and OpenAI embeddings, storing chunks from key educational texts. Retrieves top-3 relevant chunks based on user queries, supporting AC_V9-only, Montessori-only, or Blended retrieval modes.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, curriculum contexts, adaptive learning data, and RAG document chunks. In-memory session state. Lesson plan export to PDF and DOCX.
- **Adaptive Learning System (Node.js - Development Only)**: An Express.js server managing self-updating AI prompts, semantic logging, feedback, trending keywords, and subject calibration. Features a REST API for generation, feedback, and analytics, with an auto-refresh system for prompt updates.
- **Core Features**:
  - **Dual Interface**: Teacher and student modes for lesson planning, observation, and AI tutoring.
  - **Chat Conversation Management**: Sidebar-based system for creating, renaming, deleting, and reopening conversations with full message context persistence in PostgreSQL. Auto-creates conversation records on first message to ensure thread persistence across all interfaces (student, companion, planning). Analytics tracked in backend only (not visible to users).
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