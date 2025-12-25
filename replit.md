# Overview
Guide is a Streamlit-based cosmic curriculum companion that bridges Montessori's Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development by offering tailored resources and insights to educators and students, promoting a vision of integrated learning and global citizenship.

# User Preferences
Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## UI/UX Decisions
- **Framework**: Streamlit with a wide layout and dual-mode interface (educator and student).
- **Design System**: Features a Montessori-themed interface with warm earth tones for general elements and a Danish Eco-Design theme for the educator dashboard, emphasizing clean modern aesthetics, accessibility (WCAG 2.1 AA), and responsive design.
- **Streamlit Rerun Architecture**: Static UI elements are strategically placed to render before chat history to ensure consistent display during Streamlit reruns.

## Technical Implementations
- **Authentication**: Email/password for educators and username/password for students, with bcrypt hashing and session management, compliant with Australian Privacy Act 1988.
  - **Password Security (December 2025)**: Minimum 12 characters with complexity requirements (uppercase, lowercase, number).
  - **Login Rate Limiting (December 2025)**: 5 failed attempts triggers 15-minute account lockout. Tracked in `login_attempts` table.
  - **Guardian Consent (December 2025)**: Mandatory checkbox attestation when creating student accounts with consent record stored (educator ID, timestamp, attestation text).
  - **Password Management (December 2025)**:
    - **Change Password**: In Account Settings, users can change their password by entering current password + new password with validation.
    - **Forgot Password**: Login page displays contact email (guide@auxpery.com.au) for password reset requests.
    - **Admin Password Reset**: Admin users can look up any user by email and reset their password via Admin Tools section.
  - **Admin System (December 2025)**:
    - **Admin Account**: is_admin column on users table, admin@auxpery.com.au account with ADMIN_PASSWORD env var.
    - **Subscription Bypass**: Admin users skip all Stripe/subscription checks, have full access to all features.
    - **Admin Tools**: User lookup and password reset functionality in Account Settings (only visible to admins).
- **Data Privacy & Security (December 2025)**:
  - **PII Sanitization**: All messages sent to OpenAI are sanitized to remove student names, emails, phone numbers, addresses before API calls.
  - **File Upload Security**: Server-side MIME validation, 10MB size limit, and filename sanitization for all uploads.
  - **Audit Logging**: EducatorAuditLog model tracks educator actions on student data with timestamps and action details.
- **Session Management (December 2025)**:
  - 2-hour inactivity timeout for students (classroom-appropriate session length)
  - 30-minute inactivity timeout for educators (protects student data access)
  - Automatic conversation restoration on login, visual save confirmations.
- **Subscription & Payments (December 2025)**:
  - **Simplified Stripe Architecture (December 2025)**: Direct Python Stripe SDK (`stripe_client.py`) for all user-facing operations (checkout, portal, subscription sync). Node.js payments service (port 3001) now only handles webhooks and marketing site token verification.
  - **Bulletproof Subscription Verification (December 2025)**: Session-based verification with grace access:
    - At login: Check Stripe directly, store result in session (`subscription_verified`, `subscription_active`, `subscription_plan`, `subscription_status`)
    - If Stripe succeeds: Mark verified, trust for entire session
    - If Stripe errors: Grant GRACE ACCESS (subscription_active=True), don't mark verified (auto-retries on next navigation)
    - This ensures Stripe outages or webhook delays NEVER block paying users
  - **Grace Access Mode**: When Stripe API is unavailable, users are granted temporary access with "⏳ Verifying..." status indicator
  - **Manual Re-verify**: "Verify Subscription" button in sidebar expander for users who just subscribed
  - **Visible Status Indicator**: Sidebar shows current subscription plan with status (✅ verified, ⏳ verifying, ❌ none)
  - **Pricing**: $15/month with 14-day trial OR $150/year (2 months free)
  - **Subscription Gate**: Educators must have active subscription to access app features
  - **Checkout Flow**: Stripe Checkout for secure payment processing (via Python Stripe client)
  - **Billing Portal**: Self-service subscription management via Stripe Customer Portal
  - **Webhook Handling**: Real-time subscription status updates (created/updated/cancelled) via Node.js service (non-blocking)
  - **Database Fields**: stripe_customer_id, stripe_subscription_id, subscription_status, trial_ends_at, subscription_last_checked on users table
  - **Marketing Site Integration (December 2025)**: Sign-up-first flow where users create account on guide.auxpery.com.au, then pay through pricing page
    - Simple redirect links from www.auxpery.com.au to guide.auxpery.com.au for signup
    - After signup, users see pricing page and complete Stripe Checkout
    - Subscription automatically activated upon payment completion
    - Optional public API: POST `/api/public/create-checkout-session` for pre-signup payments on marketing site
    - See `MARKETING_SITE_INTEGRATION.md` for frontend implementation guide
