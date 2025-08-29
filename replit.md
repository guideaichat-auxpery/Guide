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
- **AI Integration**: OpenAI API client (GPT-4o) for natural language processing.
- **Prompt Engineering**: Dynamic system prompts based on selected curriculum framework.
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
- **Montessori Curriculum Australia**: Refers to the broader child-centered educational methodology and developmental stages.