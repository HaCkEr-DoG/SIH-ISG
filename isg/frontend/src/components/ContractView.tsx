import React, { useEffect, useState } from 'react';
import { listContracts, getContract } from '../api/isg';

interface FieldMapping {
  source_field: string;
  target_field: string;
  source_period: string;
  target_period: string;
  requires_transformation: boolean;
  transformation_authorized: boolean;
  note: string;
}

interface Contract {
  contract_id: string;
  version: number;
  source_system_id: string;
  source_system_name: string;
  target_system_id: string;
  target_system_name: string;
  purpose: string;
  status: string;
  description: string;
  consent_required: boolean;
  allowed_data_fields?: string[];
  identity_requirement?: string;
  freshness_rules?: { field: string; max_days: number; reason: string }[];
  allowed_effect?: string;
  policy_id?: string;
  policy_version?: string;
  effective_from?: string;
  field_mappings?: FieldMapping[];
}

export default function ContractView() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selected, setSelected] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listContracts().then(r => { setContracts(r.data); setLoading(false); });
  }, []);

  const select = async (id: string) => {
    const r = await getContract(id);
    setSelected(r.data);
  };

  if (loading) return <div style={styles.loading}>Loading contract registry…</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Contract Registry</h2>
        <p style={styles.subtitle}>
          Interoperability contracts are executable governance artifacts. They specify exactly
          which data may flow between which systems, under what conditions, and with what effects.
          ISG enforces every contract at every pipeline stage.
        </p>
      </div>

      <div style={styles.list}>
        {contracts.map(c => (
          <button key={c.contract_id} style={styles.card} onClick={() => select(c.contract_id)}>
            <div style={styles.cardTop}>
              <span style={styles.contractId}>{c.contract_id} v{c.version}</span>
              <span style={{ ...styles.badge, background: c.status === 'ACTIVE' ? '#14532d' : '#7f1d1d' }}>
                {c.status}
              </span>
            </div>
            <div style={styles.flow}>
              <span style={styles.systemChip}>{c.source_system_name}</span>
              <span style={styles.arrow}>→</span>
              <span style={styles.systemChip}>{c.target_system_name}</span>
            </div>
            <div style={styles.purpose}>{c.purpose}</div>
            <div style={styles.desc}>{c.description}</div>
          </button>
        ))}
      </div>

      {selected && (
        <div style={styles.detail}>
          <div style={styles.detailHeader}>
            <h3 style={styles.detailTitle}>{selected.contract_id} v{selected.version} — {selected.source_system_name} → {selected.target_system_name}</h3>
            <button style={styles.closeBtn} onClick={() => setSelected(null)}>✕</button>
          </div>

          <table style={styles.table}>
            <tbody>
              <tr><td style={styles.td1}>Purpose</td><td style={styles.td2}>{selected.purpose}</td></tr>
              <tr><td style={styles.td1}>Allowed Effect</td><td style={styles.td2}><code style={styles.code}>{selected.allowed_effect}</code></td></tr>
              <tr><td style={styles.td1}>Consent Required</td><td style={styles.td2}>{selected.consent_required ? '✓ Yes' : '✗ No'}</td></tr>
              <tr><td style={styles.td1}>Identity Requirement</td><td style={styles.td2}>{selected.identity_requirement}</td></tr>
              <tr><td style={styles.td1}>Policy</td><td style={styles.td2}>{selected.policy_id} {selected.policy_version}</td></tr>
              <tr><td style={styles.td1}>Effective From</td><td style={styles.td2}>{selected.effective_from}</td></tr>
            </tbody>
          </table>

          {selected.freshness_rules && selected.freshness_rules.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Freshness Rules</div>
              {selected.freshness_rules.map((r, i) => (
                <div key={i} style={styles.ruleRow}>
                  <code style={styles.code}>{r.field}</code>
                  <span style={styles.ruleVal}>≤ {r.max_days} days</span>
                  <span style={styles.ruleNote}>{r.reason}</span>
                </div>
              ))}
            </div>
          )}

          {selected.field_mappings && selected.field_mappings.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Field Mappings</div>
              {selected.field_mappings.map((m, i) => (
                <div key={i} style={styles.mappingCard}>
                  <div style={styles.mappingFlow}>
                    <div>
                      <code style={styles.code}>{m.source_field}</code>
                      <span style={styles.period}>{m.source_period}</span>
                    </div>
                    <span style={styles.arrow}>→</span>
                    <div>
                      <code style={styles.code}>{m.target_field}</code>
                      <span style={styles.period}>{m.target_period}</span>
                    </div>
                    <span style={{
                      ...styles.authBadge,
                      background: m.transformation_authorized ? '#14532d' : '#7f1d1d',
                    }}>
                      {m.transformation_authorized ? 'AUTHORIZED' : 'NOT AUTHORIZED'}
                    </span>
                  </div>
                  <div style={styles.mappingNote}>{m.note}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '0 0 32px' },
  header: { marginBottom: 24 },
  title: { fontSize: 20, fontWeight: 700, color: '#f9fafb', margin: '0 0 8px' },
  subtitle: { color: '#9ca3af', margin: 0, fontSize: 14, lineHeight: 1.6 },
  loading: { padding: 32, color: '#9ca3af', textAlign: 'center' },
  list: { display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 },
  card: {
    background: '#1f2937', border: 'none', borderLeft: '3px solid #3b82f6',
    borderRadius: 8, padding: 16, textAlign: 'left', cursor: 'pointer',
  },
  cardTop: { display: 'flex', justifyContent: 'space-between', marginBottom: 8 },
  contractId: { fontFamily: 'monospace', fontWeight: 700, color: '#93c5fd', fontSize: 14 },
  badge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, color: '#fff' },
  flow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 },
  systemChip: { background: '#374151', padding: '2px 8px', borderRadius: 4, fontSize: 12, color: '#e5e7eb' },
  arrow: { color: '#6b7280', fontSize: 16 },
  purpose: { fontSize: 12, color: '#60a5fa', marginBottom: 4 },
  desc: { fontSize: 12, color: '#9ca3af', lineHeight: 1.5 },
  detail: { background: '#1f2937', borderRadius: 8, padding: 24 },
  detailHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  detailTitle: { fontSize: 16, fontWeight: 700, color: '#f9fafb', margin: 0, flex: 1 },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 18, marginLeft: 16 },
  table: { width: '100%', borderCollapse: 'collapse', marginBottom: 16 },
  td1: { padding: '6px 12px 6px 0', color: '#9ca3af', fontSize: 13, width: 180 },
  td2: { padding: '6px 0', color: '#f9fafb', fontSize: 13 },
  code: { background: '#374151', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', fontSize: 12, color: '#93c5fd' },
  section: { marginTop: 16 },
  sectionTitle: { fontSize: 12, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 },
  ruleRow: { display: 'flex', gap: 12, alignItems: 'baseline', marginBottom: 6 },
  ruleVal: { color: '#fbbf24', fontSize: 12, fontWeight: 600 },
  ruleNote: { color: '#9ca3af', fontSize: 12 },
  mappingCard: { background: '#111827', borderRadius: 6, padding: 12, marginBottom: 8 },
  mappingFlow: { display: 'flex', gap: 12, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' },
  period: { fontSize: 10, color: '#9ca3af', marginLeft: 4 },
  authBadge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, color: '#fff' },
  mappingNote: { fontSize: 12, color: '#9ca3af', lineHeight: 1.5 },
};
