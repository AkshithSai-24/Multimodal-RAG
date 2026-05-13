// src/components/QueryPanel.jsx
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Bot, User, Cpu, FileText, Image, Table2, Layers,
  ChevronDown, ChevronUp, RefreshCw, Hash
} from 'lucide-react';
import styles from './QueryPanel.module.css';

const MODALITY_ICON = { text: FileText, image: Image, table: Table2, slide: Layers };
const MODALITY_COLOR = { text: 'var(--cyan)', image: 'var(--purple)', table: 'var(--amber)', slide: 'var(--green)' };

export default function QueryPanel({ onQuery, onReset, loading }) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(6);
  const [history, setHistory] = useState([]);
  const textareaRef = useRef();
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, loading]);

  const handleSend = async () => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setQuery('');
    setHistory(h => [...h, { role: 'user', content: q }]);
    try {
      const res = await onQuery(q, topK);
      setHistory(h => [...h, { role: 'assistant', content: res.answer, sources: res.sources, model: res.model_used }]);
    } catch (e) {
      setHistory(h => [...h, { role: 'error', content: e.message }]);
    }
  };

  const onKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.stepBadge}>02</span>
          <div>
            <h2 className={styles.title}>Query Interface</h2>
            <p className={styles.sub}>Ask anything about your ingested data</p>
          </div>
        </div>
        <button className={styles.resetBtn} onClick={onReset} title="Reset — clear DB and start over">
          <RefreshCw size={14} />
          Reset
        </button>
      </div>

      {/* Chat messages */}
      <div className={styles.messages}>
        {history.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}><Bot size={28} strokeWidth={1.2} /></div>
            <p className={styles.emptyTitle}>Ready to answer</p>
            <p className={styles.emptySub}>Data ingested successfully. Type your question below.</p>
          </div>
        )}

        {history.map((msg, i) => (
          <ChatMessage key={i} msg={msg} />
        ))}

        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Top-K control */}
      <div className={styles.topKRow}>
        <div className={styles.topKLabel}>
          <Hash size={12} />
          <span>Top-K documents to retrieve</span>
        </div>
        <div className={styles.topKControls}>
          <button
            className={styles.topKBtn}
            onClick={() => setTopK(v => Math.max(1, v - 1))}
            disabled={loading || topK <= 1}
            aria-label="Decrease Top-K"
          >−</button>
          <span className={styles.topKValue}>{topK}</span>
          <button
            className={styles.topKBtn}
            onClick={() => setTopK(v => Math.min(20, v + 1))}
            disabled={loading || topK >= 20}
            aria-label="Increase Top-K"
          >+</button>
        </div>
      </div>

      {/* Input row */}
      <div className={styles.inputRow}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          placeholder="Ask a question about your data… (Enter to send)"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={onKey}
          rows={1}
          disabled={loading}
        />
        <button
          className={styles.sendBtn + (!query.trim() || loading ? '' : ' ' + styles.sendBtnActive)}
          onClick={handleSend}
          disabled={!query.trim() || loading}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}

function ChatMessage({ msg }) {
  const [showSrc, setShowSrc] = useState(false);

  if (msg.role === 'user') {
    return (
      <div className={styles.msgRow + ' ' + styles.userRow}>
        <div className={styles.bubble + ' ' + styles.userBubble}>
          <p className={styles.msgText}>{msg.content}</p>
        </div>
        <div className={styles.avatar + ' ' + styles.userAvatar}><User size={14} /></div>
      </div>
    );
  }

  if (msg.role === 'error') {
    return (
      <div className={styles.msgRow}>
        <div className={styles.avatar + ' ' + styles.botAvatar}><Bot size={14} /></div>
        <div className={styles.bubble + ' ' + styles.errorBubble}>
          <p style={{ color: 'var(--red)', fontSize: '0.88rem' }}>{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.msgRow + ' animate-in'}>
      <div className={styles.avatar + ' ' + styles.botAvatar}><Bot size={14} /></div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className={styles.bubble + ' ' + styles.botBubble}>
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>

          {msg.model && (
            <div className={styles.modelTag}>
              <Cpu size={11} />
              {msg.model}
            </div>
          )}
        </div>

        {/* Sources */}
        {msg.sources?.length > 0 && (
          <div className={styles.sourceSection}>
            <button className={styles.sourceToggle} onClick={() => setShowSrc(v => !v)}>
              <Layers size={13} />
              {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''} used
              {showSrc ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            {showSrc && (
              <div className={styles.sourceList}>
                {msg.sources.map((s, i) => {
                  const Icon = MODALITY_ICON[s.modality] || FileText;
                  const col = MODALITY_COLOR[s.modality] || 'var(--cyan)';
                  return (
                    <div key={i} className={styles.sourceCard}>
                      <div className={styles.sourceHeader}>
                        <div className={styles.sourceIconWrap} style={{ background: `${col}12`, color: col }}>
                          <Icon size={13} strokeWidth={1.5} />
                        </div>
                        <span className={styles.sourceName}>{s.source_name}</span>
                        <span className={styles.sourceScore}>
                          {(s.score * 100).toFixed(0)}%
                        </span>
                        {s.page_number && (
                          <span className={styles.sourcePage}>p.{s.page_number}</span>
                        )}
                        <span className={styles.sourceModality} style={{ color: col }}>
                          {s.modality}
                        </span>
                      </div>
                      {s.content_preview && (
                        <p className={styles.sourcePreview}>{s.content_preview}</p>
                      )}
                      {s.has_image && s.image_data && (
                        <img
                          src={s.image_data}
                          alt="Retrieved image"
                          className={styles.sourceImg}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className={styles.msgRow}>
      <div className={styles.avatar + ' ' + styles.botAvatar}><Bot size={14} /></div>
      <div className={styles.bubble + ' ' + styles.botBubble} style={{ padding: '12px 16px' }}>
        <div className={styles.dots}>
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}