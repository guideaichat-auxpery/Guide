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
- **Cosmic Curriculum Integration**: Responses rooted in Montessori's Cosmic Education philosophy with systems thinking approach
- **Learning Connections**: AI-generated lesson ideas that link topics to larger systems (historical, ecological, social, economic)
- **Learning Threads & Patterns**: Interconnected topic mapping showing relationships rather than linear sequences
- **Family & Community Connection**: Parent communication highlighting whole-child development and cosmic perspective
- **Learning Invitations**: Student activities fostering independence, collaboration, real-world connection, and cosmic reflection

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