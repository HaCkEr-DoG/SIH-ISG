import React from 'react';

const COLOR_MAP: Record<string, { bg: string; text: string; label: string }> = {
  SUCCESS:                  { bg: '#166534', text: '#dcfce7', label: 'SUCCESS' },
  ALLOW:                    { bg: '#166534', text: '#dcfce7', label: 'ALLOWED' },
  QUARANTINED:              { bg: '#92400e', text: '#fef3c7', label: 'QUARANTINED' },
  QUARANTINE:               { bg: '#92400e', text: '#fef3c7', label: 'QUARANTINED' },
  REJECTED:                 { bg: '#7f1d1d', text: '#fee2e2', label: 'REJECTED' },
  REJECT:                   { bg: '#7f1d1d', text: '#fee2e2', label: 'REJECTED' },
  FAILED:                   { bg: '#1e1b4b', text: '#e0e7ff', label: 'FAILED' },
  UNKNOWN_RESULT:           { bg: '#374151', text: '#f9fafb', label: 'UNKNOWN' },
  DEFER:                    { bg: '#374151', text: '#f9fafb', label: 'UNKNOWN' },
  RECONCILIATION_REQUIRED:  { bg: '#312e81', text: '#e0e7ff', label: 'RECONCILIATION REQ.' },
  PROCESSING:               { bg: '#1e3a5f', text: '#bfdbfe', label: 'PROCESSING' },
  INITIATED:                { bg: '#374151', text: '#d1d5db', label: 'INITIATED' },
  PASS:                     { bg: '#14532d', text: '#dcfce7', label: 'PASS' },
  BLOCKED:                  { bg: '#7f1d1d', text: '#fee2e2', label: 'BLOCKED' },
  VALID:                    { bg: '#14532d', text: '#dcfce7', label: 'VALID' },
  REVOKED:                  { bg: '#7f1d1d', text: '#fee2e2', label: 'REVOKED' },
  NOT_FOUND:                { bg: '#374151', text: '#d1d5db', label: 'NOT FOUND' },
  FOUND:                    { bg: '#1e3a5f', text: '#bfdbfe', label: 'FOUND' },
  ACCEPTED:                 { bg: '#14532d', text: '#dcfce7', label: 'ACCEPTED' },
  ACCEPT:                   { bg: '#14532d', text: '#dcfce7', label: 'ACCEPTED' },
  VERIFIED:                 { bg: '#14532d', text: '#dcfce7', label: 'VERIFIED' },
  EXECUTED:                 { bg: '#14532d', text: '#dcfce7', label: 'EXECUTED' },
  LEASE_ISSUED:             { bg: '#1e3a5f', text: '#bfdbfe', label: 'LEASE ISSUED' },
  MULTIPLE_CANDIDATES:      { bg: '#92400e', text: '#fef3c7', label: 'MULTI-CANDIDATES' },
};

export function StatusBadge({ status }: { status: string }) {
  const s = (status || '').toUpperCase();
  const cfg = COLOR_MAP[s] || { bg: '#374151', text: '#9ca3af', label: s };
  return (
    <span style={{
      background: cfg.bg,
      color: cfg.text,
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.5px',
      display: 'inline-block',
      fontFamily: 'monospace',
    }}>
      {cfg.label}
    </span>
  );
}
