const TIER_CONFIG = {
  HIGH_REPORT: { color: 'var(--accent-risk)', bg: 'var(--accent-risk-dim)', border: 'rgba(251, 113, 133, 0.3)', label: 'HIGH · REPORT' },
  MEDIUM_REVIEW: { color: 'var(--accent-warn)', bg: 'var(--accent-warn-dim)', border: 'rgba(251, 191, 36, 0.3)', label: 'MEDIUM · REVIEW' },
  LOW_MONITOR: { color: 'var(--text-secondary)', bg: 'var(--bg-raised)', border: 'var(--line)', label: 'LOW · MONITOR' },
};

export default function EvidenceCard({ item, index }) {
  const tier = TIER_CONFIG[item.risk_tier];

  return (
    <div
      className="rounded-lg overflow-hidden animate-node-arrive"
      style={{
        background: 'var(--bg-panel)',
        border: `1px solid ${tier.border}`,
        animationDelay: `${index * 60}ms`,
      }}
    >
      {/* Header strip — colored by severity */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ background: tier.bg, borderBottom: `1px solid ${tier.border}` }}
      >
        <div className="flex items-baseline gap-2">
          <span className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>CUSTOMER</span>
          <span className="font-display font-bold text-[15px]" style={{ color: 'var(--text-primary)' }}>
            {item.customer_id}
          </span>
        </div>
        <span
          className="font-data font-semibold text-[10.5px] px-2 py-1 rounded"
          style={{ color: tier.color, background: 'rgba(0,0,0,0.25)' }}
        >
          {tier.label}
        </span>
      </div>

      <div className="p-4 space-y-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1.5">
          {item.statute_reference && (
            <div className="font-data text-[11px]">
              <span style={{ color: 'var(--text-dim)' }}>STATUTE </span>
              <span style={{ color: 'var(--text-secondary)' }}>{item.statute_reference}</span>
            </div>
          )}
          {item.rule_triggered && (
            <div className="font-data text-[11px]">
              <span style={{ color: 'var(--text-dim)' }}>RULE </span>
              <span style={{ color: 'var(--text-secondary)' }}>{item.rule_triggered}</span>
            </div>
          )}
        </div>

        {item.hop_trace && item.hop_trace.length > 0 && (
          <div className="rounded-md p-3" style={{ background: 'var(--bg-void)', border: '1px solid var(--line)' }}>
            <div className="font-data text-[9.5px] tracking-wide mb-2" style={{ color: 'var(--text-dim)' }}>
              MULTI-HOP TRACE
            </div>
            <div className="space-y-0.5">
              {item.hop_trace.map((hop, i) => (
                <div key={i} className="font-data text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ color: hop.startsWith('[HOP 1]') ? 'var(--accent-warn)' : 'var(--accent-live)' }}>
                    {hop.match(/^\[HOP \d+\]/)?.[0]}
                  </span>
                  {' '}{hop.replace(/^\[HOP \d+\]\s*/, '')}
                </div>
              ))}
            </div>
          </div>
        )}

        {item.ml_deviation_drivers && item.ml_deviation_drivers.length > 0 && (
          <div className="rounded-md p-3" style={{ background: 'var(--bg-void)', border: '1px solid var(--line)' }}>
            <div className="font-data text-[9.5px] tracking-wide mb-2" style={{ color: 'var(--text-dim)' }}>
              ML DEVIATION DRIVERS {item.ml_anomaly_score != null && `· score ${item.ml_anomaly_score}`}
            </div>
            <div className="flex flex-wrap gap-2">
              {item.ml_deviation_drivers.map((d, i) => (
                <div
                  key={i}
                  className="font-data text-[10.5px] px-2 py-1 rounded"
                  style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)' }}
                >
                  {d.feature} <span style={{ color: 'var(--accent-warn)' }}>z={d.zscore}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <span className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>RECOMMENDED ACTION</span>
          <span className="font-display font-semibold text-[12px]" style={{ color: 'var(--text-primary)' }}>
            {item.recommended_action}
          </span>
        </div>
      </div>
    </div>
  );
}
