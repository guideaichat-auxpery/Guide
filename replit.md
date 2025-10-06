# Overview

Guide is a Streamlit-based cosmic curriculum companion designed to bridge Montessori's Cosmic Education philosophy with contemporary curriculum frameworks. It helps educators create interconnected learning experiences that align with Australian Curriculum V9 and Montessori Curriculum Australia. The application uses AI to provide warm, humble, and practical guidance, emphasizing systems thinking and the child's place in the universe.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit (wide layout)
- **UI Components**: Chat interface, curriculum selector, file upload, accessibility wizard.
- **State Management**: Session-based for conversation history, curriculum selection, and uploaded content.
- **Visualization**: Plotly integration for charts and timelines.

## Backend Architecture
- **Core Logic**: Single-file Python application (`app.py`) with modular functions.
- **AI Integration**: OpenAI API client (GPT-4o-mini) for natural language processing with enhanced parameters.
- **Prompt Engineering**: Dynamic system prompts based on selected curriculum framework with role-based optimization.
- **Conversation History**: Intelligent 10-message rolling history management for multi-turn conversations.
- **Curriculum Context Injection**: Dynamic Australian Curriculum V9 context fetching by subject and year level.
- **Token Optimization**: Enhanced token limits (3000 for educators, 800 for students) for ChatGPT-level detailed responses.
- **File Processing**: Supports `.txt`, `.csv`, `.pdf`, `.docx`, images, audio, and presentation files.

## Data Management
- **Session State**: In-memory storage for current session data.
- **File Handling**: Upload and processing of various file types for AI integration and portfolio.
- **Data Persistence**: Session-based (non-persistent across browser sessions).

## Authentication & Security
- **API Security**: Environment variable-based OpenAI API key management.
- **Error Handling**: Graceful error handling for missing API keys.

## Core Features
- **Dual Interface**: Separate teacher and student modes.
- **Cosmic Curriculum Integration**: Responses rooted in Montessori's Cosmic Education and systems thinking.
- **Curriculum Document Upload**: Allows custom curriculum content for enhanced AI responses.
- **Comprehensive Curriculum Integration**: Embeds official Australian Curriculum V9 (including Cross-Curriculum Priorities and General Capabilities) and Montessori National Curriculum (2011).
- **Scope & Sequence Creation**: Supports AC V9, MNC, or blended approaches, with cosmic education priority.
- **Great Story Creator**: AI-assisted Montessori Great Story development with theme-based creation, age-appropriate targeting, story outlines, and narrative suggestions. Persistent storage tied to educator accounts.
- **Planning Notes Workspace**: Comprehensive word processor-style planning tool with chapter/section organization, materials management, image upload support, and persistent storage.
- **Educator Observation Dashboard**: Student activity tracking system with multi-educator access control, activity timelines, engagement metrics, and real-time updates.
- **Learning Invitations & Connections**: Tool for creating and curating learning experiences.
- **Learning Threads & Patterns**: Interconnected topic mapping.
- **Family & Community Connection**: Facilitates parent communication with a cosmic perspective.
- **Student Work Analysis**: AI-powered multi-modal feedback system focusing on growth and next steps. Always uses blended curriculum approach (AC V9 + Montessori) for consistency.
- **Skill Development**: Personalized learning pathways.
- **Assessment Rubrics System**: Advanced, configurable rubric generator supporting multiple curricula and assessment types.
- **Progress Tracking**: Holistic student monitoring, including Learning Journey Reports and CEC competency tracking.
- **CEC Competency Visualization**: Radar charts for progress across key competencies.
- **Asset-Based Assessment**: Focus on student strengths.
- **Learner Profile Generation**: Comprehensive profiles combining academic progress, competencies, and cosmic consciousness.
- **Portfolio System**: Creation and management of student portfolios with various templates, annotation features, and chronological work timeline tracking. Timestamps all portfolio uploads for My Journey timeline view. Enhanced file upload system supporting documents, images, audio, and video files.
- **Team Collaboration Hub**: Features shared rubrics, lesson plans, and resource discovery.
- **Accessibility Wizard**: Universal Design for Learning interface with comprehensive customization for diverse visual, cognitive, motor, and audio needs.
- **Mathematics Hub**: Dedicated mathematics learning tools for teachers and students, featuring cosmic math connections, mathematical investigations, pattern exploration, and inquiry-driven approaches that connect mathematics to the cosmic story and natural phenomena.
- **Enhanced Learning Tools**: Renamed and redesigned tools for clarity: "Lesson Planning Assistant" (creates specific activities and lessons, plus analyzes existing lessons for feedback and remodeling) and "Big Picture Curriculum Mapping" (maps knowledge connections for long-term planning). Both tools feature intuitive, self-directive interfaces with step-by-step guidance.

