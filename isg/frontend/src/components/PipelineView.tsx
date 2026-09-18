import React from 'react';
import { Stage } from '../api/isg';
import { StatusBadge } from './StatusBadge';

const STAGE_LABELS: Record<string, string> = {
  AUTHENTICATION: 'Authentication',
  CONTRACT: 'Contract',
  STRUCTURAL_VALIDATION: 'Structure',
  POLICY: 'Policy',
  CONSENT: 'Consent',
  PROVENANCE: 'Revenue System',
  FRESHNESS: 'Freshness',
  IDENTITY: 'Identity',
  SEMANTIC_VALIDATION: 'Semantics',
  SAFETY_KERNEL: 'Safety Kernel',
  EFFECT_AUTHORIZATION: 'Auth Lease',
  LIVE_CONSENT_RECHECK: 'Live Consent',
  LIVE_AUTHORIZATION_RECHECK: 'Live Auth',
  BOUNDED_EFFECT: 'Effect',
  OBSERVATION: 'Observation',
  RECOVERY: 'Recovery',
  IDEMPOTENCY: 'Idempotency',
  TERMINAL_STATE: 'Final State',
};

interface Props {
  stages: Stage[];
  finalStatus: string;
}

export function PipelineView({ stages, finalStatus }: Props) {
  if (!stages || stages.length === 0) return null;

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>
        ISG PROCESSING PIPELINE
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
        {stages.map((s, i) => (
          <React.Fragment key={i}>
            <div style={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 6,
              padding: '6px 10px',
              minWidth: 90,
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 10, color: '#64748b', marginBottom: 3 }}>
                {STAGE_LABELS[s.stage] || s.stage}
              </div>
              <StatusBadge status={s.result} />
              {s.detail && (
                <div style={{
                  fontSize: 9,
                  color: '#94a3b8',
                  marginTop: 3,
                  maxWidth: 120,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }} title={s.detail}>
                  {s.detail.substring(0, 40)}{s.detail.length > 40 ? '…' : ''}
                </div>
              )}
            </div>
            {i < stages.length - 1 && (
              <span style={{ color: '#475569', fontSize: 14 }}>→</span>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
