// src/api.js

const RAW_BASE =
  import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const BASE = RAW_BASE.replace(/\/+$/, ''); // remove trailing slash(es)

const apiUrl = (path) => `${BASE}/${path.replace(/^\/+/, '')}`;

async function post(path, body) {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function checkHealth() {
  const res = await fetch(apiUrl('/health'));
  if (!res.ok) throw new Error('Backend unreachable');
  return res.json();
}

export async function uploadEnv(envContent) {
  const blob = new Blob([envContent], { type: 'text/plain' });
  const form = new FormData();
  form.append('file', blob, '.env');

  const res = await fetch(apiUrl('/config/env'), {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function listCollections() {
  const res = await fetch(apiUrl('/ingest/collections'));
  if (!res.ok) throw new Error('Failed to list collections');
  return res.json();
}

export async function deleteCollection(name) {
  const res = await fetch(apiUrl(`/ingest/collections/${encodeURIComponent(name)}`), {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function resetCollections() {
  const res = await fetch(apiUrl('/ingest/reset'), { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function ingestFile(file, useVisionModel = true) {
  const form = new FormData();
  form.append('file', file);
  form.append('use_vision_model', String(useVisionModel));

  const res = await fetch(apiUrl('/ingest/file'), { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function ingestURL(url, maxDepth = 1, useVisionModel = true) {
  return post('/ingest/url', { url, max_depth: maxDepth, use_vision_model: useVisionModel });
}

export async function ingestYouTube(url, useVisionModel = true) {
  return post('/ingest/youtube', { url, use_vision_model: useVisionModel });
}

export async function ingestText(text, sourceName = 'manual-text', useVisionModel = true) {
  return post('/ingest/text', { text, source_name: sourceName, use_vision_model: useVisionModel });
}

export async function queryRAG(query, topK = 6, includeImages = true, collectionName = null) {
  return post('/query', {
    query,
    top_k: topK,
    include_images: includeImages,
    ...(collectionName ? { collection_name: collectionName } : {}),
  });
}