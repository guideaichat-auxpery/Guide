# Overview

Guide is a Streamlit-based cosmic curriculum companion that assists educators in integrating Montessori's Cosmic Education with contemporary frameworks like the Australian Curriculum V9. It offers AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe, aiming to foster holistic learning for both educators and students.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## UI/UX Decisions
- **Framework**: Streamlit with a wide layout and dual-mode interface (educator and student).
- **Design System**:
  - **Montessori Theme**: Warm earth tones, specific fonts (Cormorant Garamond, Inter), organic rounded corners, soft shadows, and smooth transitions.
  - **Danish Eco-Design Theme**: Clean modernist educator dashboard with off-white background, muted forest green accent, soft grey text, Inter typography, rounded corners, generous whitespace, and card-based navigation. Features a fixed header, welcoming greeting, 3x2 grid of interactive feature cards, and an account section. Fully responsive with WCAG 2.1 AA accessibility compliance. Uses emoji icons as a pragmatic compromise.
  - **Mobile Responsiveness**: Fully responsive design with mobile-first approach. Breakpoints: tablets (≤768px), phones (≤480px). Features include: stacked columns on mobile, full-width buttons and forms, font size reduction on smaller screens (16px→14px→13px), dynamic padding/spacing, and touch-friendly targets (44-48px). Dashboard cards: 3x2 grid on desktop, 2-column on tablet, single column on mobile. Chat and sidebar adapt to narrow viewports.
- **Streamlit Rerun Architecture**: Critical UI Placement Pattern ensures static UI elements (quick prompts, file uploaders, interactive cards) render BEFORE chat history loops to prevent mid-conversation insertion during Streamlit reruns.

## Technical Implementations
- **Authentication**: Email/password for educators and username/password for students, with bcrypt hashing and session management, compliant with Australian Privacy Act 1988.
- **Session Management**: Enhanced Streamlit configuration with extended session timeout (2 hours), automatic conversation restoration on login, visual save confirmations, and user-friendly error messages.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and an accessibility wizard. Session-based state management with PostgreSQL-backed persistence.
- **Backend**: Single-file Python application (`app.py`) for core logic, integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts and comprehensive error handling.
  - **Error Handling System**: Centralized error classification (APIError class) with user-friendly messages for rate limits, timeouts, server errors, network issues, and content filters. Includes exponential backoff retry logic, network connectivity detection, and expandable help suggestions for common issues.
  - **Retry Mechanism**: Automatic retry with exponential backoff (1s → 2s → 4s) for transient errors (rate limits, timeouts, 5xx errors). Maximum 3 retries before showing user-friendly error message.
  - **Student Research Assistant**: Year-level adaptive AI tutor with dual-mode responses (Structure/Scaffold Mode for essay breakdowns, Research Mode for 3-part answers). Enhanced source filtering provides alternative search phrasings and stable homepage URLs, prioritizing Australian and international educational sources.
  - **Age-Appropriate Lesson Planning**: AI assistant provides developmental stage-specific prompts with strict curriculum framework rules and highly detailed step-by-step instructions. All lesson plans include actionable "Suggestions for Further Refinement & Development." Framework priority varies by age group (Australian Curriculum V9 for 12-15, Montessori for Foundation-Year 6).
  - **Professional Development Expert**: Restricted-access, advanced PD coaching system with self-learning memory.
  - **Imaginarium (Creative Space)**: Free-form creative space for educators with high creativity, longer responses, and extended conversation history, designed for brainstorming and innovative concept development.
- **RAG System**: Hybrid semantic + keyword document retrieval with metadata filtering using PostgreSQL pgvector and OpenAI text-embedding-3-small. Features include increased retrieval count, curriculum code hybrid search, query expansion, enhanced metadata organization (year level, subject), and robust fallback mechanisms. Supports AC_V9-only, Montessori-only, or Blended modes.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, curriculum contexts, adaptive learning data, and RAG document chunks. Lesson plan export to PDF and DOCX.
- **Adaptive Learning System (Development Only)**: Express.js server for managing self-updating AI prompts, semantic logging, feedback, trending keywords, and subject calibration via a REST API.
- **Stripe Subscription Integration**: Webhook-based subscription management for user access control, handling `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, and `invoice.payment_failed` events. Subscription status stored in session state and displayed in the sidebar.
- **Email Notification Service** (`email_service.py`): Transactional email system supporting SendGrid and SMTP backends with graceful fallback. Sends:
  - **Welcome Emails**: Automatically sent after educator signup with onboarding guidance
  - **Subscription Confirmation**: Sent immediately after successful Stripe checkout with plan details and amount
  - **Renewal Reminders**: Sent on subscription renewal (invoice.paid webhook) with next renewal date and plan information
  - Emails gracefully disabled if no email service configured (non-blocking)
- **Help & Support System**: Two-interface system for user feedback and support:
  - **Feedback Interface** (`show_feedback_interface()`): Bug reports with severity levels (Low/Medium/High) and feature requests, stored in `feedback_tickets` table
  - **Support Contact Form** (`show_support_contact_interface()`): Subscription, billing, account, and general support inquiries stored in `subscription_contacts` table
  - Dashboard buttons ("Send Feedback" and "Support") for easy access
- **Core Features**:
  - **Dual Interface**: Teacher and student modes.
  - **Chat Conversation Management**: Sidebar-based system for creating, renaming, deleting, and reopening conversations, with auto-loading of the most recent conversation and real-time message persistence. Student chats include mandatory subject selection.
  - **Curriculum Integration**: Incorporates Australian Curriculum V9 and Montessori National Curriculum (2011), rooted in Montessori's Cosmic Education.
  - **AI-Powered Tools**: Includes Great Story Creator, Planning Notes Workspace, Educator Observation Dashboard, Lesson Planning Assistant, Big Picture Curriculum Mapping, Student Work Analysis, Imaginarium, and Rubric Generator.
  - **Document Upload & Analysis**: Educators can upload teaching materials (TXT, PDF, DOCX, JPG, PNG) for Montessori-focused AI feedback. Students can upload assignments for constructive feedback. Handles scanned/textless PDFs gracefully.
  - **Accessibility**: Universal Design for Learning interface.

# Market Readiness Features (Completed)

1. **User Onboarding** ✓ - 5-step welcome tour, sample lesson plans, first-time feature prompts
2. **Error Handling** ✓ - User-friendly messages, exponential backoff retry (1s→2s→4s), network detection, help suggestions
3. **Mobile Responsiveness** ✓ - Full responsive design with breakpoints at 768px/480px, stacked layouts, touch-friendly targets
4. **Help & Support System** ✓ - Feedback/bug reports and support contact forms with database persistence
5. **Email Notifications** ✓ - Welcome emails, subscription confirmations, and renewal reminders via SendGrid/SMTP

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o-mini model for natural language generation (British English spelling).

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