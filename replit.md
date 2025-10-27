# Overview

Guide is a Streamlit-based cosmic curriculum companion bridging Montessori's Cosmic Education with contemporary curriculum frameworks. It assists educators in creating interconnected learning experiences aligned with the Australian Curriculum V9 and Montessori Curriculum Australia. The application provides AI-powered guidance, emphasizing systems thinking and a child's place in the universe. It aims to foster holistic learning and development, supporting both educators and students with tailored resources and insights.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# Privacy & Compliance

**Australian Privacy Act 1988 Compliance:**
- Comprehensive privacy policy addressing all 13 Australian Privacy Principles (APPs)
- Consent tracking: All user consents are recorded with timestamps and policy versions for auditing
- Parental consent mechanism for students under 18 with auditable records
- Overseas disclosure notices: Users explicitly consent to OpenAI (US) data transfer (APP 8)
- Data retention policy: 2 years for conversations/analytics, 3 years for inactive accounts (APP 11.2)
- Automated data cleanup runs daily to enforce retention periods
- User rights implementation: Data access (export), correction, and deletion features (APP 12/13)
- Privacy notices displayed at signup for educators and student creation

**Database Tables for Compliance:**
- `consent_records`: Tracks all user consents (data collection, overseas transfer, privacy policy)
- `parental_consent_records`: Tracks parental consent for student accounts with educator ID, timestamp, and consent method

# System Architecture

## Authentication
- Email/password authentication for educators and username/password for students with bcrypt hashing and session management.
- Privacy compliant with consent tracking for data collection, overseas transfer, and privacy policy agreement.

## Frontend
- **Framework**: Streamlit (wide layout) with dual-mode interface (educator and student) featuring chat, curriculum selector, file upload, and accessibility wizard.
- **Design System**: Montessori-inspired visual theme with warm earth tones, specific fonts (Cormorant Garamond, Inter), organic rounded corners, soft shadows, and smooth transitions. CSS loaded via `static/css/montessori-theme.css` with Streamlit theme configuration.
- **State Management**: Session-based for conversation history, curriculum selection, and uploaded content.
- **Visualization**: Plotly for charts and timelines.

## Backend
- **Core Logic**: Single-file Python application (`app.py`) with modular functions.
- **AI Integration**: OpenAI API client (GPT-4o-mini) with dynamic system prompts based on selected curriculum and role-based optimization.
- **Student Research Assistant**: Year-level adaptive AI tutor (Year 7-12) provides structured 3-part responses: (1) Brief Answer (2-4 sentences, factual and neutral), (2) Further Research Directions (2-3 bullet points encouraging deeper thinking), (3) Reliable Sources (2-3 verified educational links). Temperature 0.3 for consistent, accurate responses. Adjusts language complexity: Year 7-8 (simplified), Year 9-10 (balanced), Year 11-12 (academic/analytical). **URL Validation**: Conservative link policy ensures only verified, existing URLs are provided; prefers trusted homepage URLs with search suggestions over potentially broken article links to maintain credibility.
- **Age-Appropriate Lesson Planning**: Intelligent lesson planning assistant with developmental stage-specific prompts:
  - Ages 3-6: Foundational skills, Montessori materials, step-by-step educator guidance
  - Ages 6-9: Literacy/numeracy building, hands-on activities, collaborative learning
  - Ages 9-12: Deeper comprehension, research skills, independent thinking
  - Ages 12-15: Complex ideas, inquiry-based learning, ethical dilemmas, systems thinking
- **Conversation Management**: Intelligent 10-message rolling history and dynamic curriculum context injection.
- **Token Optimization**: Enhanced token limits (6000 for educators, 800 for students).
- **Curriculum Keyword Extraction**: Multi-word phrase detection system with year-specific topic mapping, prioritizing longest phrases and supporting singular/plural variations. Automatically infers year levels and injects detected keywords into AI context.
- **Intelligent Year Level Inference**: Automatic year level detection based on curriculum topic keywords.
- **Trending Topics System**: Real-time curriculum keyword tracking, storing data in PostgreSQL, and dynamically injecting trending topics into AI system prompts.
- **Anonymous Query Logging**: Privacy-focused student query tracking with UUID session IDs and anonymized data storage.
- **File Processing**: Supports `.txt`, `.csv`, `.pdf`, `.docx`, images, audio, and presentation files.

