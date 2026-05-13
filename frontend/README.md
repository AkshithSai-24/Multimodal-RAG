# MultiModal RAG — Frontend

React + Vite UI for the Multimodal RAG backend by [Akshith Sai](https://akshithsai.co.in).

## Setup

```bash
cd multimodal-rag-ui
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**  
Backend must be running at **http://localhost:8000**

## Start Backend

```bash
cd Multimodal-RAG-backend
pip install -r requirements.txt
python main.py
```

## Features

- **API Key setup** — enter NVIDIA and OpenRouter keys in-browser; sent to backend via `/config/env`
- **Multi-source ingestion** — File upload (PDF, DOCX, PPTX, images, CSV, XLSX, TXT, MD), URL scrape, YouTube transcript, raw text
- **Vision model toggle** — enable/disable vision model per ingestion
- **Ingestion stats** — chunk counts by modality (text / image / table / slide)
- **Vector DB info** — collection name, document count, source ID
- **Chat query** — Markdown-rendered answers with source citations and relevance scores
- **Auto-reset** — every new ingestion clears the vector DB first (fresh context)
- **Reset button** — manually clear DB and start over from the query panel

## Backend Change

`api/routes/ingest.py` — added `POST /ingest/reset` endpoint that deletes all Chroma collections. This is called automatically by the frontend before each ingestion run.
