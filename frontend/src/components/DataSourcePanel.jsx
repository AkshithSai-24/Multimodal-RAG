// src/components/DataSourcePanel.jsx
import { useState, useRef, useCallback } from 'react';
import {
  Upload, Link2, Youtube, FileText, Eye, EyeOff,
  FileArchive, Image, Table2, Presentation, Globe,
  AlertCircle, ChevronDown
} from 'lucide-react';
import styles from './DataSourcePanel.module.css';

const SOURCE_TABS = [
  { id: 'file',    label: 'File Upload', icon: Upload },
  { id: 'url',     label: 'Website URL', icon: Globe },
  { id: 'youtube', label: 'YouTube',     icon: Youtube },
  { id: 'text',    label: 'Raw Text',    icon: FileText },
];

const ACCEPTED_EXTS = [
  '.pdf','.docx','.doc','.pptx','.ppt',
  '.jpg','.jpeg','.png','.gif','.webp','.bmp','.tiff',
  '.csv','.tsv','.xlsx','.xls','.txt','.md',
];

const FILE_ICONS = {
  '.pdf': FileArchive, '.docx': FileText, '.doc': FileText,
  '.pptx': Presentation, '.ppt': Presentation,
  '.jpg': Image, '.jpeg': Image, '.png': Image,
  '.gif': Image, '.webp': Image, '.bmp': Image, '.tiff': Image,
  '.csv': Table2, '.tsv': Table2, '.xlsx': Table2, '.xls': Table2,
  '.txt': FileText, '.md': FileText,
};

function getExt(name) { return name.slice(name.lastIndexOf('.')).toLowerCase(); }

