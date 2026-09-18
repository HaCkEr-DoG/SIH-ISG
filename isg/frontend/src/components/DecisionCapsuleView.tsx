import React from 'react';
import { DecisionCapsule } from '../api/isg';
import { StatusBadge } from './StatusBadge';

interface Props {
  capsule: DecisionCapsule;
  onClose: () => void;
}

export function DecisionCapsuleView({ capsule, onClose }: Props) {
  const s = capsule.summary as Record<string, { result?: string; detail?: string } | null>;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div style={{
        background: '#0f172a', border: '1px solid #334155', borderRadius: 10,
        maxWidth: 900, width: '100%', maxHeight: '90vh', overflow: 'auto', padding: 28,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 2, fontWeight: 700 }}>
              ISG DECISION CAPSULE
            </div>
            <div style={{ fontSize: 20, color: '#f1f5f9', fontWeight: 700, marginTop: 4 }}>
              {capsule.applicant_name}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace', marginTop: 2 }}>
              TX: {capsule.transaction_id}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <StatusBadge status={capsule.final_state} />
            <div style={{ marginTop: 6 }}>
              <StatusBadge status={capsule.safety_decision || capsule.final_state} />
            </div>
            <button onClick={onClose} style={{
              marginTop: 8, background: '#1e293b', color: '#94a3b8', border: 'none',
              padding: '4px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
            }}>Close</button>
          </div>
        </div>

        {/* Decision block */}
        <DecisionBlock
          final={capsule.final_state}
          reason={capsule.quarantine_reason || capsule.rejection_reason}
        />

        {/* Summary grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16 }}>
          <SummaryCard label="WHO" value={s.who as any || '—'} />
          <SummaryCard label="WHAT" value={s.what as any || '—'} />
          <SummaryCard label="POLICY" result={s.policy} />
          <SummaryCard label="CONTRACT" result={s.contract} />
          <SummaryCard label="SEMANTIC CHECK" result={s.semantic_check} />
          <SummaryCard label="IDENTITY DECISION" result={s.identity_decision} />
          <SummaryCard label="INITIAL CONSENT" result={s.consent_initial} />
          <SummaryCard label="LIVE CONSENT RECHECK" result={s.consent_recheck} />
          <SummaryCard label="SAFETY KERNEL" result={s.safety_kernel} />
          <SummaryCard label="EFFECT AUTHORIZATION" result={s.effect_authorization} />
          <SummaryCard label="OBSERVATION" result={s.observation} />
          <SummaryCard label="RECOVERY" result={s.recovery} />
        </div>

        {/* Effect status */}
        <div style={{
          background: '#1e293b', borderRadius: 6, padding: 12, marginTop: 14,
          display: 'flex', gap: 20,
        }}>
          <EffectStatus label="EFFECT AUTHORIZED" on={capsule.effect_authorized} />
          <EffectStatus label="EFFECT OBSERVED" on={capsule.effect_observed} />
          <EffectStatus label="EFFECT VERIFIED" on={capsule.effect_verified} />
        </div>

        {/* Audit trail */}
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>
            AUDIT TRAIL ({capsule.audit_trail.length} events)
          </div>
          <div style={{ maxHeight: 260, overflow: 'auto' }}>
            {capsule.audit_trail.map((e) => (
              <div key={e.sequence} style={{
                display: 'flex', gap: 10, padding: '6px 0',
                borderBottom: '1px solid #1e293b', alignItems: 'flex-start',
              }}>
                <span style={{ color: '#475569', fontSize: 11, width: 20, flexShrink: 0, fontFamily: 'monospace' }}>
                  {e.sequence}
                </span>
                <span style={{ color: '#64748b', fontSize: 11, width: 160, flexShrink: 0 }}>
                  {e.stage}
                </span>
                <StatusBadge status={e.result} />
                <span style={{ color: '#94a3b8', fontSize: 11, flex: 1 }}>
                  {e.detail}
                </span>
                <span style={{ color: '#374151', fontSize: 9, fontFamily: 'monospace', flexShrink: 0 }}>
                  {e.payload_hash?.substring(0, 8)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 12, fontSize: 10, color: '#475569', fontStyle: 'italic' }}>
          {capsule.prototype_disclaimer}
        </div>
      </div>
    </div>
  );
}

function DecisionBlock({ final, reason }: { final: string; reason: string | null }) {
  const isGood = final === 'SUCCESS';
  return (
    <div style={{
      background: isGood ? '#14532d33' : '#7f1d1d33',
      border: `1px solid ${isGood ? '#166534' : '#7f1d1d'}`,
      borderRadius: 6, padding: 14,
    }}>
      <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>DECISION</div>
      <div style={{ fontSize: 22, color: isGood ? '#4ade80' : '#f87171', fontWeight: 800 }}>
        {final}
      </div>
      {reason && (
        <div style={{ fontSize: 12, color: '#d1d5db', marginTop: 6 }}>
          <strong>Why:</strong> {reason}
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label, value, result,
}: {
  label: string;
  value?: string;
  result?: { result?: string; detail?: string } | null;
}) {
  if (!result && !value) return null;
  return (
    <div style={{
      background: '#1e293b', borderRadius: 6, padding: 10,
    }}>
      <div style={{ fontSize: 10, color: '#64748b', fontWeight: 700, letterSpacing: 0.5, marginBottom: 4 }}>
        {label}
      </div>
      {value && <div style={{ fontSize: 12, color: '#e2e8f0' }}>{value}</div>}
      {result && (
        <>
          <StatusBadge status={result.result || '—'} />
          {result.detail && (
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
              {result.detail?.substring(0, 120)}{result.detail && result.detail.length > 120 ? '…' : ''}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function EffectStatus({ label, on }: { label: string; on: boolean }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 4 }}>{label}</div>
      <span style={{ fontSize: 16 }}>{on ? '✓' : '✗'}</span>
      <div style={{ fontSize: 10, color: on ? '#4ade80' : '#f87171' }}>{on ? 'YES' : 'NO'}</div>
    </div>
  );
}
