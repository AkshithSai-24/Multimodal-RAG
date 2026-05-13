// src/App.jsx
import { useState, useEffect } from 'react';
import DataSourcePanel from './components/DataSourcePanel';
import IngestionStatus from './components/IngestionStatus';
import QueryPanel from './components/QueryPanel';
import KeysPanel from './components/KeysPanel';
import {
  checkHealth, ingestFile, ingestURL, ingestYouTube,
  ingestText, queryRAG, listCollections, resetCollections,
} from './api';
import styles from './App.module.css';

const PHASE = {
  SETUP: 'setup',
  INGEST: 'ingest',
  READY: 'ready',
};

export default function App() {
  const [phase, setPhase] = useState(PHASE.SETUP);
  const [keysReady, setKeysReady] = useState(false);
  const [keysWarning, setKeysWarning] = useState(false);
  const [ingestionStatus, setIngestionStatus] = useState(null);
  const [collectionInfo, setCollectionInfo] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [ingestError, setIngestError] = useState('');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    checkHealth()
      .then(h => setHealth(h))
      .catch(() => setHealth(null));
  }, []);

  const handleKeysReady = (ready) => {
    setKeysReady(ready);
    if (ready) setKeysWarning(false);
  };

  const handleIngest = async (source) => {
    if (!keysReady) {
      setKeysWarning(true);
      return;
    }
    setIngestLoading(true);
    setIngestError('');
    setKeysWarning(false);
    try {
      try { await resetCollections(); } catch (_) {}
      let result;
      if (source.type === 'file') {
        result = await ingestFile(source.file, source.useVision);
      } else if (source.type === 'url') {
        result = await ingestURL(source.url, source.depth, source.useVision);
      } else if (source.type === 'youtube') {
        result = await ingestYouTube(source.url, source.useVision);
      } else if (source.type === 'text') {
        result = await ingestText(source.text, source.sourceName, source.useVision);
      }
      setIngestionStatus({ source, result });
      const cols = await listCollections().catch(() => null);
      if (cols?.collections) {
        const col = cols.collections.find(c => c.name === result.collection_name);
        setCollectionInfo(col || null);
      }
      setPhase(PHASE.READY);
    } catch (e) {
      setIngestError(e.message);
    } finally {
      setIngestLoading(false);
    }
  };

  const handleQuery = async (q) => {
    setQueryLoading(true);
    try {
      const res = await queryRAG(q);
      return res;
    } finally {
      setQueryLoading(false);
    }
  };

  const handleReset = async () => {
    try { await resetCollections(); } catch (_) {}
    setIngestionStatus(null);
    setCollectionInfo(null);
    setIngestError('');
    setPhase(PHASE.SETUP);
  };

  return (
    <div className={styles.app}>
      <Header health={health} />

      <main className={styles.main}>
        {/* Left column */}
        <div className={styles.leftCol}>
          {/* API Keys panel — always visible in sidebar */}
          <KeysPanel onKeysReady={handleKeysReady} />

          {/* Keys warning */}
          {keysWarning && (
            <div className={styles.keysWarning}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>Please submit your API keys before ingesting data.</span>
            </div>
          )}

          <DataSourcePanel
            onIngest={handleIngest}
            loading={ingestLoading}
            keysReady={keysReady}
          />

          {ingestError && (
            <div className={styles.errorBox}>
              <span style={{ fontSize: '0.85rem', color: 'var(--red)' }}>
                ⚠ {ingestError}
              </span>
            </div>
          )}

          {ingestionStatus && (
            <div className="animate-in">
              <IngestionStatus
                status={ingestionStatus}
                collectionInfo={collectionInfo}
              />
            </div>
          )}
        </div>

        {/* Right column */}
        <div className={styles.rightCol}>
          {phase !== PHASE.READY ? (
            <div className={styles.queryLocked}>
              <div className={styles.lockIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              </div>
              <p className={styles.lockTitle}>Query locked</p>
              <p className={styles.lockSub}>Complete data ingestion to unlock the query interface.</p>
            </div>
          ) : (
            <QueryPanel
              onQuery={handleQuery}
              onReset={handleReset}
              loading={queryLoading}
            />
          )}
        </div>
      </main>

      <footer className={styles.footer}>
        <span>Developed by <strong>Akshith Sai Kondamadugu</strong></span>
      </footer>
    </div>
  );
}

function Header({ health }) {
  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <div className={styles.logo}>
          <div className={styles.logoMark}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
              <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
          </div>
          <div>
            <span className={styles.logoText}>MultiModal RAG</span>
            <span className={styles.logoBy}>by <a href="https://akshithsai.co.in" target="_blank" rel="noreferrer" className={styles.logoLink}>Akshith Sai</a></span>
          </div>
        </div>

        <div className={styles.headerRight}>
          <div className={styles.statusDot + (health ? ' ' + styles.statusOnline : ' ' + styles.statusOffline)} />
          <span className={styles.statusLabel}>
            {health ? `Backend online · ${health.default_collection_docs ?? 0} docs` : 'Backend offline'}
          </span>
        </div>
      </div>
    </header>
  );
}