export default function DataSourcePanel({ onIngest, loading }) {
  const [activeTab, setActiveTab] = useState('file');
  const [useVision, setUseVision] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [urlInput, setUrlInput] = useState('');
  const [urlDepth, setUrlDepth] = useState(1);
  const [ytUrl, setYtUrl] = useState('');
  const [rawText, setRawText] = useState('');
  const [rawName, setRawName] = useState('');
  const [error, setError] = useState('');
  const fileRef = useRef();

  const handleDrop = useCallback(e => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const ext = getExt(f.name);
    if (!ACCEPTED_EXTS.includes(ext)) {
      setError(`Unsupported type: ${ext}. Allowed: ${ACCEPTED_EXTS.join(', ')}`);
      return;
    }
    setSelectedFile(f);
    setError('');
  }, []);

  const handleFileChange = e => {
    const f = e.target.files[0];
    if (!f) return;
    const ext = getExt(f.name);
    if (!ACCEPTED_EXTS.includes(ext)) {
      setError(`Unsupported type: ${ext}`);
      return;
    }
    setSelectedFile(f);
    setError('');
  };

  const handleIngest = () => {
    setError('');
    if (activeTab === 'file') {
      if (!selectedFile) { setError('Please select a file.'); return; }
      onIngest({ type: 'file', file: selectedFile, useVision });
    } else if (activeTab === 'url') {
      if (!urlInput.trim()) { setError('Please enter a URL.'); return; }
      onIngest({ type: 'url', url: urlInput.trim(), depth: urlDepth, useVision });
    } else if (activeTab === 'youtube') {
      if (!ytUrl.trim()) { setError('Please enter a YouTube URL.'); return; }
      onIngest({ type: 'youtube', url: ytUrl.trim(), useVision });
    } else if (activeTab === 'text') {
      if (!rawText.trim()) { setError('Please enter some text.'); return; }
      onIngest({ type: 'text', text: rawText.trim(), sourceName: rawName || 'manual-text', useVision });
    }
  };

  const canSubmit = () => {
    if (loading) return false;
    if (activeTab === 'file') return !!selectedFile;
    if (activeTab === 'url') return !!urlInput.trim();
    if (activeTab === 'youtube') return !!ytUrl.trim();
    if (activeTab === 'text') return !!rawText.trim();
    return false;
  };

  return (
    <div className={styles.panel}>
      {/* Section heading */}
      <div className={styles.sectionHead}>
        <span className={styles.stepBadge}>01</span>
        <div>
          <h2 className={styles.sectionTitle}>Data Source</h2>
          <p className={styles.sectionSub}>Select a source to ingest into the vector database</p>
        </div>
      </div>

      {/* Source tabs */}
      <div className={styles.tabs}>
        {SOURCE_TABS.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              className={styles.tab + (activeTab === t.id ? ' ' + styles.tabActive : '')}
              onClick={() => { setActiveTab(t.id); setError(''); setSelectedFile(null); }}
            >
              <Icon size={14} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className={styles.tabContent}>
        {activeTab === 'file' && (
          <div
            className={styles.dropzone + (dragOver ? ' ' + styles.dropzoneActive : '')}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED_EXTS.join(',')}
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            {selectedFile ? (
              <SelectedFile file={selectedFile} onClear={() => setSelectedFile(null)} />
            ) : (
              <DropPlaceholder />
            )}
          </div>
        )}

        {activeTab === 'url' && (
          <div className={styles.inputGroup}>
            <label className={styles.label}>Website URL</label>
            <input
              className={styles.input}
              type="url"
              placeholder="https://example.com/docs"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
            />
            <label className={styles.label} style={{ marginTop: 12 }}>Crawl Depth (1–5)</label>
            <div className={styles.depthRow}>
              {[1,2,3,4,5].map(d => (
                <button
                  key={d}
                  className={styles.depthBtn + (urlDepth === d ? ' ' + styles.depthActive : '')}
                  onClick={() => setUrlDepth(d)}
                >{d}</button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'youtube' && (
          <div className={styles.inputGroup}>
            <label className={styles.label}>YouTube URL</label>
            <input
              className={styles.input}
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={ytUrl}
              onChange={e => setYtUrl(e.target.value)}
            />
            <p className={styles.hint}>Transcript will be fetched and ingested as text chunks.</p>
          </div>
        )}

        {activeTab === 'text' && (
          <div className={styles.inputGroup}>
            <label className={styles.label}>Source Label (optional)</label>
            <input
              className={styles.input}
              placeholder="e.g. my-notes"
              value={rawName}
              onChange={e => setRawName(e.target.value)}
            />
            <label className={styles.label} style={{ marginTop: 12 }}>Raw Text</label>
            <textarea
              className={styles.textarea}
              placeholder="Paste any text content here…"
              value={rawText}
              onChange={e => setRawText(e.target.value)}
              rows={6}
            />
          </div>
        )}
      </div>

      {/* Vision toggle */}
      <div className={styles.visionRow}>
        <div className={styles.visionInfo}>
          <Eye size={15} style={{ color: 'var(--cyan)' }} />
          <div>
            <span className={styles.visionLabel}>Vision Model</span>
            <span className={styles.visionHint}> — analyse images, slides &amp; diagrams</span>
          </div>
        </div>
        <button
          className={styles.toggle + (useVision ? ' ' + styles.toggleOn : '')}
          onClick={() => setUseVision(v => !v)}
          title={useVision ? 'Disable vision model' : 'Enable vision model'}
        >
          <span className={styles.toggleKnob} />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className={styles.error}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* Ingest button */}
      <button
        className={styles.ingestBtn + (canSubmit() ? ' ' + styles.ingestBtnActive : '')}
        onClick={handleIngest}
        disabled={!canSubmit()}
      >
        {loading ? (
          <><span className={styles.spinner} /> Ingesting…</>
        ) : (
          <>Start Ingestion</>
        )}
      </button>
    </div>
  );
}

function DropPlaceholder() {
  return (
    <div style={{ textAlign: 'center', pointerEvents: 'none' }}>
      <div style={{
        width: 56, height: 56, borderRadius: 'var(--radius-md)',
        background: 'rgba(99,210,255,0.06)', border: '1px solid var(--border-muted)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 12px', color: 'var(--cyan)',
      }}>
        <Upload size={24} strokeWidth={1.5} />
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-base)', marginBottom: 6 }}>
        Drop a file here or <span style={{ color: 'var(--cyan)' }}>browse</span>
      </p>
      <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', lineHeight: 1.6 }}>
        PDF · DOCX · PPTX · CSV · XLSX · Images (JPG/PNG/WebP) · TXT · MD
      </p>
    </div>
  );
}

function SelectedFile({ file, onClear }) {
  const ext = getExt(file.name);
  const Icon = FILE_ICONS[ext] || FileText;
  const sizeMB = (file.size / 1024 / 1024).toFixed(2);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, pointerEvents: 'none' }}>
      <div style={{
        width: 44, height: 44, flexShrink: 0, borderRadius: 'var(--radius-md)',
        background: 'rgba(99,210,255,0.08)', border: '1px solid var(--border-accent)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--cyan)',
      }}>
        <Icon size={20} strokeWidth={1.5} />
      </div>
      <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
        <p style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-all', overflowWrap: 'anywhere', lineHeight: 1.3 }}>
          {file.name}
        </p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
          {ext.toUpperCase().slice(1)} · {sizeMB} MB
        </p>
      </div>
      <button
        style={{
          pointerEvents: 'all', background: 'none', border: 'none',
          cursor: 'pointer', color: 'var(--text-muted)', fontSize: '1.2rem',
          lineHeight: 1, padding: '2px 6px',
        }}
        onClick={e => { e.stopPropagation(); onClear(); }}
      >×</button>
    </div>
  );
}
