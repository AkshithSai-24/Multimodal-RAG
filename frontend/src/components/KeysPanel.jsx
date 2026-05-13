// src/components/KeysPanel.jsx
import { useState } from 'react';
import { KeyRound, Eye, EyeOff, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import { uploadEnv } from '../api';
import styles from './KeysPanel.module.css';

export default function KeysPanel({ onKeysReady }) {
  const [nvidiaKey, setNvidiaKey] = useState('');
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [showNvidia, setShowNvidia] = useState(false);
  const [showOr, setShowOr] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const valid = nvidiaKey.trim() && openrouterKey.trim();

  const handleSubmit = async () => {
    if (!valid) return;
    setLoading(true);
    setError('');
    const envContent = [
      `NVIDIA_API_KEY=${nvidiaKey.trim()}`,
      `OPENROUTER_API_KEY=${openrouterKey.trim()}`,
      `LLM_MODEL=openai/gpt-oss-20b:free`,
      `VISION_MODEL=meta/llama-4-maverick-17b-128e-instruct`,
      `EMBEDDING_MODEL=nvidia/llama-nemotron-embed-1b-v2`,
      `APP_HOST=0.0.0.0`,
      `APP_PORT=8000`,
      `DEBUG=false`,
      `CORS_ORIGINS=["*"]`,
      `CHROMA_PERSIST_DIR=./chroma_db`,
      `CHROMA_COLLECTION_NAME=multimodal_rag`,
      `CHUNK_SIZE=1000`,
      `CHUNK_OVERLAP=200`,
      `TOP_K=6`,
      `MAX_IMAGE_DOCS=3`,
      `INCLUDE_IMAGES_IN_RESPONSE=true`,
      `UPLOAD_DIR=./uploads`,
      `MAX_UPLOAD_SIZE_MB=50`,
    ].join('\n');
    try {
      await uploadEnv(envContent);
      setSubmitted(true);
      setCollapsed(true);
      onKeysReady(true);
    } catch (e) {
      setError(e.message);
      onKeysReady(false);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setCollapsed(false);
    setSubmitted(false);
    onKeysReady(false);
  };

  return (
    <div className={styles.panel}>
      {/* Header row */}
      <div className={styles.panelHeader} onClick={() => submitted && setCollapsed(v => !v)}>
        <div className={styles.panelTitle}>
          <div className={styles.iconWrap}>
            <KeyRound size={14} strokeWidth={1.8} />
          </div>
          <span className={styles.titleText}>API Keys</span>
          {submitted && (
            <span className={styles.badge}>
              <CheckCircle2 size={11} /> Configured
            </span>
          )}
        </div>
        {submitted && (
          <button className={styles.collapseBtn} onClick={e => { e.stopPropagation(); setCollapsed(v => !v); }}>
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        )}
      </div>

      {/* Collapsed success state */}
      {submitted && collapsed ? (
        <div className={styles.successRow}>
          <span className={styles.successText}>Keys saved — backend initialised</span>
          <button className={styles.editBtn} onClick={handleEdit}>Edit</button>
        </div>
      ) : (
        <div className={styles.fields}>
          <KeyField
            label="NVIDIA API Key"
            placeholder="nvapi-..."
            value={nvidiaKey}
            onChange={setNvidiaKey}
            show={showNvidia}
            onToggle={() => setShowNvidia(v => !v)}
          />
          <KeyField
            label="OpenRouter API Key"
            placeholder="sk-or-..."
            value={openrouterKey}
            onChange={setOpenrouterKey}
            show={showOr}
            onToggle={() => setShowOr(v => !v)}
          />

          {error && (
            <div className={styles.error}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span>{error}</span>
            </div>
          )}

          <button
            className={styles.btn + (valid && !loading ? ' ' + styles.btnActive : '')}
            onClick={handleSubmit}
            disabled={!valid || loading}
          >
            {loading ? (
              <><span className={styles.spinner} /> Initialising…</>
            ) : (
              <>Initialise Backend</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

function KeyField({ label, placeholder, value, onChange, show, onToggle }) {
  return (
    <div className={styles.fieldGroup}>
      <label className={styles.label}>{label}</label>
      <div className={styles.inputWrap}>
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className={styles.input}
        />
        <button className={styles.eyeBtn} onClick={onToggle} type="button">
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    </div>
  );
}
