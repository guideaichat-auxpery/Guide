# Overview

Guide is an AI-powered curriculum assistant built with Streamlit that helps teachers create lesson plans, generate activities, and communicate with parents. The application supports both Australian Curriculum V9 and Montessori Curriculum Australia frameworks, providing contextual guidance through an interactive chat interface powered by OpenAI's GPT-4o model.

# User Preferences

Preferred communication style: Simple, everyday language.

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
- **Curriculum Adaptation**: Context-aware responses based on Australian Curriculum V9 or Montessori frameworks
- **Lesson Planning**: AI-generated lesson ideas aligned to selected curriculum
- **Scope & Sequence**: CSV-based topic visualization with timeline charts
- **Communication Tools**: Parent letter and information sheet generation
- **Activity Generation**: Age-appropriate task suggestions for primary and middle years

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