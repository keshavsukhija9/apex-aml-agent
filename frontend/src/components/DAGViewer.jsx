const TOOL_LABELS = {
  eda: 'EDA',
  feature_eng: 'FEATURE_ENG',
  rules: 'RULES',
  ml: 'ML',
  graph: 'GRAPH',
  risk: 'RISK',
  explain: 'EXPLAIN',
};

const DEFAULT_ORDER = ['eda', 'feature_eng', 'rules', 'ml', 'graph', 'risk', 'explain'];

export default function DAGViewer({ toolTrace }) {
  const nodesByTool = {};
  (toolTrace || []).forEach((t) => { nodesByTool[t.tool] = t; });

  return (
    <div>
      <div className="text-xs text-zinc-500 mb-3">EXECUTION DAG</div>
      <div className="grid grid-cols-4 gap-2">
        {DEFAULT_ORDER.map((toolName) => {
          const record = nodesByTool[toolName];
          const isExecuted = record?.status === 'executed';
          const isSkipped = record?.status === 'skipped';
          const isIdle = !record;

          let classes = 'border-zinc-800/40 bg-zinc-900/30 text-zinc-700';
          if (isExecuted) classes = 'border-emerald-800/60 bg-emerald-950/40 text-emerald-400';
          if (isSkipped) classes = 'border-zinc-800/40 bg-zinc-900/50 text-zinc-600 line-through';

          return (
            <div
              key={toolName}
              title={record?.reason || 'Not yet run'}
              className={`p-3 rounded border text-xs transition-colors ${classes}`}
            >
              <div className="font-bold">{TOOL_LABELS[toolName]}</div>
              <div className="mt-1 text-[10px]">
                {isExecuted && record.duration_ms != null && `EXECUTED ${record.duration_ms}ms`}
                {isSkipped && 'SKIPPED'}
                {isIdle && '· idle'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
