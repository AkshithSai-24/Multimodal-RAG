// src/components/IngestionStatus.jsx
import { Database, FileText, Image, Table2, Layers, CheckCircle2, Cpu } from 'lucide-react';
import styles from './IngestionStatus.module.css';

export default function IngestionStatus({ status, collectionInfo }) {
  const { source, result } = status;

  const stats = [
    { label: 'Total Chunks',  value: result.total_chunks,  icon: Layers,   color: 'var(--cyan)'   },
    { label: 'Text',          value: result.text_chunks,   icon: FileText, color: 'var(--green)'  },
    { label: 'Images/Slides', value: result.image_chunks,  icon: Image,    color: 'var(--purple)' },
    { label: 'Tables',        value: result.table_chunks,  icon: Table2,   color: 'var(--amber)'  },
  ];

  return (
    <div className={styles.wrap + ' animate-in'}>
      {/* Success banner */}
      <div className={styles.successBar}>
        <CheckCircle2 size={16} style={{ color: 'var(--green)' }} />
        <span className={styles.successText}>
          Ingestion complete — <strong>{result.source_name}</strong>
        </span>
        <span className={styles.badge}>{result.source_type}</span>
      </div>

      {/* Stats grid */}
      <div className={styles.grid}>
        {stats.map(s => {
          const Icon = s.icon;
          return (
            <div key={s.label} className={styles.statCard}>
              <div className={styles.statIcon} style={{ color: s.color, background: `${s.color}12` }}>
                <Icon size={16} strokeWidth={1.5} />
              </div>
              <div>
                <p className={styles.statValue} style={{ color: s.color }}>{s.value ?? 0}</p>
                <p className={styles.statLabel}>{s.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Vector DB panel */}
      <div className={styles.dbPanel}>
        <div className={styles.dbHeader}>
          <Database size={14} style={{ color: 'var(--cyan)' }} />
          <span className={styles.dbTitle}>Vector Database</span>
          <span className={styles.dbBadge}>Chroma</span>
        </div>
        <div className={styles.dbRows}>
          <DbRow label="Collection" value={result.collection_name} mono />
          {collectionInfo && (
            <DbRow label="Total Documents" value={collectionInfo.count} />
          )}
          <DbRow label="Source ID" value={result.source_id} mono truncate />
        </div>
      </div>
    </div>
  );
}

function DbRow({ label, value, mono, truncate }) {
  return (
    <div className={styles.dbRow}>
      <span className={styles.dbRowLabel}>{label}</span>
      <span
        className={styles.dbRowValue + (mono ? ' ' + styles.mono : '') + (truncate ? ' ' + styles.truncate : '')}
        title={String(value)}
      >
        {value}
      </span>
    </div>
  );
}