## Adaptive Learning System (Node.js)
- **Architecture**: Standalone Express.js server running on port 3000 alongside Streamlit (port 5000) with a centralized dependency injection pattern.
- **Core Components**: Manages self-updating AI prompts, semantic logging (Replit KV + PostgreSQL with OpenAI embeddings), feedback (Replit KV + PostgreSQL with emoji-based sentiment), trending keywords (Replit KV + PostgreSQL), and subject calibration.
- **Database Tables**: `adaptive_interactions`, `adaptive_feedback`, `adaptive_prompts`, `adaptive_weights`, `trending_keywords`, `system_config`.
- **Auto-Refresh System**: 72-hour cycle with hourly checks to dynamically update prompts based on feedback patterns, storing generated prompts in `system_config`.
- **REST API**: Available at `http://localhost:3000/api` with endpoints for generation, feedback, analytics, weight management, and trending topics. **Note**: Development-only service for adaptive prompts; not required for production deployment.
- **Self-Improvement**: System automatically updates prompts and adjusts weights based on student feedback patterns.

## Professional Development Expert (Python)
- **Architecture**: Python-based implementation integrated directly into Streamlit app (`utils.py`) for production compatibility.
- **Implementation**: `call_pd_expert()` function eliminates inter-service dependencies by calling OpenAI API directly.
- **Memory System**: PostgreSQL `pd_expert_memory` table stores conversation history with 30-day retention and automatic cleanup.
- **Features**: Self-learning memory (summarizes prior focus), contextual keyword analysis, comprehensive 6-section responses (800-1500 words).
- **Access Control**: Restricted to `guideaichat@gmail.com` only.
- **Performance**: 6000 max_tokens, 120-second timeout, British English conventions.
- **Production Ready**: No localhost dependencies, works in both development and published deployments.