# External Dependencies

## AI Services
- **OpenAI API**: Uses GPT-4o model for natural language generation and guidance.
- **API Key**: `OPENAI_API_KEY` environment variable is required.

## Python Libraries
- **streamlit**: For building the web application.
- **pandas**: For data manipulation, specifically CSV processing.
- **plotly.express & plotly.graph_objects**: For interactive charts and visualizations.
- **openai**: Official OpenAI Python client.
- **datetime**: For date and time handling.

## Curriculum Frameworks
- **Comprehensive Australian Curriculum V9**: Integrated official government education standards across all major learning areas, including Cross-Curriculum Priorities and General Capabilities.
- **Montessori National Curriculum (2011)**: Integrated official Montessori Australia Foundation framework.
- **Dr. Montessori's Own Handbook**: Integrated Maria Montessori's authentic handbook covering sensory education, motor education, writing, arithmetic, and moral factors in child development.
- **The Absorbent Mind**: Integrated Maria Montessori's foundational work on child development, covering the unique mental powers of young children and their natural learning processes from birth to six years.
- **The Montessori Method**: Integrated Maria Montessori's seminal work on scientific pedagogy, discipline through liberty, prepared environments, and practical life applications in the Children's Houses.
- **Montessori Curriculum Australia**: Refers to the broader child-centered educational methodology and developmental stages.

# Recent Changes

## October 6, 2025 - Enhanced AI Chat System with Curriculum Context
- **Conversation History Management**: Intelligent rolling history (last 10 exchanges) for natural multi-turn conversations across all chat interfaces
- **Curriculum Context Injection**: Dynamic AC V9 content descriptor fetching by subject (Science, Mathematics, English) and year level (Years 1-6)
- **Enhanced Token Limits**: Increased to 3000 tokens for educators and 800 for students, enabling ChatGPT-level detailed responses
- **Improved System Prompts**: Role-based prompts for educators and students based on GuideChat implementation with structured, detailed guidance
- **Enhanced API Parameters**: Temperature (0.75), presence penalty (0.3), and frequency penalty (0.2) for balanced, diverse responses
- **Student Curriculum Selector**: Optional subject/year level selector in student interface for curriculum-aligned learning support
- **Montessori Integration**: All curriculum contexts include Montessori material connections and cosmic education links

## October 6, 2025 - Great Stories & Planning Notes System
- **Montessori Great Story Creator**: AI-assisted cosmic education story development tool with theme-based creation, age-appropriate targeting, and persistent storage
- **Planning Notes Workspace**: Comprehensive planning workspace with chapter organization, materials management, image upload support, and word processor functionality
- **Educator Observation System**: Complete student activity tracking with multi-educator access control, activity timelines, and engagement metrics
- **Database Enhancements**: Added GreatStory and PlanningNote models with full CRUD operations
- **Navigation Improvements**: Streamlined educator dashboard with dedicated sections for Great Stories and Planning Notes
- **Code Optimization**: Fixed import errors, updated API call structure, and improved error handling

## September 10, 2025 - Complete Montessori Reference Database Integration
- **Complete Integration**: Successfully integrated all three foundational Montessori texts into the curriculum reference database:
  - "Dr. Montessori's Own Handbook" - sensory education, motor education, and moral development
  - "The Absorbent Mind" - child psychology, developmental stages, and natural learning processes
  - "The Montessori Method" - scientific pedagogy, practical applications, and prepared environments
- **Enhanced AI Responses**: All AI interactions now reference authentic Montessori methodology from Maria Montessori's complete foundational works
- **Comprehensive Cosmic Education**: Responses are deeply grounded in both contemporary Montessori curricula and Maria Montessori's original pedagogical philosophy, ensuring authentic guidance rooted in proven developmental science