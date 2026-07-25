const TIER_STYLES = {
  HIGH_REPORT: 'border-rose-800/60 bg-rose-950/40 text-rose-400',
  MEDIUM_REVIEW: 'border-amber-800/60 bg-amber-950/40 text-amber-400',
  LOW_MONITOR: 'border-zinc-800 bg-zinc-900/40 text-zinc-400',
};

export default function EvidenceCard({ item }) {
  return (
    <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30 space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-bold text-sm">Customer {item.customer_id}</div>
        <span className={`px-2 py-0.5 rounded border text-xs font-bold ${TIER_STYLES[item.risk_tier]}`}>
          {item.risk_tier.replace('_', ' / ')}
        </span>
      </div>

      {item.statute_reference && (
        <div className="text-xs text-zinc-400">
          <span className="text-zinc-600">STATUTE:</span> {item.statute_reference}
        </div>
      )}

      {item.rule_triggered && (
        <div className="text-xs text-zinc-400">
          <span className="text-zinc-600">RULE:</span> {item.rule_triggered}
        </div>
      )}

      {item.hop_trace && item.hop_trace.length > 0 && (
        <div className="bg-zinc-950/60 border border-zinc-800/60 rounded p-2 space-y-0.5">
          <div className="text-[10px] text-zinc-600 mb-1">MULTI-HOP TRACE</div>
          {item.hop_trace.map((hop, i) => (
            <div key={i} className="text-[11px] text-zinc-400">{hop}</div>
          ))}
        </div>
      )}

      {item.ml_deviation_drivers && item.ml_deviation_drivers.length > 0 && (
        <div className="bg-zinc-950/60 border border-zinc-800/60 rounded p-2 space-y-0.5">
          <div className="text-[10px] text-zinc-600 mb-1">
            ML DEVIATION DRIVERS {item.ml_anomaly_score != null && `(score: ${item.ml_anomaly_score})`}
          </div>
          {item.ml_deviation_drivers.map((d, i) => (
            <div key={i} className="text-[11px] text-zinc-400">
              {d.feature}: z={d.zscore}
            </div>
          ))}
        </div>
      )}

      <div className="pt-2 border-t border-zinc-800/60 text-xs">
        <span className="text-zinc-600">ACTION:</span>{' '}
        <span className="text-zinc-200 font-medium">{item.recommended_action}</span>
      </div>
    </div>
  );
}