## RAG System (Retrieval-Augmented Generation)
- **Architecture**: Semantic document retrieval system using PostgreSQL pgvector extension and OpenAI embeddings.
- **Implementation**: `rag_system.py` for ingestion and retrieval, integrated into `call_openai_api()` in `utils.py`.
- **Database Table**: `document_chunks` stores 196 embedded chunks from 7 source files (Australian Curriculum V9, General Capabilities, Cross-Curriculum Priorities, Montessori National Curriculum, Montessori's Own Handbook, The Absorbent Mind, The Montessori Method).
- **Embedding Model**: OpenAI text-embedding-3-small (1536 dimensions) with pgvector HNSW index for fast cosine similarity search.
- **Retrieval**: Top-3 most relevant chunks retrieved based on user queries (76% similarity for Montessori queries, 66% for AC V9 queries in tests).
- **Framework-Aware Filtering**: Supports AC_V9-only, Montessori-only, or Blended retrieval modes based on curriculum_type parameter.
- **Context Injection**: Retrieved chunks automatically formatted and injected as system messages before AI response generation.
- **Error Handling**: Silent failures (returns empty context) to preserve user experience; errors logged for debugging.
- **Chunking**: ~800 tokens per chunk with 100-token overlap for context preservation.
- **Production Status**: Core functionality operational with identified improvements (caching, configurable parameters, enhanced error handling) documented for future optimization.

## Data Management
- **Persistence**: PostgreSQL for conversation history, educator analytics, student activities, great stories, planning notes, curriculum contexts, adaptive learning data, and PD Expert memory.
- **Session State**: In-memory storage for current session data.
- **Export Capabilities**: Lesson plan export to PDF and DOCX using Montessori-themed templates.
- **PD Expert Memory Table**: `pd_expert_memory` stores professional development prompts for self-learning memory system (user_email, prompt, created_at with 30-day retention).

## Core Features
- **Dual Interface**: Teacher and student modes with features like lesson planning, observation dashboards (educator), and AI tutor with file upload and anonymous tracking (student).
- **Curriculum Integration**: Incorporates Australian Curriculum V9 and Montessori National Curriculum (2011), with AI responses rooted in Montessori's Cosmic Education.
- **Age-to-Year-Level Mapping**: Automatic translation of age groups to AC year levels with visual display.
- **Comprehensive Subject Coverage**: Age-appropriate multiselect subject selector for various subjects across different year levels.
- **V9 Enforcement**: Explicit Australian Curriculum VERSION 9 enforcement (all codes must start with "AC9").
- **Age-Appropriate Outputs**: Mandatory cognitive development matching for Foundation-Year 3, Years 4-6, and Years 7-9.
- **Pure Montessori Companion**: Authentic Montessori philosophical companion with age-specific guidance (3-6, 6-9, 9-12, 12-15) or comprehensive all-ages support. Rooted in Dr. Montessori's foundational texts, providing teacher training, philosophical guidance, and practical implementation across all developmental planes WITHOUT curriculum alignment or government standards.
- **AI-Powered Tools**: Includes Great Story Creator (branching narratives), Planning Notes Workspace (with materials list and image attachments), Educator Observation Dashboard, Lesson Planning Assistant (with three modes: Lesson Planning, Scope & Sequence Creation, and Assessment Rubric), Big Picture Curriculum Mapping, and Student Work Analysis.
- **Assessment & Tracking**: Advanced rubric generator, holistic student progress tracking, CEC competency visualization, asset-based assessment, and learner profile generation.
- **Portfolio System**: Creation and management of student portfolios.
- **Collaboration**: Team Collaboration Hub for shared resources.
- **Accessibility**: Universal Design for Learning interface.
- **Mathematics Hub**: Dedicated tools for cosmic math connections.
- **Provocational Framework**: Design emphasizing adolescent sophistication, focusing on real Australian provocations, mature philosophical tone, and adherence to a 10-point checklist.
- **Professional Development Expert Mode**: Restricted-access advanced PD coaching system for authorized educators with 25-50 years of simulated experience. **Production-ready Python implementation** with self-learning memory (PostgreSQL `pd_expert_memory` table), contextual keyword analysis, and comprehensive 6-section responses (Summary, Evidence-Based Insights, Detailed Approach, Montessori Connections, Implementation Timeline, Practical Examples). Includes Harvard Instructional Moves, Edutopia strategies, adult learning theory (Knowles, Kolb, Schön, Wenger), and Montessori-aligned coaching. 6000 token limit for 800-1500+ word in-depth guidance with 120-second timeout for comprehensive responses. Direct OpenAI API integration eliminates inter-service dependencies for reliable deployment. **Access:** guideaichat@gmail.com (password: pdexpert123)

# External Dependencies

## AI Services
- **OpenAI API**: Uses GPT-4o-mini model for natural language generation.
- **Language Convention**: All AI outputs use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.)

## Python Libraries
- **streamlit**: Web application framework.
- **pandas**: Data manipulation.
- **plotly.express & plotly.graph_objects**: Interactive visualizations.
- **openai**: Official OpenAI Python client.
- **datetime**: Date and time handling.
- **reportlab & python-docx**: PDF and DOCX export.

## Curriculum Frameworks
- **Comprehensive Australian Curriculum V9**: Official government education standards.
- **Montessori National Curriculum (2011)**: Official Montessori Australia Foundation framework.
- **Dr. Montessori's Own Handbook**: Foundational Montessori text.
- **The Absorbent Mind**: Foundational Montessori text.
- **The Montessori Method**: Seminal Montessori work on pedagogy.
- **Montessori Curriculum Australia**: Broader child-centered educational methodology.