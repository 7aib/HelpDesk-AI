# HelpDesk-AI

AI-powered customer support platform with RAG (Retrieval-Augmented Generation), document processing, and embeddable chat widgets.

## Features

- **Chatbot Management** — Create, configure, and manage multiple AI chatbots with custom system prompts, temperature, and model settings
- **RAG Pipeline** — Upload documents (PDF, DOCX, TXT, Markdown) that are automatically chunked, embedded, and indexed for semantic search
- **Q&A Pairs** — Manually add question-answer pairs to the knowledge base
- **Chat Interface** — Real-time chat with conversation history, streaming responses, and typing indicators
- **Embeddable Widget** — Drop a single `<script>` tag to embed a chatbot on any external website
- **UI Customization** — Customize widget colors, welcome message, and placeholder text with a live preview editor
- **REST API** — Full API for chat, documents, knowledge base, and chatbot management

## Tech Stack

- **Backend:** Django 5.1, Django REST Framework, Celery + Redis
- **Database:** PostgreSQL + pgvector (vector similarity search)
- **LLM:** Ollama (llama3.2 default, any model supported)
- **Embeddings:** Sentence Transformers (BAAI/bge-small-en-v1.5 default)
- **Frontend:** Bootstrap 5.3, custom CSS/JS, HTMX-style interactions
- **Auth:** django-allauth (email login)

## Prerequisites

- Python 3.12+
- PostgreSQL 15+ with pgvector extension
- Redis
- Ollama running locally

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd HelpDesk-AI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your database credentials, Redis URL, and Ollama URL.

### 3. Database

```bash
# Create PostgreSQL database
createdb helpdesk

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Pull Ollama model

```bash
ollama pull llama3.2
```

### 5. Run

```bash
# Terminal 1 — Django
python manage.py runserver

# Terminal 2 — Celery worker
celery -A config worker -l info
```

Visit `http://localhost:8000`

## Project Structure

```
HelpDesk-AI/
├── apps/
│   ├── accounts/       # User model, auth, dashboard
│   ├── api/            # REST API endpoints
│   ├── chat/           # Chat interface, conversations, messages
│   ├── chatbots/       # Chatbot CRUD, UI customization
│   ├── core/           # Base models, utilities
│   ├── documents/      # Document upload, processing, chunking
│   ├── embed/          # Embeddable widget (public, no auth)
│   ├── knowledge/      # Knowledge base, Q&A pairs
│   └── rag/            # RAG pipeline, embedding, vector search
├── config/             # Django settings, URLs, Celery config
├── templates/          # All HTML templates
├── static/             # CSS, JS assets
├── requirements/       # Pip requirements (base, dev, prod)
└── manage.py
```

## Embed Widget

Add this to any website:

```html
<script src="http://localhost:8000/embed/widget.js?chatbot=your-chatbot-slug"></script>
```

The widget renders in an iframe with zero dependencies on the host page.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/<chatbot_id>/` | Send message, get response |
| GET | `/api/chatbots/` | List chatbots |
| POST | `/api/chatbots/` | Create chatbot |
| GET | `/api/knowledge/` | List knowledge bases |
| POST | `/api/documents/upload/` | Upload document |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_ENV` | `development` | Settings module |
| `DB_NAME` | `helpdesk` | PostgreSQL database |
| `DB_USER` | `helpdesk` | Database user |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `DEFAULT_LLM` | `llama3.2` | Default LLM model |
| `DEFAULT_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Default embedding model |
