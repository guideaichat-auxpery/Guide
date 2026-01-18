# Overview
Guide is a Streamlit-based cosmic curriculum companion that bridges Montessori's Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. It provides AI-powered guidance for creating interconnected learning experiences, emphasizing systems thinking and a child's place in the universe. The application aims to foster holistic learning and development by offering tailored resources and insights to educators and students, promoting a vision of integrated learning and global citizenship.

# User Preferences
Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## UI/UX Decisions
- **Framework**: Streamlit with a wide layout and dual-mode interface (educator and student).
- **Design System**: Montessori-themed interface with warm earth tones and a Danish Eco-Design theme for the educator dashboard, emphasizing clean modern aesthetics, accessibility (WCAG 2.1 AA), and responsive design. Includes dark mode and enhanced mobile responsiveness.
- **Login Experience**: Clear tab-based separation for Educator and Student login.
- **Sidebar UX**: Redesigned conversation sidebar with warm earth-tone gradient background, new chat button, hover-to-reveal edit/delete actions, floating toggle button, date grouping for conversation history, and AI auto-titling.
- **Streamlit Rerun Architecture**: Static UI elements render before chat history for consistent display.

## Technical Implementations
- **Authentication**: Email/password for educators and username/password for students, with bcrypt hashing, session management, and compliance with Australian Privacy Act 1988. Features password security, login rate limiting, guardian consent for student accounts, and comprehensive password management.
- **Admin System**: `is_admin` column on users table, bypassing subscription checks for admin users, and admin tools for user lookup and password reset.
- **Data Privacy & Security**: PII sanitization for OpenAI API calls, server-side file upload security, audit logging for educator actions on student data, and data retention compliance (7 years for student records, 25 years for child safety records).
- **Session Management**: Inactivity timeouts (2 hours for students, 30 minutes for educators), automatic conversation restoration, and persistent login via cookie-based session tokens.
- **Subscription & Payments**: Simplified Stripe integration using Python SDK for user-facing operations. Features bulletproof subscription verification with grace access, manual re-verification, visible status indicators, pricing tiers, Stripe Checkout for payment, and Stripe Customer Portal for self-service management. Integrated with marketing site for signup-first flow.
- **Email Integration**: Automated transactional emails via Resend for welcome, password reset, and contact form auto-reply.
- **Child Safety Measures**: Content monitoring for concerning student messages with alerts to educators, confidential student reporting, and complete data deletion functionality.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and accessibility wizard.
- **Backend**: Single-file Python application integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts for various features: Student Research Assistant, Age-Appropriate Lesson Planning, Professional Development Expert, and Imaginarium.
- **RAG System**: Hybrid semantic and keyword document retrieval using PostgreSQL pgvector and OpenAI embeddings, with metadata filtering.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, and RAG document chunks. Supports professional PDF and DOCX export, and GDPR data export in JSON format.
- **Student Learning Journey Map**: Visual learning progress tracker showing explored curriculum topics, summary metrics, interactive nodes, and subject exploration sections.
- **Core Features**: Dual Teacher/Student Interface, Chat Conversation Management, Curriculum Integration (Australian Curriculum V9, Montessori National Curriculum), AI-Powered Tools (Great Story Creator, Lesson Planning Assistant, etc.), Document Upload & Analysis, and Universal Design for Learning.

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o-mini model.

## Python Libraries
- **streamlit**
- **pandas**
- **plotly.express & plotly.graph_objects**
- **openai**
- **datetime**
- **reportlab & python-docx**

## Curriculum Frameworks
- **Australian Curriculum V9**
- **Montessori National Curriculum (2011)**