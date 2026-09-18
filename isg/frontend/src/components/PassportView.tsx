import React, { useEffect, useState } from 'react';
import { listPassports, getPassport } from '../api/isg';

interface Passport {
  system_id: string;
  name: string;
  owner: string;
  interface: string;
  schema_version: string;
  schema_hash: string;
  capabilities: Record<string, boolean>;
  data_authority: string;
  status: string;
  description: string;
  id_scheme: string;
  sample_fields: string[];
  color: string;
}

export default function PassportView() {
  const [passports, setPassports] = useState<Passport[]>([]);
  const [selected, setSelected] = useState<Passport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPassports().then(r => { setPassports(r.data); setLoading(false); });
  }, []);

  const select = async (id: string) => {
    const r = await getPassport(id);
    setSelected(r.data);
  };

  if (loading) return <div style={styles.loading}>Loading passport registry…</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>System Passport Registry</h2>
        <p style={styles.subtitle}>
          Every system connected to ISG declares a passport: capabilities, schema version,
          data authority, and identity scheme. ISG validates passports before permitting any
          interoperability.
        </p>
      </div>

      <div style={styles.grid}>
        {passports.map(p => (
          <button key={p.system_id} style={{ ...styles.card, borderTopColor: p.color }}
            onClick={() => select(p.system_id)}>
            <div style={{ ...styles.cardId, color: p.color }}>{p.system_id}</div>
            <div style={styles.cardName}>{p.name}</div>
            <div style={styles.cardOwner}>{p.owner}</div>
            <div style={styles.badgeRow}>
              <span style={{ ...styles.badge, background: p.status === 'ACTIVE' ? '#14532d' : '#7f1d1d' }}>
                {p.status}
              </span>
              <span style={styles.badgeGray}>{p.schema_version}</span>
            </div>
            <div style={styles.caps}>
              {Object.entries(p.capabilities).map(([k, v]) => (
                <span key={k} style={{ ...styles.cap, opacity: v ? 1 : 0.3 }}>
                  {v ? '✓' : '✗'} {k}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div style={styles.detail}>
          <div style={styles.detailHeader}>
            <h3 style={{ color: selected.color, margin: 0 }}>{selected.name}</h3>
            <button style={styles.closeBtn} onClick={() => setSelected(null)}>✕</button>
          </div>
          <table style={styles.table}>
            <tbody>
              {[
                ['System ID', selected.system_id],
                ['Owner', selected.owner],
                ['Interface', selected.interface],
                ['Schema Version', selected.schema_version],
                ['Schema Hash', <code style={styles.code}>{selected.schema_hash}</code>],
                ['Data Authority', selected.data_authority],
                ['ID Scheme', selected.id_scheme],
                ['Status', selected.status],
              ].map(([k, v]) => (
                <tr key={k as string}>
                  <td style={styles.td1}>{k}</td>
                  <td style={styles.td2}>{v as React.ReactNode}</td>
                </tr>
              ))}
              <tr>
                <td style={styles.td1}>Sample Fields</td>
                <td style={styles.td2}>
                  {selected.sample_fields.map(f => (
                    <code key={f} style={{ ...styles.code, marginRight: 6 }}>{f}</code>
                  ))}
                </td>
              </tr>
              <tr>
                <td style={styles.td1}>Description</td>
                <td style={{ ...styles.td2, color: '#9ca3af', fontStyle: 'italic' }}>{selected.description}</td>
              </tr>
            </tbody>
          </table>
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
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginBottom: 24 },
  card: {
    background: '#1f2937', border: 'none', borderTop: '3px solid', borderRadius: 8,
    padding: 16, textAlign: 'left', cursor: 'pointer', transition: 'transform 0.15s',
  },
  cardId: { fontSize: 11, fontWeight: 700, letterSpacing: 1, marginBottom: 4 },
  cardName: { fontSize: 16, fontWeight: 600, color: '#f9fafb', marginBottom: 4 },
  cardOwner: { fontSize: 12, color: '#9ca3af', marginBottom: 10 },
  badgeRow: { display: 'flex', gap: 6, marginBottom: 10 },
  badge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, color: '#fff' },
  badgeGray: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#374151', color: '#d1d5db' },
  caps: { display: 'flex', flexWrap: 'wrap', gap: 4 },
  cap: { fontSize: 10, color: '#d1d5db', background: '#374151', padding: '1px 5px', borderRadius: 3 },
  detail: { background: '#1f2937', borderRadius: 8, padding: 24 },
  detailHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  closeBtn: { background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 18 },
  table: { width: '100%', borderCollapse: 'collapse' },
  td1: { padding: '8px 12px 8px 0', color: '#9ca3af', fontSize: 13, width: 160, verticalAlign: 'top' },
  td2: { padding: '8px 0', color: '#f9fafb', fontSize: 13, verticalAlign: 'top' },
  code: { background: '#374151', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', fontSize: 12, color: '#93c5fd' },
};
