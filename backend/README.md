# MultiModal RAG Backend

A production-ready **Multi-modal Retrieval-Augmented Generation** backend built with FastAPI.  
Supports ingesting text, images, tables, and slides from multiple sources via MCP and direct loaders, storing them in a Chroma vector database, and answering questions with a vision-capable LLM through OpenRouter.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│                                                                 │
│  POST /ingest/*          POST /query                            │
│       │                       │                                 │
│       ▼                       ▼                                 │
│  ┌──────────┐          ┌─────────────┐                         │
│  │ Loaders  │          │  RAG Chain  │                         │
│  │  Web     │          │  (core/)    │                         │
│  │  PDF     │          └──────┬──────┘                         │
│  │  DOCX    │                 │ retrieve                        │
│  │  PPTX    │          ┌──────▼──────┐                         │
│  │  Image   │          │   Chroma    │                         │
│  │  CSV     │◄────────►│  Vector DB  │                         │
│  │  YouTube │  store   └─────────────┘                         │
│  │  GDrive  │                                                   │
│  └────┬─────┘                                                   │
│       │ raw chunks                                              │
│       ▼                                                         │
│  ┌──────────────────────┐                                       │
│  │ MultiModal Processor │                                       │
│  │  ├─ TextProcessor    │  split long text/tables               │
│  │  ├─ ImageProcessor   │  vision LLM → rich descriptions       │
│  │  └─ TableProcessor   │  LLM → semantic table descriptions    │
│  └──────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

### What makes it Multi-modal?

| Modality | At Ingest | At Query |
|----------|-----------|----------|
| **Text** | Split into chunks, embedded | Retrieved by semantic similarity |
| **Table** | Converted to Markdown + LLM description | Retrieved + included as structured context |
| **Image** | Vision LLM generates rich description; base64 stored in metadata | Description retrieved; original image optionally sent to vision LLM |
| **Slide** | Text + notes extracted; slide images processed by vision LLM | Multi-modal context assembled |

---

## Project Structure

```
multimodal_rag_backend/
├── main.py                    # FastAPI app entry point
├── requirements.txt
├── .env.example
│
├── config/
│   └── settings.py            # All config via env vars (pydantic-settings)
│
├── models/
│   ├── document.py            # DocumentChunk, RetrievedChunk, RAGResponse
│   └── schemas.py             # API request/response schemas
│
├── core/
│   ├── embeddings.py          # Google Generative AI embeddings (text-embedding-004)
│   ├── llm.py                 # ChatOpenRouter (text + vision)
│   ├── vectorstore.py         # Chroma manager (async wrappers)
│   └── rag_chain.py           # Multi-modal RAG pipeline
│
├── loaders/
│   ├── base_loader.py         # Abstract base
│   ├── web_loader.py          # requests + trafilatura + BS4
│   ├── pdf_loader.py          # pypdf + pdfplumber + pymupdf
│   ├── docx_loader.py         # python-docx
│   ├── pptx_loader.py         # python-pptx
│   ├── image_loader.py        # Pillow
│   ├── csv_loader.py          # pandas
│   ├── youtube_loader.py      # youtube-transcript-api
│   └── loader_factory.py      # Auto-detect loader by file/URL
│
├── processors/
│   ├── text_processor.py      # RecursiveCharacterTextSplitter
│   ├── image_processor.py     # Vision LLM summaries (async batched)
│   ├── table_processor.py     # LLM table descriptions
│   └── multimodal_processor.py# Orchestrator
│
├── mcp/
│   ├── base_client.py         # JSON-RPC 2.0 over HTTP
│   ├── gdrive_client.py       # Google Drive MCP client
│   └── registry.py            # MCP server registry
│
└── api/routes/
    ├── health.py
    ├── ingest.py              # All /ingest/* endpoints
    └── query.py               # /query and /query/search
```

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** If `langchain-openrouter` is not yet available on PyPI, install it from source:
> ```bash
> pip install git+https://github.com/langchain-ai/langchain-openrouter
> ```
> Or configure `langchain-openai` with OpenRouter base URL instead (see `core/llm.py`).

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set both keys:
#   OPENROUTER_API_KEY=sk-or-...   (from https://openrouter.ai/keys)
#   GOOGLE_API_KEY=AIza...         (from https://aistudio.google.com/app/apikey)
```

### 3. Run the server

```bash
python main.py
# or
uvicorn main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## API Reference

### Ingest

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest/file` | Upload PDF, DOCX, PPTX, image, CSV, … |
| POST | `/ingest/url` | Scrape a website (shallow crawl supported) |
| POST | `/ingest/gdrive` | Import a Google Drive file by ID |
| POST | `/ingest/text` | Ingest raw text |
| POST | `/ingest/youtube` | Ingest YouTube transcript |
| GET | `/ingest/collections` | List Chroma collections |
| DELETE | `/ingest/collections/{name}` | Delete a collection |

### Query

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Multi-modal RAG — retrieval + generation |
| POST | `/query/search` | Raw similarity search (no LLM) |

### Example: Ingest a PDF

```bash
curl -X POST http://localhost:8000/ingest/file \
  -F "file=@report.pdf" \
  -F "collection_name=my_docs"
```

### Example: Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key findings in the quarterly report?",
    "collection_name": "my_docs",
    "top_k": 6,
    "include_images": true
  }'
```

---

## Supported Sources

| Source | Loader | Modalities |
|--------|--------|-----------|
| PDF | `PDFLoader` | Text, Table, Image |
| DOCX | `DOCXLoader` | Text, Table, Image |
| PPTX | `PPTXLoader` | Slide (text+notes), Table, Image |
| Web URL | `WebLoader` | Text, Image |
| Image (PNG/JPEG/…) | `ImageLoader` | Image |
| CSV / Excel | `CSVLoader` | Text (schema), Table |
| YouTube | `YouTubeLoader` | Text (transcript) |
| Google Drive | `GDriveClient` via MCP | Delegates to above loaders |

---

## Adding New Sources

1. Create `loaders/my_loader.py` extending `BaseLoader`
2. Register it in `loaders/loader_factory.py`
3. Add an endpoint in `api/routes/ingest.py`

---

## Deployment (Vercel)

This backend is designed to be deployed separately from the frontend.

1. Add a `vercel.json`:
```json
{
  "builds": [{"src": "main.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "main.py"}]
}
```
2. Set all environment variables in the Vercel dashboard.
3. Use a hosted Chroma instance (e.g. Chroma Cloud) by updating `CHROMA_PERSIST_DIR`.

---

## Environment Variables

See `.env.example` for the full list. Two keys are required:

| Variable | Where to get it |
|---|---|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| `GOOGLE_API_KEY` | https://aistudio.google.com/app/apikey |
