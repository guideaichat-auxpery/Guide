# Overview

Guide is a Streamlit-based cosmic curriculum companion bridging Montessori's Cosmic Education with contemporary curriculum frameworks. It assists educators in creating interconnected learning experiences aligned with the Australian Curriculum V9 and Montessori Curriculum Australia. The application provides AI-powered, warm, humble, and practical guidance, emphasizing systems thinking and a child's place in the universe. It aims to foster holistic learning and development, supporting both educators and students with tailored resources and insights.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Frontend
- **Framework**: Streamlit (wide layout) with dual-mode interface (educator and student) featuring chat, curriculum selector, file upload, and accessibility wizard.
- **State Management**: Session-based for conversation history, curriculum selection, and uploaded content with separate contexts for educators and students.
- **Visualization**: Plotly for charts and timelines.

## Backend
- **Core Logic**: Single-file Python application (`app.py`) with modular functions.
- **AI Integration**: OpenAI API client (GPT-4o-mini) with dynamic system prompts based on selected curriculum and role-based optimization.
- **Conversation Management**: Intelligent 10-message rolling history and dynamic curriculum context injection.
- **Token Optimization**: Enhanced token limits (3000 for educators, 800 for students).
- **Curriculum Keyword Extraction**: Sophisticated multi-word phrase detection system with year-specific topic mapping - recognizes official AC V9 topic names (e.g., "Geographies of Interconnections", "Making a Nation", "Biomes and Food Security") and automatically infers appropriate year levels (Year 7-9) from detected curriculum content. System prioritizes longest phrases first to prevent overlap, supports singular/plural variations, and injects detected keywords into AI context for enhanced alignment.
- **Intelligent Year Level Inference**: Automatic year level detection based on curriculum topic keywords - when Year 9-specific topics like "Geographies of Interconnections" are mentioned, system overrides default Year 8 and selects Year 9, ensuring age-appropriate content delivery.
- **Trending Topics System**: Real-time curriculum keyword tracking that detects AC V9 topics in student queries, stores trending keywords by subject in PostgreSQL, and dynamically injects trending topics into AI system prompts to enhance response relevance and curriculum alignment - builds contextual awareness across student sessions.
- **Anonymous Query Logging**: Privacy-focused student query tracking with UUID session IDs, detected keyword metadata, and anonymized data storage - enables analytics while protecting student privacy.
- **File Processing**: Supports `.txt`, `.csv`, `.pdf`, `.docx`, images, audio, and presentation files for AI integration.

## Adaptive Learning System (Node.js)
- **Architecture**: Standalone Express.js server running on port 3000 alongside Streamlit (port 5000)
- **Core Components**:
  - **adaptiveCore.js**: Main orchestrator coordinating all adaptive subsystems
  - **adaptivePromptManager.js**: Self-updating AI prompts based on feedback patterns - dynamically evolves system prompts when 10+ feedback samples indicate need for adjustment
  - **semanticLogger.js**: Hybrid Replit KV + PostgreSQL embeddings system - persistent Replit KV database (@replit/database) for fast writes with workflow survival, 30-second auto-sync to PostgreSQL for analytics; OpenAI embeddings-based interaction logging with k-means clustering for topic discovery; UUID-based collision-proof keys; race condition prevention with sync guard
  - **feedbackSystem.js**: Hybrid Replit KV + PostgreSQL feedback system - persistent Replit KV database for fast writes with workflow survival, 30-second auto-sync to PostgreSQL for analytics; emoji-based sentiment tracking (🤩=excellent, 😕=confused, 📚=curriculum-aligned, 🌍=Montessori-cosmic) with weight calculation; UUID-based collision-proof keys; race condition prevention with sync guard
  - **trendingKeywords.js**: Hybrid Replit KV + PostgreSQL trending curriculum topics system - persistent Replit KV database for fast keyword recording with workflow survival, 30-second auto-sync with intelligent UPDATE-or-INSERT logic (increments count for existing keywords), dynamic weight calculation (1 + total/50, capped at 1.5) for curriculum alignment boost; UUID-based collision-proof keys; race condition prevention with sync guard; composite index on (subject, keyword) for efficient lookups at scale
  - **subjectCalibrator.js**: Dynamic weight adjustment system balancing Montessori philosophy (0.7), curriculum alignment (0.6), scaffolding (0.5), and complexity (0.6) with optional trending topics boost multiplier
  - **analyticsRoute.js**: REST API with 10+ endpoints for dashboard, trends, student profiles, and system analytics
  - **server.js**: Express server with auto database initialization and 72-hour auto-refresh cycle
