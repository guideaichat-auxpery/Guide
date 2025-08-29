# Overview

Guide is a cosmic curriculum companion built with Streamlit that bridges Montessori's Cosmic Education philosophy with contemporary curriculum frameworks. The application integrates systems thinking and interconnected learning approaches, helping teachers create meaningful learning experiences that connect to the larger patterns of life and the universe. It supports both Australian Curriculum V9 and Montessori Curriculum Australia frameworks through an AI-powered interface that emphasizes warm, humble, and practical guidance.

# User Preferences

Preferred communication style: Simple, everyday language.
Philosophy: Montessori Cosmic Education and systems thinking approach - emphasizing interconnections, big ideas, patterns, and the child's place in the universe story.
Tone: Warm, humble, practical, avoiding jargon while honoring developmental stages and student agency.

# Recent Changes (August 27, 2025)

## Comprehensive Curriculum Integration Enhancement
- **Cross-Curriculum Priorities V9**: Embedded complete framework for Sustainability, Asia and Australia's Engagement with Asia, and Aboriginal and Torres Strait Islander Histories and Cultures with all organising ideas
- **General Capabilities V9**: Integrated full learning continuums for all seven capabilities (Literacy, Numeracy, Digital Literacy, Critical and Creative Thinking, Personal and Social Capability, Intercultural Understanding, Ethical Understanding)
- **Enhanced System Prompts**: Updated AI responses to reference authentic terminology from cross-curriculum priorities and general capabilities, ensuring comprehensive curriculum alignment
- **Cosmic Education Integration**: All new content connects to Montessori's cosmic education principles, showing how capabilities and priorities support the grand narrative of universal development

## Accessibility Wizard Implementation (August 28, 2025)
- **Universal Design for Learning**: Comprehensive accessibility wizard available to both teachers and students for customizing the learning interface
- **Visual Accessibility**: Font size adjustment (Small to Extra Large), contrast modes (Standard, High Contrast, Dark Mode, Low Light), dyslexia-friendly fonts, reduced motion options
- **Cognitive Support**: Simplified interface option, focus mode, ADHD support with chunked content, memory support with visual cues, reading comprehension aids
- **Motor & Navigation**: Enhanced keyboard navigation, screen reader optimization for assistive technology compatibility
- **Audio Support**: Text-to-speech integration placeholder for future multimedia accessibility
- **Adaptive Content Formatting**: AI responses automatically format based on user accessibility preferences (ADHD chunking, reading support highlighting, memory visual cues)
- **Persistent Settings**: Accessibility preferences saved across sessions with reset-to-defaults option
- **Universal Access**: Available to all user roles (teachers and students) with comprehensive CSS styling system for real-time interface adaptation

## Student Work Feedback System Implementation (August 28, 2025)
- **Multi-Modal File Support**: Students can upload text files, PDFs, images, audio recordings, and presentation slides for feedback
- **AI-Powered Analysis**: Comprehensive feedback system using GPT-4o mini to analyze student work with constructive, growth-oriented responses
- **Curriculum-Aligned Feedback**: Feedback connects to Australian Curriculum V9 or Montessori learning goals and outcomes
- **Accessibility Integration**: All feedback automatically formats based on student's accessibility preferences (ADHD chunking, reading support, etc.)
- **Learning Journey Integration**: Feedback submissions automatically link to student progress tracking and CEC competency development
- **Feedback History**: Students can review previous feedback to track their growth and learning progression
- **Next Steps Guidance**: Interactive options for reflection, asking follow-up questions, and portfolio integration
- **Constructive Focus**: Feedback emphasizes strengths, practical next steps, and connections to bigger learning goals rather than evaluation

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
- **Curriculum Document Upload**: File upload system supporting .txt, .csv, .pdf, .docx files for enhanced AI responses with custom curriculum content
- **Montessori National Curriculum Integration**: Embedded official 2011 Montessori National Curriculum document provides authentic reference throughout all AI responses, ensuring alignment with official Montessori principles and developmental frameworks
- **Comprehensive Australian Curriculum V9 Integration**: Complete embedding of official curriculum documents across all major learning areas including:
  - English (Language, Literature, Literacy strands)
  - HASS F-6 and Years 7-10 specialised subjects (Civics & Citizenship, Economics & Business, Geography, History)
  - Mathematics (Number, Algebra, Measurement, Geometry, Statistics, Probability)
  - Science (Biological, Chemical, Earth/Space, Physical sciences)
  - Technologies (Design and Technologies, Digital Technologies with Systems/Design/Computational thinking)
  - Indonesian Language (Second Language Learner pathway)
  - Health and Physical Education (Personal/Social/Community Health, Movement/Physical Activity)
  All with authentic terminology, achievement standards, content descriptions, focus areas, and assessment approaches
