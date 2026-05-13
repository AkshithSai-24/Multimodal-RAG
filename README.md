# 🧠 MultiModal RAG

A full-stack **Retrieval-Augmented Generation (RAG)** application that understands and answers questions about text, tables, images, slides, PDFs, web pages, YouTube videos, and more — all through a sleek chat interface.

Built with **FastAPI** + **ChromaDB** on the backend and **React (Vite)** on the frontend.

---

## ✨ Features

- **Multimodal ingestion** — PDFs, DOCX, PPTX, images, CSV, web URLs, YouTube transcripts, and raw text
- **Vision model support** — uses NVIDIA's Llama 4 Maverick to understand images and slides
- **Semantic search** — NVIDIA embedding model with ChromaDB vector store
- **Configurable Top-K retrieval** — choose how many documents to retrieve per query directly from the UI
- **Source citations** — every answer shows the exact chunks (with modality, page number, and similarity score) that were used
- **Zero-config frontend** — paste your free API keys in the UI; no `.env` editing required

---

## 🗂 Project Structure

```
multimodal_rag/
├── backend/
│   ├── api/routes/         # FastAPI route handlers (ingest, query, config, health)
│   ├── config/             # Pydantic settings
│   ├── core/               # Embeddings, LLM clients, RAG chain, vector store
│   ├── loaders/            # File-type loaders (PDF, DOCX, PPTX, CSV, web, YouTube…)
│   ├── models/             # Pydantic schemas & document models
│   ├── processors/         # Image, table, text, multimodal processors
│   ├── mcp/                # Google Drive MCP integration
│   ├── utils/              # File utilities, logger
│   └── main.py             # FastAPI app entry point
└── frontend/
    └── src/
        ├── components/
        │   ├── KeysPanel.jsx       # API key entry with free-key references
        │   ├── DataSourcePanel.jsx # Ingest UI (file, URL, YouTube, text)
        │   ├── QueryPanel.jsx      # Chat interface with Top-K selector
        │   └── IngestionStatus.jsx # Post-ingest summary
        ├── api.js          # Backend API client
        └── App.jsx         # Root app & state management
```

---

## 🔑 API Keys (both are free)

| Key | Where to get it |
|-----|-----------------|
| **NVIDIA API Key** | [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys) |
| **OpenRouter API Key** | [openrouter.ai/docs/api/reference/authentication](https://openrouter.ai/docs/api/reference/authentication) |

Both providers offer a free tier — no credit card required to get started.

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/multimodal-rag.git
cd multimodal-rag
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r ./backend/requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend starts at `http://localhost:8000`. API docs are at `http://localhost:8000/docs`.

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 4. Configure API keys in the UI

1. Paste your **NVIDIA API Key** and **OpenRouter API Key** in the **API Keys** panel.
2. Click **Initialise Backend** — this writes a `.env` to the running backend.
3. Ingest a data source (file, URL, YouTube, or text).
4. Ask questions in the chat — adjust **Top-K** to control how many document chunks are retrieved per query.

---

## ⚙️ Environment Variables

You can also configure the backend manually by editing `backend/.env`:

```env
# Required
NVIDIA_API_KEY=nvapi-...
OPENROUTER_API_KEY=sk-or-...

# Models
LLM_MODEL=openai/gpt-oss-20b:free
VISION_MODEL=meta/llama-4-maverick-17b-128e-instruct
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-1b-v2

# Vector store
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=multimodal_rag

# Retrieval
TOP_K=6
MAX_IMAGE_DOCS=3
INCLUDE_IMAGES_IN_RESPONSE=true

# Server
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
CORS_ORIGINS=["*"]

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Upload
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50
```

---

## 📡 API Reference

### Health

```
GET /health
```

### Ingest

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest/file` | POST (multipart) | Upload a local file |
| `/ingest/url` | POST | Crawl a web page |
| `/ingest/youtube` | POST | Transcribe a YouTube video |
| `/ingest/text` | POST | Ingest raw text |
| `/ingest/collections` | GET | List all collections |
| `/ingest/collections/{name}` | DELETE | Delete a collection |
| `/ingest/reset` | POST | Delete all collections |

### Query

```http
POST /query
Content-Type: application/json

{
  "query": "What is the main topic?",
  "top_k": 6,
  "include_images": true,
  "collection_name": null
}
```

Response:
```json
{
  "answer": "...",
  "sources": [...],
  "model_used": "meta/llama-4-maverick-17b-128e-instruct"
}
```

### Config

```
POST /config/env   — upload a .env file to reconfigure the backend at runtime
```

---

## 🛠 Supported File Types

| Type | Extensions |
|------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |
| Spreadsheet | `.csv` |
| Image | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` |
| Web | any URL (with configurable crawl depth) |
| Video | YouTube URLs (transcript extraction) |
| Text | plain text via the UI |

---

## 🧩 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — async REST API
- [ChromaDB](https://www.trychroma.com/) — local vector store
- [LangChain](https://python.langchain.com/) — LLM orchestration
- [NVIDIA NIM](https://build.nvidia.com/) — embeddings & vision
- [OpenRouter](https://openrouter.ai/) — LLM routing

**Frontend**
- [React](https://react.dev/) + [Vite](https://vitejs.dev/)
- [Lucide React](https://lucide.dev/) — icons
- [react-markdown](https://github.com/remarkjs/react-markdown) — markdown rendering

---

## 📄 License

MIT 

---

Developed by **Akshith Sai Kondamadugu**