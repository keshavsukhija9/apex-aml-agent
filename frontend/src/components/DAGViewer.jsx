const TOOL_META = {
  eda: { label: 'EDA', full: 'Exploratory Profiler' },
  feature_eng: { label: 'FEATURE_ENG', full: 'Feature Engine' },
  rules: { label: 'RULES', full: 'FinCEN Rule Engine' },
  ml: { label: 'ML', full: 'Isolation Forest' },
  graph: { label: 'GRAPH', full: 'Multi-Hop Traversal' },
  risk: { label: 'RISK', full: 'Risk Classifier' },
  explain: { label: 'EXPLAIN', full: 'Evidence Compiler' },
};

const ORDER = ['eda', 'feature_eng', 'rules', 'ml', 'graph', 'risk', 'explain'];

export default function DAGViewer({ toolTrace }) {
  const nodesByTool = {};
  (toolTrace || []).forEach((t) => { nodesByTool[t.tool] = t; });
  const hasTrace = !!toolTrace;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5">
        <div className="font-display font-semibold text-[13px]" style={{ color: 'var(--text-primary)' }}>
          Pipeline Routing Flow
        </div>
        <div className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>
          dynamic tool routing — not a fixed pipeline
        </div>
      </div>

      {/* SVG connector layer */}
      <div className="relative">
        <svg
          className="absolute pointer-events-none"
          style={{ top: '27px', left: 0, width: '100%', height: '2px' }}
          preserveAspectRatio="none"
        >
          <line
            x1="7%" y1="1" x2="93%" y2="1"
            stroke="var(--line)" strokeWidth="1"
          />
          {hasTrace && ORDER.map((toolName, i) => {
            if (i === 0) return null;
            const prev = nodesByTool[ORDER[i - 1]];
            const curr = nodesByTool[toolName];
            const bothActive = prev?.status === 'executed' && curr?.status === 'executed';
            if (!bothActive) return null;
            const x1 = ((i - 1) / (ORDER.length - 1)) * 86 + 7;
            const x2 = (i / (ORDER.length - 1)) * 86 + 7;
            return (
              <line
                key={toolName}
                x1={`${x1}%`} y1="1" x2={`${x2}%`} y2="1"
                stroke="var(--accent-live)" strokeWidth="1.5"
                strokeDasharray="4 3"
              >
                <animate attributeName="stroke-dashoffset" from="14" to="0" dur="0.6s" repeatCount="indefinite" />
              </line>
            );
          })}
        </svg>

        <div className="grid grid-cols-7 gap-0 relative">
          {ORDER.map((toolName, i) => {
            const record = nodesByTool[toolName];
            const meta = TOOL_META[toolName];
            const isExecuted = record?.status === 'executed';
            const isSkipped = record?.status === 'skipped';

            return (
              <div
                key={toolName}
                className={hasTrace ? 'animate-node-arrive' : ''}
                style={{ animationDelay: hasTrace ? `${i * 45}ms` : '0ms' }}
              >
                <div className="flex justify-center relative" style={{ height: '28px' }}>
                  <div
                    className="w-2 h-2 rounded-full mt-[24px] relative z-10 transition-all duration-300"
                    style={{
                      background: isExecuted ? 'var(--accent-live)' : isSkipped ? 'var(--line-bright)' : 'var(--line-bright)',
                      boxShadow: isExecuted ? '0 0 10px rgba(52, 211, 153, 0.7)' : 'none',
                      transform: isSkipped ? 'scale(0.6)' : 'scale(1)',
                    }}
                  />
                </div>

                <div
                  title={record?.reason || 'Awaiting query'}
                  className="mx-1 rounded-md px-2.5 py-2 transition-all duration-300"
                  style={{
                    background: isExecuted ? 'var(--accent-live-dim)' : 'var(--bg-raised)',
                    border: `1px solid ${isExecuted ? 'rgba(52, 211, 153, 0.3)' : 'var(--line)'}`,
                    opacity: isSkipped ? 0.45 : 1,
                  }}
                >
                  <div
                    className="font-data font-semibold text-[9.5px] tracking-tight truncate"
                    style={{
                      color: isExecuted ? 'var(--accent-live)' : 'var(--text-dim)',
                      textDecoration: isSkipped ? 'line-through' : 'none',
                    }}
                  >
                    {meta.label}
                  </div>
                  <div className="font-data text-[8.5px] mt-1" style={{ color: isExecuted ? 'rgba(52,211,153,0.7)' : 'var(--text-dim)' }}>
                    {isExecuted && record.duration_ms != null && `⚡ ${record.duration_ms}ms`}
                    {isExecuted && record.duration_ms == null && '✓ done'}
                    {isSkipped && '❌ skipped'}
                    {!record && 'idle'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Visible planner reasoning -- the highest-leverage fix: surface why, not just what */}
      {hasTrace && (
        <div className="mt-5 rounded-md p-3" style={{ background: 'var(--bg-panel)', border: '1px solid var(--line)' }}>
          <div className="font-data text-[9.5px] tracking-wide mb-2" style={{ color: 'var(--text-dim)' }}>
            PLANNER REASONING
          </div>
          <div className="space-y-1">
            {toolTrace.map((t) => (
              <div key={t.tool} className="flex items-start gap-2 font-data text-[10.5px]">
                <span
                  className="w-16 shrink-0 font-semibold"
                  style={{ color: t.status === 'executed' ? 'var(--accent-live)' : 'var(--text-dim)' }}
                >
                  {TOOL_META[t.tool].label}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>{t.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
