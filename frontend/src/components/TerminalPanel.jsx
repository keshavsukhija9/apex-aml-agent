import { useState } from 'react';

const PRESETS = [
  { n: '01', label: 'Structuring Search', sub: 'last 30 days', query: 'Find structuring patterns in the last 30 days' },
  { n: '02', label: 'Sub-10K Threshold', sub: 'direct rule aggregation', query: 'Which customers made 10+ transactions under $10,000?' },
  { n: '03', label: 'Entity Hop-Trace', sub: 'customer 9006', query: 'Is customer 9006 suspicious?' },
  { n: '04', label: 'Global Profiling', sub: 'dataset-wide EDA', query: 'Profile global dataset transaction distribution' },
];

export default function TerminalPanel({ onRunQuery, loading, error }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !loading) onRunQuery(input.trim());
  };

  return (
    <div className="p-5 flex flex-col h-full">
      <div className="font-data text-[10px] tracking-wider mb-4" style={{ color: 'var(--text-dim)' }}>
        INVESTIGATION QUERIES
      </div>

      <div className="space-y-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.query}
            onClick={() => onRunQuery(p.query)}
            disabled={loading}
            className="w-full text-left px-3 py-2.5 rounded-md transition-all duration-150 group disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ background: 'var(--bg-raised)', border: '1px solid var(--line)' }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--line-bright)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--line)'; }}
          >
            <div className="flex items-baseline gap-2">
              <span className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>{p.n}</span>
              <span className="font-display font-medium text-[12.5px]" style={{ color: 'var(--text-primary)' }}>
                {p.label}
              </span>
            </div>
            <div className="font-data text-[10px] mt-0.5 ml-6" style={{ color: 'var(--text-dim)' }}>
              {p.sub}
            </div>
          </button>
        ))}
      </div>

      <div className="flex-1" />

      <form onSubmit={handleSubmit} className="pt-4 space-y-2" style={{ borderTop: '1px solid var(--line)' }}>
        <div
          className="flex items-center gap-2 rounded-md px-3 py-2.5"
          style={{ background: 'var(--bg-raised)', border: '1px solid var(--line)' }}
        >
          <span className="font-data text-[13px]" style={{ color: 'var(--accent-live)' }}>{'>'}</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="custom investigation query..."
            className="flex-1 bg-transparent outline-none font-data text-[12px]"
            style={{ color: 'var(--text-primary)' }}
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-full py-2.5 rounded-md font-display font-semibold text-[12.5px] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            background: loading ? 'var(--bg-raised)' : 'var(--text-primary)',
            color: loading ? 'var(--text-secondary)' : 'var(--bg-void)',
          }}
        >
          {loading ? 'EXECUTING…' : 'EXECUTE'}
        </button>
      </form>

      {error && (
        <div
          className="mt-3 px-3 py-2 rounded-md font-data text-[11px]"
          style={{ background: 'var(--accent-risk-dim)', border: '1px solid rgba(251, 113, 133, 0.25)', color: 'var(--accent-risk)' }}
        >
          ERROR: {error}
        </div>
      )}
    </div>
  );
}
