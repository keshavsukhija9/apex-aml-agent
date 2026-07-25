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
    <div className="h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-mono flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-zinc-900/40">
        <div className="font-bold tracking-wider text-sm">
          APEX <span className="text-zinc-500">//</span> AML COMPLIANCE TERMINAL
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="px-2 py-1 rounded border border-zinc-800 text-zinc-400">
            [PARSER: {parserLabel}]
          </span>
          <span className="px-2 py-1 rounded border border-zinc-800 text-zinc-400">
            ⚡ {trace ? `${trace.total_duration_ms}ms` : '—'}
          </span>
          <span className="px-2 py-1 rounded border border-zinc-800 text-zinc-400">
            [TOOLS EXECUTED: {executedCount}/{totalTools}]
          </span>
        </div>
      </header>

      {/* Main 2-column layout */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-2/5 border-r border-zinc-800 overflow-y-auto">
          <TerminalPanel onRunQuery={runQuery} loading={loading} error={error} />
        </div>
        <div className="w-3/5 overflow-y-auto p-6 space-y-6">
          <DAGViewer toolTrace={trace?.tool_trace} />
          {trace && (
            <div className="space-y-3">
              <div className="text-xs text-zinc-500">{trace.summary}</div>
              {trace.evidence.length === 0 && (
                <div className="text-sm text-zinc-600 italic">No entities flagged for this query.</div>
              )}
              {trace.evidence.map((item) => (
                <EvidenceCard key={item.customer_id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
