# Overview

Guide is a cosmic curriculum companion built with Streamlit that bridges Montessori's Cosmic Education philosophy with contemporary curriculum frameworks. The application integrates systems thinking and interconnected learning approaches, helping teachers create meaningful learning experiences that connect to the larger patterns of life and the universe. It supports both Australian Curriculum V9 and Montessori Curriculum Australia frameworks through an AI-powered interface that emphasizes warm, humble, and practical guidance.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit with wide layout configuration
- **UI Components**: Chat interface, curriculum selector dropdown, file upload capability
- **State Management**: Session-based state management for conversation history, curriculum selection, and uploaded content
- **Visualization**: Plotly integration for charts and timelines (imported but implementation pending)

## Backend Architecture
- **Core Logic**: Single-file Python application (app.py) with modular helper functions
- **AI Integration**: OpenAI API client with GPT-4o model for natural language processing
- **Prompt Engineering**: Dynamic system prompts that adapt based on selected curriculum framework
- **File Processing**: Support for .txt and .csv file uploads with content integration into AI responses

## Data Management
- **Session State**: In-memory storage for conversation history, curriculum preferences, and uploaded file content
- **File Handling**: Text and CSV file upload capability for curriculum notes and topics
- **Data Persistence**: Session-based (non-persistent across browser sessions)

## Authentication & Security
- **API Security**: Environment variable-based OpenAI API key management
- **Error Handling**: Graceful error handling for missing API keys with user-friendly messages

## Core Features Architecture
- **Dual Interface**: Separate teacher and student-facing modes with appropriate tools for each audience
- **Cosmic Curriculum Integration**: Responses rooted in Montessori's Cosmic Education philosophy with systems thinking approach
- **Learning Connections**: AI-generated lesson ideas that link topics to larger systems (historical, ecological, social, economic)
- **Learning Threads & Patterns**: Interconnected topic mapping showing relationships rather than linear sequences
- **Family & Community Connection**: Parent communication highlighting whole-child development and cosmic perspective
- **Learning Invitations**: Student activities fostering independence, collaboration, real-world connection, and cosmic reflection
- **Student Work Analysis**: AI-powered feedback on student work that celebrates discoveries and suggests meaningful extensions
- **Skill Development**: Personalized learning pathways based on student interests and demonstrated understanding
- **Assessment Rubrics**: Curriculum-aligned rubric generator with Montessori developmental approach and growth-focused language
- **Progress Tracking**: Holistic student progress monitoring with learning journey reports that honor individual development
- **Cosmic Education Competencies (CEC)**: Competency-based tracking system inspired by International Big Picture Learning with 6 core competencies adapted for cosmic education
- **Real-World Learning Portfolio**: Track internships, exhibitions, community projects, and authentic learning experiences
- **CEC Competency Visualization**: Radar chart profiles showing progression across Knowing How to Learn, Empirical Reasoning, Quantitative Reasoning, Social Reasoning, Communication, and Personal Qualities with cosmic education themes
- **Asset-Based Assessment**: Focus on "how the student is smart" rather than deficit-based evaluation
- **Learner Profile Generation**: Comprehensive profiles combining academic progress with real-world competencies and cosmic consciousness
- **Student Activity Linking**: Automatic connection between student interface activities and their progress profiles, tracking submissions, feedback, and competency development
- **Final Work Submissions**: Dedicated submission system for completed projects supporting multiple file types (PDF, DOC, images, audio, video) with integrated reflection and CEC assessment
- **Multimedia File Processing**: Comprehensive support for various file formats with automatic content analysis and integration into student learning profiles
- **Collaborative Planning**: Team lesson sharing with commenting system for collaborative curriculum development

# External Dependencies

## AI Services
- **OpenAI API**: GPT-4o model for natural language generation and curriculum-specific guidance
- **API Key**: Required via OPENAI_API_KEY environment variable

## Python Libraries
- **streamlit**: Web application framework and UI components
- **pandas**: Data manipulation for CSV file processing
- **plotly.express & plotly.graph_objects**: Interactive charts and timeline visualizations
- **openai**: Official OpenAI Python client library
- **datetime**: Date/time handling for timeline features

## Development Environment
- **Python Runtime**: Standard Python environment with package management
- **Environment Variables**: OPENAI_API_KEY for API authentication

## Curriculum Frameworks
- **Australian Curriculum V9**: Government education standards and learning areas
- **Montessori Curriculum Australia**: Child-centered educational methodology and developmental stages