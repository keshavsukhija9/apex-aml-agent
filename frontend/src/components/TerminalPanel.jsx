import { useState } from 'react';
import { Terminal, Play } from 'lucide-react';

const PRESETS = [
  { label: '1. Structuring Search (30d)', query: 'Find structuring patterns in the last 30 days' },
  { label: '2. Sub-10k Threshold Rules', query: 'Which customers made 10+ transactions under $10,000?' },
  { label: '3. Entity 9006 Hop-Trace', query: 'Is customer 9006 suspicious?' },
  { label: '4. Global Dataset Profiling', query: 'Profile global dataset transaction distribution' },
];

export default function TerminalPanel({ onRunQuery, loading, error }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onRunQuery(input.trim());
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2 text-zinc-400 text-xs mb-2">
        <Terminal size={14} />
        <span>INVESTIGATION QUERIES</span>
      </div>

      <div className="space-y-2">
        {PRESETS.map((p) => (
          <button
            key={p.query}
            onClick={() => onRunQuery(p.query)}
            disabled={loading}
            className="w-full text-left px-3 py-2 rounded border border-zinc-800 bg-zinc-900/40
                       text-sm text-zinc-300 hover:bg-zinc-800/60 hover:border-zinc-700
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {p.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="pt-4 border-t border-zinc-800 space-y-2">
        <div className="flex items-center gap-2 bg-zinc-900/60 border border-zinc-800 rounded px-3 py-2">
          <span className="text-emerald-500 text-sm">{'>'}</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="enter custom investigation query..."
            className="flex-1 bg-transparent outline-none text-sm text-zinc-100 placeholder-zinc-600"
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-full flex items-center justify-center gap-2 py-2 rounded
                     bg-zinc-100 text-zinc-950 font-bold text-sm
                     hover:bg-zinc-200 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Play size={14} />
          {loading ? 'EXECUTING...' : 'EXECUTE'}
        </button>
      </form>

      {error && (
        <div className="px-3 py-2 rounded border border-rose-800/60 bg-rose-950/40 text-rose-400 text-xs">
          ERROR: {error}
        </div>
      )}
    </div>
  );
}
