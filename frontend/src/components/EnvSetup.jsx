// src/components/EnvSetup.jsx
import { useState } from 'react';
import { KeyRound, ChevronRight, AlertCircle, CheckCircle2, Eye, EyeOff, Zap } from 'lucide-react';
import { uploadEnv } from '../api';
import styles from './EnvSetup.module.css';

export default function EnvSetup({ onComplete }) {
  const [nvidiaKey, setNvidiaKey] = useState('');
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [showNvidia, setShowNvidia] = useState(false);
  const [showOr, setShowOr] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      const res = await uploadEnv(envContent);
      onComplete({ nvidiaKey: nvidiaKey.trim(), openrouterKey: openrouterKey.trim(), envRes: res });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card + ' animate-in'}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.iconWrap}>
            <KeyRound size={24} strokeWidth={1.5} />
          </div>
          <div>
            <h1 className={styles.title}>API Configuration</h1>
            <p className={styles.subtitle}>Two keys required to initialise the RAG pipeline</p>
          </div>
        </div>

        {/* Divider */}
        <div className={styles.divider} />

        {/* Fields */}
        <div className={styles.fields}>
          <PasswordField
            label="NVIDIA API Key"
            hint="Required for NVIDIA LlamaIndex embeddings"
            value={nvidiaKey}
            onChange={setNvidiaKey}
            show={showNvidia}
            onToggle={() => setShowNvidia(v => !v)}
            placeholder="nvapi-..."
          />
          <PasswordField
            label="OpenRouter API Key"
            hint="Required for LLM inference via OpenRouter"
            value={openrouterKey}
            onChange={setOpenrouterKey}
            show={showOr}
            onToggle={() => setShowOr(v => !v)}
            placeholder="sk-or-..."
          />
        </div>

        {/* Error */}
        {error && (
          <div className={styles.errorBox}>
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        {/* CTA */}
        <button
          className={styles.btn + (valid && !loading ? ' ' + styles.btnActive : '')}
          onClick={handleSubmit}
          disabled={!valid || loading}
        >
          {loading ? (
            <>
              <span className={styles.spinner} />
              Initialising backend…
            </>
          ) : (
            <>
              <Zap size={16} />
              Initialise Backend
              <ChevronRight size={16} />
            </>
          )}
        </button>

        <p className={styles.note}>
          Keys are sent only to your local backend at <code>localhost:8000</code>
        </p>
      </div>
    </div>
  );
}

function PasswordField({ label, hint, value, onChange, show, onToggle, placeholder }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label style={{
        fontSize: '0.8rem',
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: 'var(--cyan)',
        fontFamily: 'var(--font-display)',
      }}>
        {label}
      </label>
      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 2 }}>{hint}</p>
      <div style={{ position: 'relative' }}>
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          style={{
            width: '100%',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-muted)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 44px 12px 14px',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            outline: 'none',
            transition: 'var(--transition)',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--cyan)'}
          onBlur={e => e.target.style.borderColor = 'var(--border-muted)'}
        />
        <button
          onClick={onToggle}
          style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
          }}
        >
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    </div>
  );
}
