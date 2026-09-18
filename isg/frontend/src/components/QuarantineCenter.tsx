import React, { useEffect, useState } from 'react';
import { listTransactions, getDecisionCapsule } from '../api/isg';

interface Transaction {
  transaction_id: string;
  application_id: string;
  applicant_name: string;
  status: string;
  safety_decision: string | null;
  quarantine_reason: string | null;
  created_at: string;
  state_version: number;
  effect_authorized: boolean;
  effect_observed: boolean;
}

export default function QuarantineCenter() {
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    const r = await listTransactions();
    setTxns(r.data);
    setLoading(false);
  };

  const quarantined = txns.filter(t => t.status === 'QUARANTINED' || t.safety_decision === 'QUARANTINE');
  const allTerminal = txns.filter(t =>
    ['SUCCESS', 'REJECTED', 'QUARANTINED', 'FAILED', 'COMPENSATED', 'CANCELLED', 'EXPIRED'].includes(t.status)
  );

  const openDetail = async (txId: string) => {
    setDetailLoading(true);
    const r = await getDecisionCapsule(txId);
    setSelected(r.data);
    setDetailLoading(false);
  };

  const statusColor: Record<string, string> = {
    SUCCESS: '#4ade80',
    REJECTED: '#f87171',
    QUARANTINED: '#fbbf24',
    FAILED: '#f87171',
    COMPENSATED: '#60a5fa',
    CANCELLED: '#9ca3af',
    PENDING: '#6b7280',
  };

  if (loading) return <div style={styles.loading}>Loading transactions…</div>;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Quarantine Center & Transaction Review</h2>
      <p style={styles.subtitle}>
        Quarantined transactions require human review before any resolution. No automated
        system may resolve a QUARANTINED transaction. All terminal states are immutable.
      </p>

      <div style={styles.stats}>
        <div style={styles.statCard}>
          <div style={{ ...styles.statNum, color: '#fbbf24' }}>{quarantined.length}</div>
          <div style={styles.statLabel}>Quarantined</div>
        </div>
        <div style={styles.statCard}>
          <div style={{ ...styles.statNum, color: '#4ade80' }}>
            {txns.filter(t => t.status === 'SUCCESS').length}
          </div>
          <div style={styles.statLabel}>Succeeded</div>
        </div>
        <div style={styles.statCard}>
          <div style={{ ...styles.statNum, color: '#f87171' }}>
            {txns.filter(t => t.status === 'REJECTED').length}
          </div>
          <div style={styles.statLabel}>Rejected</div>
        </div>
        <div style={styles.statCard}>
          <div style={{ ...styles.statNum, color: '#9ca3af' }}>{txns.length}</div>
          <div style={styles.statLabel}>Total</div>
        </div>
      </div>

      {/* Quarantine table */}
      {quarantined.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <span style={styles.warningIcon}>⚠</span> Quarantined — Require Human Review
          </div>
          <table style={styles.table}>
            <thead>
              <tr>
                {['Transaction ID', 'Application', 'Applicant', 'Quarantine Reason', 'State v'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {quarantined.map(t => (
                <tr key={t.transaction_id} style={styles.tr} onClick={() => openDetail(t.transaction_id)}>
                  <td style={styles.td}><code style={styles.code}>{t.transaction_id}</code></td>
                  <td style={styles.td}>{t.application_id}</td>
                  <td style={styles.td}>{t.applicant_name}</td>
                  <td style={{ ...styles.td, color: '#fbbf24', fontSize: 12 }}>{t.quarantine_reason || '—'}</td>
                  <td style={styles.td}>{t.state_version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* All transactions table */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>All Transactions</div>
        <table style={styles.table}>
          <thead>
            <tr>
              {['Transaction ID', 'Applicant', 'Status', 'Effect Auth', 'Effect Obs'].map(h => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {txns.map(t => (
              <tr key={t.transaction_id} style={styles.tr} onClick={() => openDetail(t.transaction_id)}>
                <td style={styles.td}><code style={styles.code}>{t.transaction_id}</code></td>
                <td style={styles.td}>{t.applicant_name}</td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.badge,
                    color: statusColor[t.status] || '#9ca3af',
                    borderColor: statusColor[t.status] || '#9ca3af',
                  }}>{t.status}</span>
                </td>
                <td style={{ ...styles.td, textAlign: 'center', color: t.effect_authorized ? '#4ade80' : '#6b7280' }}>
                  {t.effect_authorized ? '✓' : '—'}
                </td>
                <td style={{ ...styles.td, textAlign: 'center', color: t.effect_observed ? '#4ade80' : '#6b7280' }}>
                  {t.effect_observed ? '✓' : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail Panel */}
      {(selected || detailLoading) && (
        <div style={styles.detail}>
          <div style={styles.detailHeader}>
            <h3 style={styles.detailTitle}>Decision Capsule</h3>
            <button style={styles.closeBtn} onClick={() => setSelected(null)}>✕</button>
          </div>
          {detailLoading ? (
            <div style={{ color: '#9ca3af', padding: 16 }}>Loading capsule…</div>
          ) : selected ? (
            <>
              <div style={styles.capsuleMeta}>
                <div><span style={styles.metaKey}>Transaction</span><code style={styles.code}>{selected.transaction_id}</code></div>
                <div><span style={styles.metaKey}>Applicant</span>{selected.applicant_name}</div>
                <div><span style={styles.metaKey}>Final State</span>
                  <span style={{ color: statusColor[selected.final_state] || '#9ca3af', fontWeight: 700 }}>
                    {selected.final_state}
                  </span>
                </div>
                {selected.quarantine_reason && (
                  <div><span style={styles.metaKey}>Quarantine Reason</span>
                    <span style={{ color: '#fbbf24' }}>{selected.quarantine_reason}</span>
                  </div>
                )}
                <div><span style={styles.metaKey}>Audit Events</span>{selected.audit_trail?.length}</div>
              </div>
              <div style={styles.auditTitle}>Audit Trail</div>
              {selected.audit_trail?.slice(0, 10).map((ev: any) => (
                <div key={ev.sequence} style={styles.auditRow}>
                  <span style={styles.auditSeq}>{ev.sequence}</span>
                  <span style={styles.auditStage}>{ev.stage}</span>
                  <span style={{
                    ...styles.auditResult,
                    color: ev.result === 'PASS' || ev.result === 'SUCCESS' ? '#4ade80'
                      : ev.result === 'QUARANTINED' || ev.result === 'FAIL' ? '#f87171' : '#fbbf24',
                  }}>{ev.result}</span>
                  <span style={styles.auditDetail}>{ev.detail}</span>
                </div>
              ))}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '0 0 32px' },
  title: { fontSize: 20, fontWeight: 700, color: '#f9fafb', margin: '0 0 8px' },
  subtitle: { color: '#9ca3af', margin: '0 0 20px', fontSize: 14, lineHeight: 1.6 },
  loading: { padding: 32, color: '#9ca3af', textAlign: 'center' },
  stats: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 },
  statCard: { background: '#1f2937', borderRadius: 8, padding: 16, textAlign: 'center' },
  statNum: { fontSize: 28, fontWeight: 900, marginBottom: 4 },
  statLabel: { fontSize: 12, color: '#9ca3af' },
  section: { background: '#1f2937', borderRadius: 8, padding: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 13, fontWeight: 700, color: '#9ca3af', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 },
  warningIcon: { color: '#fbbf24' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '6px 8px', fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', textAlign: 'left', borderBottom: '1px solid #374151' },
  tr: { cursor: 'pointer' },
  td: { padding: '8px', fontSize: 13, color: '#d1d5db', borderBottom: '1px solid #111827' },
  code: { background: '#374151', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', fontSize: 11, color: '#93c5fd' },
  badge: { border: '1px solid', padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700 },
  detail: { background: '#1f2937', borderRadius: 8, padding: 20, marginTop: 16 },
  detailHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 16 },
  detailTitle: { fontSize: 16, fontWeight: 700, color: '#f9fafb', margin: 0 },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 18 },
  capsuleMeta: { display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 },
  metaKey: { color: '#9ca3af', fontSize: 12, marginRight: 8, display: 'inline-block', minWidth: 130 },
  auditTitle: { fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', marginBottom: 8 },
  auditRow: { display: 'flex', gap: 8, padding: '4px 0', borderBottom: '1px solid #111827', alignItems: 'baseline' },
  auditSeq: { color: '#6b7280', fontSize: 11, minWidth: 20, fontFamily: 'monospace' },
  auditStage: { color: '#60a5fa', fontSize: 11, minWidth: 140, fontFamily: 'monospace' },
  auditResult: { fontSize: 11, fontWeight: 700, minWidth: 80 },
  auditDetail: { color: '#9ca3af', fontSize: 12 },
};
