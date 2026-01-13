# Lia Support Bot (Stateful)

## Project Overview

Lia Support Bot is a stateful AI-powered chatbot designed to provide digital trust support for eMudhra, a leading provider of Digital Signature Certificates (DSC), SSL certificates, USB tokens, and related PKI services. The bot, named "Lia," assists users with inquiries related to DSC applications, status tracking, troubleshooting, installation guides, and more. It integrates with various backend systems to offer verified, tool-driven responses and can seamlessly hand over conversations to live human agents when necessary.

### Key Features

- **User Authentication & Verification**: Supports OTP-based mobile number verification for secure access to user-specific application details.
- **AI-Powered Responses**: Utilizes LangChain and OpenAI's GPT-4o-mini model to generate accurate, context-aware responses based on a comprehensive knowledge base.
- **Knowledge Base Integration**: Leverages Retrieval-Augmented Generation (RAG) with vectorized FAQ and error documents stored in Google Docs.
- **PII Masking**: Automatically masks sensitive information like Aadhaar numbers, PAN cards, and mobile numbers in chat logs for privacy compliance.
- **Live Agent Handover**: Detects when human intervention is required and forwards the conversation to Ameyo-powered live support agents.
- **Application Status & Details Fetching**: Retrieves and displays real-time application details, timelines, and payment status from eMudhra's API.
- **Shipment Tracking**: Integrates with Shiprocket to track USB token deliveries.
- **Persistent Chat History**: Maintains session-based chat history for contextual conversations.
- **Frontend Chat Widget**: Provides a user-friendly, embeddable chat interface with typing indicators, message bubbles, and responsive design.

### Workflow

1. **Initialization**: User enters their registered 10-digit mobile number.
2. **OTP Verification**: System sends OTP via eMudhra's API and verifies it.
3. **Auto-Fetch Details**: Upon verification, automatically fetches and displays application details (if available).
4. **AI Interaction**: User interacts with Lia for queries related to DSC, SSL, tokens, etc. Responses are generated using RAG tools and hardcoded knowledge.
5. **Handover**: If the query requires human assistance, the bot triggers a handover to live agents via Ameyo API.
6. **Logging & Persistence**: All interactions are logged to a PostgreSQL database with PII masking.

## Technological Stack

### Backend
- **Language**: Python 3.x
- **Framework**: FastAPI (for building the REST API)
- **AI/ML**:
  - LangChain (for agent orchestration and tool integration)
  - OpenAI GPT-4o-mini (LLM for response generation)
- **Database**: PostgreSQL (for chat logging and user data)
- **Integrations**:
  - Ameyo API (for live agent messaging and handover)
  - Shiprocket API (for shipment tracking)
  - eMudhra Internal API (for application details and OTP)
  - Google Docs API (for knowledge base retrieval)
- **Libraries**:
  - Pydantic (for data validation)
  - Requests (for HTTP calls)
  - UUID, JSON, RE, Time (standard libraries)
  - Dotenv (for environment variable management)
  - Logging (for application logging)
- **Security**: CORS middleware for cross-origin requests, PII masking for data protection

### Frontend
- **Languages**: HTML5, CSS3, JavaScript (ES6+)
- **Features**: Responsive chat widget with floating toggle button, message display, typing indicators, and modal dialogs
- **Assets**: Custom CSS for styling, JavaScript for interactivity, image assets (e.g., eMudhra logo)

### Infrastructure & Tools
- **Environment Management**: dotenv for configuration
- **Vector Store**: Custom RAG implementation with chunking (size: 800, overlap: 150) for document retrieval
- **Deployment**: Designed for containerization (e.g., Docker), with configurable host/port settings
- **Development Tools**: Logger configuration for structured logging, test API endpoints for development

### External Dependencies
- OpenAI API (for LLM inference)
- Google Docs (for FAQ and error document storage)
- Ameyo (for live chat integration)
- Shiprocket (for logistics tracking)
- eMudhra APIs (for core business logic)

This stack enables a robust, scalable, and secure chatbot solution tailored for digital trust services.