- **Database Tables**: 
  - `adaptive_interactions`: Query/response pairs with embeddings
  - `adaptive_feedback`: Emoji and rating-based feedback with sentiment weights
  - `adaptive_prompts`: Versioned prompt history per subject
  - `adaptive_weights`: Subject-specific calibration weights
  - `trending_keywords`: Curriculum keyword tracking with count aggregation and dynamic weights (composite index on subject+keyword)
  - `system_config`: Configuration storage for auto-refresh timestamps
- **Auto-Refresh System**: 72-hour cycle with hourly checks - dynamically discovers active subjects from database, updates prompts based on accumulated feedback patterns, tracks refresh timestamp in system_config table
  - **Helpfulness-Based Refresh**: Calculates helpfulness ratios from feedback (weight ≥0.6 = helpful), generates Montessori GuideChat-style prompts with targeted improvement instructions for subjects below 50% helpful threshold
  - **Dynamic Prompt Storage**: Stores generated prompts in system_config as `systemPrompt_dynamic` for persistent, evolving system guidance
- **REST API**: Available at `http://localhost:3000/api` with endpoints for generation, feedback, analytics, weight management, and trending topics
  - `/api/simple-feedback`: Simplified rating endpoint (1-5 scale) with subject/student association and validation
  - `/api/message`: Message pipeline integration logging semantic vectors and returning adaptive prompts
  - `/api/kv-feedback`: Fast Replit KV-based feedback recording with auto-sync to PostgreSQL
  - `/api/kv-store`: View current persistent Replit KV store size and keys for feedback
  - `/api/kv-sync`: Manual sync trigger for KV entries to PostgreSQL
  - `/api/kv-embeddings`: View embedding Replit KV store size and keys
  - `/api/kv-embeddings-sync`: Manual sync trigger for embedding entries to PostgreSQL
  - `/api/trending/record`: Fast curriculum keyword recording to persistent Replit KV store
  - `/api/trending/kv-store`: Monitor trending keywords Replit KV store
  - `/api/trending/kv-sync`: Manual sync trigger for trending keywords to PostgreSQL
  - `/api/trending/subject/:subject`: Get trending keywords and dynamic weight for subject
  - `/api/trending/all`: Get all trending keywords across subjects
  - `/api/trending/stats`: Aggregated statistics for trending keywords
  - `/api/trending/keyword/:keyword`: Historical data for specific keyword
  - `/analytics`: Simplified real-time analytics showing current Replit KV state (feedback, embeddings, trending keywords)
- **Self-Improvement**: System automatically updates prompts and adjusts weights based on student feedback patterns

## Data Management
- **Persistence**: PostgreSQL for conversation history, educator analytics, student activities, great stories, planning notes, curriculum contexts, and adaptive learning data.
- **Session State**: In-memory storage for current session data.
- **Export Capabilities**: Lesson plan export to PDF and DOCX using Montessori-themed templates.

## Core Features
- **Dual Interface**: Teacher and student modes with parallel feature sets:
  - **Educator Mode**: Full lesson planning, curriculum alignment review, observation dashboards, and advanced tools
  - **Student Mode**: AI tutor with curriculum-aligned support, file upload for homework help, multi-subject selection, intelligent year level inference (Years 6-9), privacy notice banner, and anonymous query tracking with trending curriculum topics
