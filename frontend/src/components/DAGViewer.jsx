const TOOL_META = {
  eda: { label: 'EDA', full: 'Exploratory Profiler' },
  feature_eng: { label: 'FEATURE_ENG', full: 'Feature Engine' },
  rules: { label: 'RULES', full: 'FinCEN Rule Engine' },
  ml: { label: 'ML', full: 'Isolation Forest' },
  graph: { label: 'GRAPH', full: 'Multi-Hop Graph' },
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
          Execution DAG
        </div>
        <div className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>
          dynamic tool routing — not a fixed pipeline
        </div>
      </div>

      <div className="relative">
        {/* Connector spine */}
        <div
          className="absolute left-0 right-0 h-px"
          style={{ top: '28px', background: 'var(--line)' }}
        />

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
                {/* Node dot on the spine */}
                <div className="flex justify-center relative" style={{ height: '28px' }}>
                  <div
                    className="w-2 h-2 rounded-full mt-[24px] relative z-10 transition-all duration-300"
                    style={{
                      background: isExecuted ? 'var(--accent-live)' : isSkipped ? 'var(--text-dim)' : 'var(--line-bright)',
                      boxShadow: isExecuted ? '0 0 8px rgba(52, 211, 153, 0.6)' : 'none',
                    }}
                  />
                </div>

                {/* Card */}
                <div
                  title={record?.reason || 'Awaiting query'}
                  className="mx-1 rounded-md px-3 py-2.5 transition-all duration-300"
                  style={{
                    background: isExecuted ? 'var(--accent-live-dim)' : 'var(--bg-raised)',
                    border: `1px solid ${isExecuted ? 'rgba(52, 211, 153, 0.25)' : 'var(--line)'}`,
                    opacity: isSkipped ? 0.5 : 1,
                  }}
                >
                  <div
                    className="font-data font-semibold text-[10px] tracking-tight truncate"
                    style={{
                      color: isExecuted ? 'var(--accent-live)' : isSkipped ? 'var(--text-dim)' : 'var(--text-secondary)',
                      textDecoration: isSkipped ? 'line-through' : 'none',
                    }}
                  >
                    {meta.label}
                  </div>
                  <div
                    className="font-data text-[9px] mt-1 truncate"
                    style={{ color: isExecuted ? 'rgba(52, 211, 153, 0.7)' : 'var(--text-dim)' }}
                  >
                    {isExecuted && record.duration_ms != null && `${record.duration_ms}ms`}
                    {isExecuted && record.duration_ms == null && 'done'}
                    {isSkipped && 'skipped'}
                    {!record && 'idle'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