- **Enhanced Scope & Sequence Creation**: Comprehensive learning progressions with choice between explicit/siloed learning areas or concept/theme-based integration, supporting AC V9 only, MNC only, or blended approaches with cosmic education priority
- **Unified Learning Invitations & Connections**: Merged tool combining learning invitations and connections with age group adjustment capabilities and integrated GPT-4o mini chat for teacher refinement and curation
- **Learning Threads & Patterns**: Interconnected topic mapping showing relationships rather than linear sequences with enhanced curriculum framework selection
- **Family & Community Connection**: Parent communication highlighting whole-child development and cosmic perspective with multiple communication types and tones
- **Student Work Analysis**: AI-powered feedback on student work that celebrates discoveries and suggests meaningful extensions
- **Skill Development**: Personalized learning pathways based on student interests and demonstrated understanding
- **Enhanced Assessment Rubrics System**: Advanced curriculum-aligned rubric generator with comprehensive configuration:
  - **Flexible Year Selection**: Single year, Montessori 3-year cycles (Cycle 1: 3-6, Cycle 2: 6-9, Cycle 3: 9-12, Cycle 4: 12-15), and multi-year ranges
  - **Multi-Curriculum Support**: Australian Curriculum V9, Montessori Curriculum Australia, or blended approach
  - Learning area selection (8 Australian Curriculum areas + Montessori equivalents)
  - Assessment type options (project-based, performance tasks, portfolio, etc.)
  - Focus area customization (knowledge, skills, understanding, application, cosmic connections)
  - Advanced options (3-5 performance levels, growth-focused/standards-based styles, language complexity)
  - Persistent rubric library with robust file-based storage and error handling
  - Team collaboration features for sharing rubrics with commenting system
- **Progress Tracking**: Holistic student progress monitoring with learning journey reports that honor individual development
- **Cosmic Education Competencies (CEC)**: Competency-based tracking system inspired by International Big Picture Learning with 6 core competencies adapted for cosmic education
- **Real-World Learning Portfolio**: Track internships, exhibitions, community projects, and authentic learning experiences
- **CEC Competency Visualization**: Radar chart profiles showing progression across Knowing How to Learn, Empirical Reasoning, Quantitative Reasoning, Social Reasoning, Communication, and Personal Qualities with cosmic education themes
- **Asset-Based Assessment**: Focus on "how the student is smart" rather than deficit-based evaluation
- **Learner Profile Generation**: Comprehensive profiles combining academic progress with real-world competencies and cosmic consciousness
- **Student Activity Linking**: Automatic connection between student interface activities and their progress profiles, tracking submissions, feedback, and competency development
- **Final Work Submissions**: Dedicated submission system for completed projects supporting multiple file types (PDF, DOC, images, audio, video) with integrated reflection and CEC assessment
- **Multimedia File Processing**: Comprehensive support for various file formats with automatic content analysis and integration into student learning profiles
- **Portfolio System**: Comprehensive portfolio creation and management with multiple templates (blank, themed, subject-based, year-level, term-based)
- **Portfolio Templates**: Pre-designed structures including blank canvas for custom layouts, themed organization by big ideas, subject-based learning areas, yearly tracking, and term-specific focus
- **Entry Annotation System**: Students can annotate their portfolio entries with learning reflections and growth observations over time
- **Portfolio Reflection Tools**: Built-in reflection prompts and tools for students to document their learning journey and identify patterns in their growth
- **Team Collaboration Hub**: Comprehensive collaboration system featuring:
  - Shared rubrics library with team commenting
  - Shared lesson plans and learning connections
  - Team activity feed showing recent sharing and collaboration
  - Resource discovery across teaching teams
- **Accessibility Wizard**: Universal design for learning interface allowing comprehensive customization for diverse learners including visual, cognitive, motor, and audio accessibility needs with adaptive content formatting
- **Student Work Feedback System**: Comprehensive multi-modal feedback system for students to upload and receive constructive feedback on written work, images, audio recordings, and presentation slides with AI-powered analysis and learning-focused guidance

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
- **Comprehensive Australian Curriculum V9**: Complete integration of official government education standards across all major learning areas:
  - English (Language, Literature, Literacy strands)
  - HASS F-6 and Years 7-10 (Civics & Citizenship, Economics & Business, Geography, History)
  - Mathematics (all strands with visual resources)
  - Science (all sciences with investigation processes)
  - Technologies (Design and Digital with thinking frameworks)
  - Indonesian Language (Second Language Learner pathway)
  - Health and Physical Education (health and movement focus areas)
  - The Arts - Visual Arts (elements/principles, 2D/3D/4D processes, cultural practices, ICIP protocols)
  - **Cross-Curriculum Priorities**: Sustainability, Asia and Australia's Engagement with Asia, Aboriginal and Torres Strait Islander Histories and Cultures with full organising ideas and frameworks
  - **General Capabilities**: Literacy, Numeracy, Digital Literacy, Critical and Creative Thinking, Personal and Social Capability, Intercultural Understanding, Ethical Understanding with complete learning continuums
  Includes authentic terminology, achievement standards, content descriptions, glossaries, and visual learning resources
- **Montessori National Curriculum (2011)**: Official Montessori Australia Foundation curriculum framework integrated throughout the system, providing authentic reference for the three planes of development, Cosmic Education approach, and developmental characteristics
- **Montessori Curriculum Australia**: Child-centered educational methodology and developmental stages