- **Curriculum Integration**: Incorporates Australian Curriculum V9 and Montessori National Curriculum (2011), with AI responses rooted in Montessori's Cosmic Education.
- **Age-to-Year-Level Mapping**: Automatic translation of age groups to AC year levels (6-9→Years 1-3, 9-12→Years 4-6, 12-15→Years 7-9) with visual display.
- **Comprehensive Subject Coverage**: Age-appropriate multiselect subject selector - HASS (Humanities and Social Sciences) for Foundation-Year 6; separate History, Geography, Business and Economics, Civics and Citizenship for Years 7-9; plus English, Mathematics, Science, Design and Technologies, Digital Technologies, The Arts, Health and Physical Education, Languages for cross-curricular planning.
- **V9 Enforcement**: Explicit Australian Curriculum VERSION 9 enforcement - all codes must start with "AC9" (e.g., AC9S6H01), never V8.4 codes.
- **Age-Appropriate Outputs**: Mandatory cognitive development matching - Foundation-Year 3 (concrete, simple), Years 4-6 (transitional, guided), Years 7-9 (abstract, independent).
- **AI-Powered Tools**:
    - **Great Story Creator**: AI-assisted Montessori Great Story development with persistent storage.
    - **Planning Notes Workspace**: Word processor-style planning tool with organization, materials management, and image upload.
    - **Educator Observation Dashboard**: Student activity tracking with multi-educator access.
    - **Lesson Planning Assistant**: Creates specific activities and lessons, and analyzes existing ones.
    - **Curriculum Alignment Review**: Intelligent document analysis tool that appears when files are uploaded and "Curriculum Alignment Review" planning type is selected - uses sophisticated keyword recognition to detect AC V9 topics, automatically infers year levels, and provides comprehensive alignment feedback against AC V9 and MNC with specific citations, detected keywords display, year-level appropriateness assessment, and actionable improvement recommendations.
    - **Big Picture Curriculum Mapping**: Maps knowledge connections for long-term planning.
    - **Student Work Analysis**: AI-powered multi-modal feedback using a blended curriculum approach.
- **Assessment & Tracking**: Advanced rubric generator, holistic student progress tracking, CEC competency visualization (radar charts), asset-based assessment, and learner profile generation.
- **Portfolio System**: Creation and management of student portfolios with various templates and chronological tracking.
- **Collaboration**: Team Collaboration Hub for shared resources.
- **Accessibility**: Universal Design for Learning interface with comprehensive customization.
- **Mathematics Hub**: Dedicated tools for cosmic math connections and inquiry-driven approaches.
- **Provocational Framework**: Expert-informed design emphasizing adolescent sophistication - responses must frame dilemmas/tensions (not just topics), begin with real Australian provocations, use mature philosophical tone, expect autonomy/real-world engagement, avoid childish activities for adolescents, and self-assess against a 10-point checklist including AC V9 codes, General Capabilities, First Nations perspectives, and Montessori third-plane alignment.

# External Dependencies

## AI Services
- **OpenAI API**: Uses GPT-4o model for natural language generation. Requires `OPENAI_API_KEY` environment variable.

## Python Libraries
- **streamlit**: Web application framework.
- **pandas**: Data manipulation (CSV processing).
- **plotly.express & plotly.graph_objects**: Interactive visualizations.
- **openai**: Official OpenAI Python client.
- **datetime**: Date and time handling.
- **reportlab & python-docx**: PDF and DOCX export.

## Curriculum Frameworks
- **Comprehensive Australian Curriculum V9**: Integrated official government education standards.
- **Montessori National Curriculum (2011)**: Integrated official Montessori Australia Foundation framework.
- **Dr. Montessori's Own Handbook**: Integrated foundational Montessori text.
- **The Absorbent Mind**: Integrated foundational Montessori text on child development.
- **The Montessori Method**: Integrated seminal Montessori work on pedagogy.
- **Montessori Curriculum Australia**: Broader child-centered educational methodology.