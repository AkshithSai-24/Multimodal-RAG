#!/usr/bin/env python3
"""
test_pipeline.py — Standalone Multi-modal RAG Pipeline Tester
==============================================================

Runs the FULL pipeline end-to-end without FastAPI or main.py:

  Source (URL / file path)
        │
        ▼  [STEP 1] Load
  Raw DocumentChunks  (text, table, image, slide)
        │
        ▼  [STEP 2] Process
  Enriched Chunks  (vision summaries, table descriptions, text splits)
        │
        ▼  [STEP 3] Embed + Store
  Chroma Vector DB  (in-memory, wiped after each run unless --persist)
        │
        ▼  [STEP 4] Retrieve
  Top-K Chunks  (by semantic similarity to query)
        │
        ▼  [STEP 5] Generate
  Final Answer  (multi-modal prompt → vision LLM via OpenRouter)

Usage
-----
  python test.py --source "https://en.wikipedia.org/wiki/Retrieval-augmented_generation" --query "what is RAG?" --no-vision 
  python test.py --source "./test.pdf" --query "Summarise key findings" --no-vision 
  python test_pipeline.py --source "./data.pptx" --query "Main slides?" --persist
  python test_pipeline.py --source "https://docs.python.org/3/" --query "decorators?" --top-k 4 --no-vision 
  python test_pipeline.py --source "./report.pdf" --query "tables" --no-vision --no-vision 
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import textwrap
import time
from pathlib import Path
from typing import List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from dotenv import load_dotenv
load_dotenv(_HERE / ".env")

from config.settings import settings
from loaders.loader_factory import LoaderFactory
from models.document import DocumentChunk, Modality, RetrievedChunk
from processors.multimodal_processor import MultiModalProcessor
from processors.text_processor import TextProcessor
from core.embeddings import get_embeddings
from core.llm import get_vision_llm
from core.vectorstore import VectorStoreManager
from core.rag_chain import run_rag

# ── ANSI colour helpers ────────────────────────────────────────────────────────
_USE_COLOUR = sys.stdout.isatty()

def _c(code, text):  return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text
def _bold(t):        return _c("1",    t)
def _cyan(t):        return _c("1;36", t)
def _green(t):       return _c("1;32", t)
def _yellow(t):      return _c("1;33", t)
def _red(t):         return _c("1;31", t)
def _grey(t):        return _c("2",    t)
def _blue(t):        return _c("1;34", t)
def _magenta(t):     return _c("1;35", t)

# ── Verbose logger ─────────────────────────────────────────────────────────────
class VerboseLogger:
    def __init__(self):
        self._step = 0
        self._t0 = time.perf_counter()

    def _elapsed(self):
        return _grey(f"[{time.perf_counter() - self._t0:6.2f}s]")

    def step(self, title):
        self._step += 1
        bar = "─" * 60
        print(f"\n{_cyan(bar)}")
        print(f"  {_cyan(f'STEP {self._step}')}  {_bold(title)}")
        print(f"{_cyan(bar)}")

    def info(self, msg):
        print(f"  {self._elapsed()} {_green('INFO')}  {msg}")

    def debug(self, msg):
        print(f"  {self._elapsed()} {_grey('DBG ')}  {_grey(msg)}")

    def warn(self, msg):
        print(f"  {self._elapsed()} {_yellow('WARN')}  {_yellow(msg)}")

    def error(self, msg):
        print(f"  {self._elapsed()} {_red('ERR ')}  {_red(msg)}")

    def separator(self):
        print(f"  {_grey('·' * 60)}")

    def banner(self, title):
        bar = "═" * 64
        print(f"\n{_bold(_cyan(bar))}")
        print(f"{_bold(_cyan(title.center(64)))}")
        print(f"{_bold(_cyan(bar))}\n")

    def chunk_summary(self, chunks: List[DocumentChunk]):
        if not chunks:
            self.warn("No chunks to display.")
            return
        counts: dict = {}
        for c in chunks:
            counts[c.modality.value] = counts.get(c.modality.value, 0) + 1
        parts = [f"{_bold(k)}: {v}" for k, v in sorted(counts.items())]
        self.info(f"Total chunks: {_bold(str(len(chunks)))}  │  " + "  ".join(parts))

    def retrieved_chunks(self, chunks: List[RetrievedChunk]):
        self.info(f"Retrieved {_bold(str(len(chunks)))} chunk(s):")
        _MC = {"text": _green, "table": _yellow, "image": _magenta, "slide": _blue}
        for i, c in enumerate(chunks, 1):
            mc     = _MC.get(c.modality.value, _grey)
            label  = mc(f"[{c.modality.value.upper():6}]")
            score  = _cyan(f"score={c.score:.4f}")
            src    = _grey(f"src={c.source_name!r}")
            page   = _grey(f"p.{c.page_number}") if c.page_number else ""
            prev   = textwrap.shorten(c.content.replace("\n", " "), width=90)
            print(f"    {i:>2}. {label} {score}  {src} {page}")
            print(f"        {_grey(prev)}")


# ── Pipeline ───────────────────────────────────────────────────────────────────
async def run_pipeline(source, query, top_k=6, persist=False,
                       no_vision=True, collection="pipeline_test"):

    log = VerboseLogger()
    log.banner("MultiModal RAG — Pipeline Test")

    print(f"  {'Source':<22} {_bold(source)}")
    print(f"  {'Query':<22} {_bold(repr(query))}")
    print(f"  {'LLM model':<22} {settings.LLM_MODEL}")
    print(f"  {'Vision model':<22} {settings.VISION_MODEL}")
    print(f"  {'Embedding model':<22} {settings.EMBEDDING_MODEL}")
    print(f"  {'Embedding task type':<22} {settings.EMBEDDING_TASK_TYPE}")
    print(f"  {'Top-K':<22} {top_k}")
    print(f"  {'Vision during ingest':<22} {not no_vision}")
    print(f"  {'Persist Chroma':<22} {persist}")
    persist_dir = settings.CHROMA_PERSIST_DIR if persist else "/tmp/mmrag_test_chroma"
    print(f"  {'Chroma dir':<22} {persist_dir}")

    # ── STEP 1: LOAD ──────────────────────────────────────────────────────────
    log.step("Load source content")
    t0 = time.perf_counter()

    source_path = Path(source)
    if source_path.exists():
        loader = LoaderFactory.from_path(str(source_path))
        if loader is None:
            log.info(f"Plain text file — reading directly: {source_path.name}")
            raw_text = source_path.read_text(encoding="utf-8", errors="replace")
            from models.document import SourceType
            import uuid
            raw_chunks = [DocumentChunk(
                content=raw_text, modality=Modality.TEXT,
                source_type=SourceType.TEXT,
                source_id=str(source_path), source_name=source_path.name,
            )]
        else:
            log.info(f"File loader: {_bold(type(loader).__name__)}  →  {source_path.name}")
            raw_chunks = await loader.load(str(source_path))
    else:
        loader = LoaderFactory.from_url(source)
        log.info(f"URL loader: {_bold(type(loader).__name__)}  →  {source}")
        raw_chunks = await loader.load(source)

    log.info(f"Loaded in {time.perf_counter()-t0:.2f}s")
    log.chunk_summary(raw_chunks)
    log.separator()

    for i, c in enumerate(raw_chunks):
        img = "🖼  has_image" if c.image_base64 else ""
        log.debug(f"chunk[{i:>3}]  mod={c.modality.value:<8}  "
                  f"src={c.source_name!r:<30}  len={len(c.content):>6}  {img}")

    if not raw_chunks:
        log.error("No content loaded. Aborting.")
        sys.exit(1)

    # ── STEP 2: PROCESS ───────────────────────────────────────────────────────
    log.step("Multi-modal processing  (split · vision · tables)")
    t0 = time.perf_counter()

    if no_vision:
        log.warn("--no-vision: skipping vision LLM and table enrichment.")
        enriched_chunks = TextProcessor().process(raw_chunks)
    else:
        img_n = sum(1 for c in raw_chunks
                    if c.modality in (Modality.IMAGE, Modality.SLIDE) and c.image_base64)
        tbl_n = sum(1 for c in raw_chunks if c.modality == Modality.TABLE)
        log.debug(f"images_to_summarise={img_n}  tables_to_describe={tbl_n}")
        if img_n:
            log.info(f"Calling vision LLM for {img_n} image(s) …")
        if tbl_n:
            log.info(f"Calling text LLM for {tbl_n} table(s) …")
        enriched_chunks = await MultiModalProcessor().process(raw_chunks)

    log.info(f"Processing done in {time.perf_counter()-t0:.2f}s")
    log.chunk_summary(enriched_chunks)
    log.separator()

    for i, c in enumerate(enriched_chunks):
        prev = textwrap.shorten(c.content.replace("\n", " "), width=80)
        img  = "🖼" if c.image_base64 else "  "
        log.debug(f"chunk[{i:>3}]  {img}  mod={c.modality.value:<8}  "
                  f"len={len(c.content):>6}  preview={_grey(repr(prev))}")

    # ── STEP 3: EMBED + STORE ─────────────────────────────────────────────────
    log.step("Embed chunks & store in Chroma")
    t0 = time.perf_counter()

    log.info(f"Embedding model : {_bold(settings.EMBEDDING_MODEL)}")
    log.info(f"Task type       : {settings.EMBEDDING_TASK_TYPE}")
    log.info(f"Chroma dir      : {persist_dir}")
    log.info(f"Collection      : {collection}")
    log.info(f"Chunks to embed : {len(enriched_chunks)}")

    if not persist:
        settings.__dict__["CHROMA_PERSIST_DIR"] = persist_dir

    vs = VectorStoreManager()
    await vs.initialize()

    log.info("Verifying embedding API …")
    '''try:
        _ = get_embeddings().embed_query("connectivity test")
        log.info(_green("Embedding API ✓"))
    except Exception as exc:
        log.error(f"Embedding API failed: {exc}")
        log.error("Check GOOGLE_API_KEY in your .env file.")
        sys.exit(1)'''

    added = await vs.add_chunks(enriched_chunks, collection_name=collection)
    total_in_col = await vs.get_collection_count(collection)
    log.info(f"Stored {_bold(str(added))} chunks in {time.perf_counter()-t0:.2f}s  "
             f"│  collection total = {total_in_col}")

    # ── STEP 4: RETRIEVE ──────────────────────────────────────────────────────
    log.step(f"Retrieve  (top-k={top_k})")
    t0 = time.perf_counter()

    log.info(f"Query: {_bold(repr(query))}")
    retrieved = await vs.similarity_search(query, collection_name=collection, k=top_k)
    log.info(f"Retrieval completed in {time.perf_counter()-t0:.3f}s")
    log.retrieved_chunks(retrieved)

    if not retrieved:
        log.warn("Nothing retrieved — query may be too different from ingested content.")

    mod_counts: dict = {}
    for r in retrieved:
        mod_counts[r.modality.value] = mod_counts.get(r.modality.value, 0) + 1
    log.debug("Retrieval modality breakdown: " + str(mod_counts))

    # ── STEP 5: GENERATE ──────────────────────────────────────────────────────
    log.step("Generate answer  (multi-modal RAG)")
    t0 = time.perf_counter()

    log.info(f"Vision model    : {_bold(settings.VISION_MODEL)}")
    log.info(f"Include images  : {not no_vision}")

    rag_result = await run_rag(
        query=query,
        vs_manager=vs,
        collection_name=collection,
        top_k=top_k,
        include_images=(not no_vision),
    )
    log.info(f"Generation done in {time.perf_counter()-t0:.2f}s")
    if rag_result.total_tokens:
        log.info(f"Tokens used: {rag_result.total_tokens}")

    # ── FINAL OUTPUT ──────────────────────────────────────────────────────────
    bar = "═" * 64
    print(f"\n{_bold(_green(bar))}")
    print(f"{_bold(_green('  ANSWER'))}")
    print(f"{_bold(_green(bar))}\n")
    print(textwrap.fill(rag_result.answer, width=72,
                        initial_indent="  ", subsequent_indent="  "))
    print()

    if rag_result.sources:
        print(f"{_bold(_cyan('  SOURCES USED'))}")
        print(f"  {_cyan('─' * 60)}")
        _MC = {"text": _green, "table": _yellow, "image": _magenta, "slide": _blue}
        for i, src in enumerate(rag_result.sources, 1):
            mc    = _MC.get(src.modality.value, _grey)
            score = _cyan(f"{src.score:.4f}")
            page  = f"  p.{src.page_number}" if src.page_number else ""
            img_f = _magenta("  [has image]") if src.has_image else ""
            print(f"  {i:>2}. {mc(f'[{src.modality.value.upper()}]'):<20} "
                  f"{score}  {_bold(src.source_name)}{page}{img_f}")

    wall = time.perf_counter() - log._t0
    print(f"\n  {_grey(f'Total wall-clock time: {wall:.2f}s')}")
    print(f"{_bold(_green(bar))}\n")

    if not persist:
        try:
            await vs.delete_collection(collection)
            log.debug(f"Cleaned up test collection '{collection}'.")
        except Exception:
            pass


# ── CLI ────────────────────────────────────────────────────────────────────────
def _parse_args():
    p = argparse.ArgumentParser(
        prog="test_pipeline.py",
        description="Run the full Multi-modal RAG pipeline from the CLI.",
    )
    p.add_argument("--source", "-s", required=True,
                   help="URL to scrape or local file path")
    p.add_argument("--query",  "-q", required=True,
                   help="Question to answer with RAG")
    p.add_argument("--top-k",  "-k", type=int, default=6,
                   help="Chunks to retrieve (default: 6)")
    p.add_argument("--persist", action="store_true",
                   help="Keep Chroma DB after run")
    p.add_argument("--no-vision", action="store_true",
                   help="Skip vision LLM during ingest")
    p.add_argument("--collection", default="pipeline_test",
                   help="Chroma collection name (default: pipeline_test)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if settings.OPENROUTER_API_KEY.startswith("your-"):
        print(_red("\n  ⚠  OPENROUTER_API_KEY not set in .env\n"))
        sys.exit(1)
    if settings.GOOGLE_API_KEY.startswith("your-"):
        print(_red("\n  ⚠  GOOGLE_API_KEY not set in .env\n"))
        sys.exit(1)

    asyncio.run(run_pipeline(
        source=args.source,
        query=args.query,
        top_k=args.top_k,
        persist=args.persist,
        no_vision=args.no_vision,
        collection=args.collection,
    ))