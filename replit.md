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
- **Data Privacy & Security (December 2025)**:
  - **PII Sanitization**: All messages sent to OpenAI are sanitized to remove student names, emails, phone numbers, addresses before API calls.
  - **File Upload Security**: Server-side MIME validation, 10MB size limit, and filename sanitization for all uploads.
  - **Audit Logging**: EducatorAuditLog model tracks educator actions on student data with timestamps and action details.
- **Session Management**: Enhanced Streamlit configuration with 2-hour session timeout, automatic conversation restoration on login, and visual save confirmations.
- **Frontend**: Streamlit-based with chat, curriculum selector, file upload, and accessibility wizard.
- **Backend**: Single-file Python application (`app.py`) integrating OpenAI API.
- **AI Integration**: Uses OpenAI API (GPT-4o-mini) with dynamic system prompts for various features:
    - **Student Research Assistant**: Provides year-level adaptive AI tutoring in Structure/Scaffold or Research modes, with enhanced source filtering prioritizing educational domains and specific Australian resources.
    - **Age-Appropriate Lesson Planning**: AI assistant provides developmental stage-specific, highly detailed lesson plans with mandatory differentiation and cross-curricular connections, aligning with Australian Curriculum V9 and Montessori frameworks.
    - **Professional Development Expert**: A restricted-access, advanced PD coaching system.
    - **Imaginarium (Creative Space)**: Free-form creative space for brainstorming and innovative lesson concepts with high creativity and extended conversation history.
- **RAG System**: Hybrid semantic and keyword document retrieval using PostgreSQL pgvector and OpenAI embeddings, enhanced with metadata filtering for year level and subject.
- **Data Management**: PostgreSQL for persistence of conversation history, analytics, planning notes, and RAG document chunks. Supports PDF and DOCX export. **NEW - Professional PDF Export (December 2025)**: Enhanced print-friendly A4 formatting with professional header (Guide by AUXPERY branding + date), improved typography, justified text alignment, better table formatting, comprehensive bullet/list marker handling, and branded footer.
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