import { useState } from 'react';
import { Copy, Check, ChevronDown } from 'lucide-react';

const TIER_CONFIG = {
  HIGH_REPORT: { color: '#fb7185', bg: 'rgba(136, 19, 55, 0.35)', border: 'rgba(251, 113, 133, 0.4)', label: 'HIGH RISK // SAR FILING MANDATED' },
  MEDIUM_REVIEW: { color: 'var(--accent-warn)', bg: 'var(--accent-warn-dim)', border: 'rgba(251, 191, 36, 0.3)', label: 'MEDIUM RISK // ANALYST REVIEW' },
  LOW_MONITOR: { color: 'var(--text-secondary)', bg: 'var(--bg-raised)', border: 'var(--line)', label: 'LOW RISK // ROUTINE MONITOR' },
};

function parseHop(hop) {
  const m = hop.match(/\[HOP (\d+)\]\s*(\S+)\s*->\s*(\S+)\s*\(\$([\d,.]+)\)/);
  if (!m) return null;
  return { hopNum: m[1], from: m[2], to: m[3], amount: m[4] };
}

export default function EvidenceCard({ item, index }) {
  const [copied, setCopied] = useState(false);
  const [narrativeOpen, setNarrativeOpen] = useState(false);
  const tier = TIER_CONFIG[item.risk_tier];

  const parsedHops = (item.hop_trace || []).map(parseHop).filter(Boolean);
  const hop1 = parsedHops.find(h => h.hopNum === '1');
  const hop2s = parsedHops.filter(h => h.hopNum === '2');

  const copyNarrative = () => {
    navigator.clipboard.writeText(item.explanation);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      className="rounded-lg overflow-hidden animate-node-arrive"
      style={{ background: 'var(--bg-panel)', border: `1px solid ${tier.border}`, animationDelay: `${index * 60}ms` }}
    >
      {/* Tactical risk header */}
      <div className="px-4 py-3" style={{ background: tier.bg, borderBottom: `1px solid ${tier.border}` }}>
        <div className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>CUSTOMER</span>
            <span className="font-display font-bold text-[16px]" style={{ color: 'var(--text-primary)' }}>{item.customer_id}</span>
          </div>
          <span className="font-data font-bold text-[10.5px] tracking-wide" style={{ color: tier.color }}>
            {tier.label}
          </span>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Statutory citation -- prominent, own row */}
        {item.statute_reference && (
          <div
            className="rounded-md px-3 py-2 font-data text-[11px]"
            style={{ background: 'var(--bg-void)', border: '1px solid var(--line)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--accent-warn)' }}>§ STATUTE </span>
            {item.statute_reference}
            {item.rule_triggered && <span style={{ color: 'var(--text-dim)' }}> · rule: {item.rule_triggered}</span>}
          </div>
        )}

        {/* Money-flow terminal */}
        {hop1 && (
          <div className="rounded-md p-3 overflow-x-auto" style={{ background: 'var(--bg-void)', border: '1px solid var(--line)' }}>
            <div className="font-data text-[9.5px] tracking-wide mb-2" style={{ color: 'var(--text-dim)' }}>
              MONEY-FLOW TRACE
            </div>
            <div className="font-data text-[11px] whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
              <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-raised)', color: 'var(--accent-warn)' }}>
                [{hop1.from}]
              </span>
              <span style={{ color: 'var(--text-dim)' }}> ──(${hop1.amount})──► </span>
              <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-raised)', color: 'var(--text-primary)' }}>
                [{hop1.to}]
              </span>
              {hop2s.length > 0 && (
                <>
                  <span style={{ color: 'var(--text-dim)' }}> ──(SPLIT x{hop2s.length})──► </span>
                  <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-raised)', color: 'var(--accent-live)' }}>
                    [ACCOUNT RING]
                  </span>
                </>
              )}
            </div>
            {hop2s.length > 0 && (
              <div className="mt-2 space-y-0.5 pl-2" style={{ borderLeft: '1px solid var(--line)' }}>
                {hop2s.map((h, i) => (
                  <div key={i} className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>
                    ↳ [{h.from}] → [{h.to}] <span style={{ color: 'var(--accent-live)' }}>${h.amount}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {item.ml_deviation_drivers && item.ml_deviation_drivers.length > 0 && (
          <div className="rounded-md p-3" style={{ background: 'var(--bg-void)', border: '1px solid var(--line)' }}>
            <div className="font-data text-[9.5px] tracking-wide mb-2" style={{ color: 'var(--text-dim)' }}>
              ML DEVIATION DRIVERS {item.ml_anomaly_score != null && `· score ${item.ml_anomaly_score}`}
            </div>
            <div className="flex flex-wrap gap-2">
              {item.ml_deviation_drivers.map((d, i) => (
                <div key={i} className="font-data text-[10.5px] px-2 py-1 rounded" style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)' }}>
                  {d.feature} <span style={{ color: 'var(--accent-warn)' }}>z={d.zscore}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evidence narrative -- honest labeling, not "SAR ready" */}
        <div>
          <button
            onClick={() => setNarrativeOpen(!narrativeOpen)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-md font-data text-[10.5px] transition-colors"
            style={{ background: 'var(--bg-raised)', border: '1px solid var(--line)', color: 'var(--text-secondary)' }}
          >
            <span>VIEW EVIDENCE NARRATIVE</span>
            <ChevronDown size={13} style={{ transform: narrativeOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>
          {narrativeOpen && (
            <div className="mt-2 rounded-md p-3" style={{ background: 'var(--bg-void)', border: '1px solid var(--line)' }}>
              <pre className="font-data text-[10.5px] whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {item.explanation}
              </pre>
              <button
                onClick={copyNarrative}
                className="mt-2 flex items-center gap-1.5 px-2.5 py-1.5 rounded font-data text-[10px] transition-colors"
                style={{ background: 'var(--bg-raised)', color: copied ? 'var(--accent-live)' : 'var(--text-secondary)', border: '1px solid var(--line)' }}
              >
                {copied ? <Check size={11} /> : <Copy size={11} />}
                {copied ? 'COPIED' : 'COPY EVIDENCE NARRATIVE'}
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="font-data text-[10px]" style={{ color: 'var(--text-dim)' }}>RECOMMENDED ACTION</span>
          <span className="font-display font-semibold text-[12px]" style={{ color: tier.color }}>
            {item.recommended_action}
          </span>
        </div>
      </div>
    </div>
  );
}