- **Child Safety Measures (December 2025)**:
  - **Content Monitoring**: SafetyAlert model detects concerning content (self-harm, bullying, abuse indicators) in student messages. Keywords classified by severity (high/medium/low). Educators receive alerts for review.
  - **Student Reporting**: "Need to talk to someone?" expander in student interface allows students to confidentially report concerns to their educator.
  - **Data Retention Compliance**: 7-year retention for student records and conversations (Australian education baseline), 25-year retention for child safety records, permanent audit logs.
  - **Complete Data Deletion**: `delete_student_and_data()` provides cascade deletion of student + activities + conversations + consent records with permanent audit trail.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and accessibility wizard.
- **Backend**: Single-file Python application (`app.py`) integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts for various features:
    - **Student Research Assistant**: Provides year-level adaptive AI tutoring in Structure/Scaffold or Research modes, with enhanced source filtering prioritizing educational domains and specific Australian resources.
    - **Age-Appropriate Lesson Planning**: AI assistant provides developmental stage-specific, highly detailed lesson plans with mandatory differentiation and cross-curricular connections, aligning with Australian Curriculum V9 and Montessori frameworks.
    - **Professional Development Expert**: A restricted-access, advanced PD coaching system.
    - **Imaginarium (Creative Space)**: Free-form creative space for brainstorming and innovative lesson concepts with high creativity and extended conversation history.
- **RAG System**: Hybrid semantic and keyword document retrieval using PostgreSQL pgvector and OpenAI embeddings, enhanced with metadata filtering for year level and subject.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, and RAG document chunks. Supports PDF and DOCX export. **NEW - Professional PDF Export (December 2025)**: Enhanced print-friendly A4 formatting with professional header (Guide by AUXPERY branding + date), improved typography, justified text alignment, better table formatting, comprehensive bullet/list marker handling, and branded footer.
- **NEW - GDPR Data Export (December 2025)**: Users can download all their data in JSON format via sidebar expander. Exports include profile info, lesson plans, stories, planning notes, conversations, and usage analytics. Excludes sensitive fields (password hashes, internal IDs).
- **NEW - Dark Mode (December 2025)**: Toggle in sidebar switches between light (default warm Montessori) and dark themes. Dark theme uses Montessori-inspired muted earth tones. Preference stored in session state.
- **NEW - Mobile Responsive (December 2025)**: Enhanced touch targets (minimum 44px per WCAG 2.1), improved sidebar behavior, column stacking on small screens, and reduced-motion support for accessibility.
- **NEW - Student Learning Journey Map (December 2025)**: Visual Plotly network graph for students showing explored curriculum topics as nodes (sized by frequency, colored by subject with Montessori earth tones) with interconnecting edges. Tabbed interface in student view ("Research Assistant" | "My Learning Journey"). Features topic extraction from chat history, expandable subject lists, and empty state guidance for new students. Supports Montessori Cosmic Education philosophy of interconnected learning.
- **Core Features**:
    - **Dual Interface**: Teacher and student modes for various educational tasks.
    - **Chat Conversation Management**: Sidebar-based system for creating, renaming, deleting, and reopening conversations with real-time persistence and subject-based organization for students.
    - **Curriculum Integration**: Incorporates Australian Curriculum V9 and Montessori National Curriculum (2011), rooted in Montessori's Cosmic Education.
    - **AI-Powered Tools**: Includes Great Story Creator, Planning Notes, Educator Observation Dashboard, Lesson Planning Assistant, Big Picture Curriculum Mapping, Student Work Analysis, Imaginarium, and an advanced Rubric Generator.
    - **Document Upload & Analysis**: Educators and students can upload various file types (TXT, PDF, DOCX, JPG, PNG) for AI feedback and analysis through a Montessori lens, with robust handling for scanned documents.
    - **Accessibility**: Universal Design for Learning interface.

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o-mini model.

## Python Libraries
- **streamlit**: Web application framework.
- **pandas**: Data manipulation.
- **plotly.express & plotly.graph_objects**: Interactive visualizations.
- **openai**: Official OpenAI Python client.
- **datetime**: Date and time handling.
- **reportlab & python-docx**: PDF and DOCX export.

## Curriculum Frameworks
- **Australian Curriculum V9**
- **Montessori National Curriculum (2011)**
- **Dr. Montessori's Own Handbook**
- **The Absorbent Mind**
- **The Montessori Method**
- **Montessori Curriculum Australia**