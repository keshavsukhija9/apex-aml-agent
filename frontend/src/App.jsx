import { useState } from 'react';
import TerminalPanel from './components/TerminalPanel';
import DAGViewer from './components/DAGViewer';
import EvidenceCard from './components/EvidenceCard';

const API_BASE = 'http://localhost:8000';

function App() {
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runQuery = async (query) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setTrace(data);
    } catch (e) {
      setError(e.message);
      setTrace(null);
    } finally {
      setLoading(false);
    }
  };

  const parserLabel = trace?.intent?.parsed_by === 'llm' ? 'LLM_PRIMARY' : 'FALLBACK_REGEX';
  const executedCount = trace?.tool_trace?.filter(t => t.status === 'executed').length ?? 0;
  const totalTools = trace?.tool_trace?.length ?? 7;

  return (
    <div className="h-screen overflow-hidden flex flex-col" style={{ background: 'var(--bg-void)' }}>

      {/* Header */}
      <header
        className="px-6 py-3.5 flex items-center justify-between shrink-0"
        style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg-panel)' }}
      >
        <div className="flex items-center gap-3">
          <div className="relative w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-live)' }}>
            <div className="absolute inset-0 rounded-full animate-pulse-live" style={{ background: 'var(--accent-live)' }} />
          </div>
          <div className="font-display font-bold text-[13px] tracking-wide" style={{ color: 'var(--text-primary)' }}>
            APEX <span style={{ color: 'var(--text-dim)' }}>//</span> AML COMPLIANCE TERMINAL
          </div>
        </div>

        <div className="flex items-center gap-2 font-data text-[10.5px]">
          <div
            className="px-2.5 py-1 rounded-sm flex items-center gap-1.5"
            style={{ border: '1px solid var(--line)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--text-dim)' }}>PARSER</span>
            <span style={{ color: 'var(--text-primary)' }}>{parserLabel}</span>
          </div>
          <div
            className="px-2.5 py-1 rounded-sm flex items-center gap-1.5 tabular-nums"
            style={{ border: '1px solid var(--line)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--accent-live)' }}>⚡</span>
            <span style={{ color: trace ? 'var(--text-primary)' : 'var(--text-dim)' }}>
              {trace ? `${trace.total_duration_ms}ms` : '— ms'}
            </span>
          </div>
          <div
            className="px-2.5 py-1 rounded-sm flex items-center gap-1.5"
            style={{ border: '1px solid var(--line)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--text-dim)' }}>TOOLS</span>
            <span style={{ color: 'var(--text-primary)' }}>{executedCount}/{totalTools}</span>
          </div>
        </div>
      </header>

      {/* Main 2-column layout */}
      <div className="flex flex-1 overflow-hidden">
        <div
          className="w-[380px] shrink-0 overflow-y-auto"
          style={{ borderRight: '1px solid var(--line)', background: 'var(--bg-panel)' }}
        >
          <TerminalPanel onRunQuery={runQuery} loading={loading} error={error} />
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-7">
          <DAGViewer toolTrace={trace?.tool_trace} />

          {trace && (
            <div className="mt-8 space-y-3">
              <div className="font-data text-[11px]" style={{ color: 'var(--text-dim)' }}>
                {trace.summary}
              </div>

              {trace.evidence.length === 0 && (
                <div
                  className="font-data text-[12px] py-8 text-center rounded"
                  style={{ color: 'var(--text-dim)', border: '1px dashed var(--line)' }}
                >
                  no entities flagged for this query
                </div>
              )}

              {trace.evidence.map((item, i) => (
                <EvidenceCard key={item.customer_id} item={item} index={i} />
              ))}
            </div>
          )}

          {!trace && !loading && (
            <div className="mt-16 text-center">
              <div className="font-data text-[11px]" style={{ color: 'var(--text-dim)' }}>
                awaiting investigation query —
              </div>
              <div className="font-data text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                select a preset or type a custom query to begin
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
