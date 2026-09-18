import React, { useState, useEffect } from 'react';
import {
  getAIMappingSuggestion,
  getMultilingualExamples,
  simulateSchemaDrift,
  resetSchemaDrift,
  getSchemaDriftStatus,
} from '../api/isg';

interface Check {
  check: string;
  result: string;
  note: string;
}

interface Suggestion {
  source_field: string;
  source_period: string;
  source_value_display: string;
  target_field: string;
  target_period: string;
  suggested_transformation: string;
  confidence: number;
  ai_reasoning: string;
  deterministic_result: string;
  deterministic_reason: string;
  deterministic_checks: Check[];
  temporal_coverage_provable: boolean;
  ai_authority: string;
}

interface MultilingualExample {
  source_language: string;
  source_text: string;
  target_field: string;
  confidence: number;
  method: string;
}

export default function AIMappingStudio() {
  const [period, setPeriod] = useState<'MONTHLY' | 'FINANCIAL_YEAR_ANNUAL'>('MONTHLY');
  const [value, setValue] = useState(25000);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [mlExamples, setMlExamples] = useState<MultilingualExample[]>([]);
  const [driftStatus, setDriftStatus] = useState<any>(null);
  const [driftLoading, setDriftLoading] = useState(false);

  useEffect(() => {
    getMultilingualExamples().then(r => setMlExamples(r.data));
    getSchemaDriftStatus().then(r => setDriftStatus(r.data));
  }, []);

  const runMapping = async () => {
    setLoading(true);
    try {
      const r = await getAIMappingSuggestion({
        source_period: period,
        source_value: value,
        target_period: 'FINANCIAL_YEAR_ANNUAL',
        period_reference: 'FY2025-26',
      });
      setSuggestion(r.data);
    } finally {
      setLoading(false);
    }
  };

  const toggleDrift = async () => {
    setDriftLoading(true);
    try {
      const r = driftStatus?.drift_detected
        ? await resetSchemaDrift()
        : await simulateSchemaDrift();
      setDriftStatus(r.data);
    } finally {
      setDriftLoading(false);
    }
  };

  const checkColor = (r: string) =>
    r === 'PASS' ? '#4ade80' : r === 'FAIL' ? '#f87171' : '#fbbf24';

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>AI Mapping Studio</h2>
      <p style={styles.subtitle}>
        AI suggests semantic field transformations. The deterministic safety engine always
        decides. <strong style={{ color: '#f87171' }}>ai_authority is always NONE.</strong>
      </p>

      {/* Invariant Banner */}
      <div style={styles.invariantBanner}>
        <span style={styles.invariantIcon}>🔒</span>
        <span>
          <strong>CRITICAL SAFETY INVARIANT:</strong> ai_was_final_authority = False always.
          AI identifies patterns and suggests mappings. The ISG deterministic safety engine
          makes every authorization decision. AI cannot authorize a government data exchange.
        </span>
      </div>

      {/* Mapping Demo */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Income Field Mapping Demo</div>
        <div style={styles.controls}>
          <label style={styles.label}>Source Period</label>
          <div style={styles.segmented}>
            {(['MONTHLY', 'FINANCIAL_YEAR_ANNUAL'] as const).map(p => (
              <button key={p} style={{ ...styles.seg, ...(period === p ? styles.segActive : {}) }}
                onClick={() => { setPeriod(p); setSuggestion(null); }}>
                {p === 'MONTHLY' ? 'Monthly' : 'Annual FY'}
              </button>
            ))}
          </div>
          <label style={styles.label}>Income Value (₹)</label>
          <input type="number" style={styles.input} value={value}
            onChange={e => setValue(Number(e.target.value))} min={1000} max={1000000} step={1000} />
          <button style={styles.runBtn} onClick={runMapping} disabled={loading}>
            {loading ? 'Analyzing…' : 'Get AI Suggestion + Safety Analysis'}
          </button>
        </div>

        {suggestion && (
          <div style={styles.result}>
            <div style={styles.twoCol}>
              {/* AI Side */}
              <div style={styles.panel}>
                <div style={styles.panelTitle}>🤖 AI Suggestion</div>
                <div style={styles.panelConfidence}>Confidence: {(suggestion.confidence * 100).toFixed(0)}%</div>
                <div style={styles.transformBox}>{suggestion.suggested_transformation}</div>
                <div style={styles.reasoning}>{suggestion.ai_reasoning}</div>
                <div style={{ ...styles.authTag, background: '#374151', color: '#fbbf24' }}>
                  ai_authority: {suggestion.ai_authority}
                </div>
              </div>

              {/* Deterministic Side */}
              <div style={{ ...styles.panel, borderColor: suggestion.deterministic_result === 'PASS' ? '#4ade80' : '#f87171' }}>
                <div style={styles.panelTitle}>⚙️ Deterministic Safety Analysis</div>
                <div style={{
                  ...styles.verdict,
                  color: suggestion.deterministic_result === 'PASS' ? '#4ade80' : '#f87171',
                }}>
                  {suggestion.deterministic_result}
                </div>
                <div style={styles.reasoning}>{suggestion.deterministic_reason}</div>
                <div style={styles.checksTitle}>Checks:</div>
                {suggestion.deterministic_checks.map((c, i) => (
                  <div key={i} style={styles.checkRow}>
                    <span style={{ ...styles.checkResult, color: checkColor(c.result) }}>{c.result}</span>
                    <span style={styles.checkName}>{c.check}</span>
                    <span style={styles.checkNote}>{c.note}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Multilingual Examples */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Multilingual Field Matching (AI)</div>
        <p style={styles.sectionDesc}>
          AI identifies semantic equivalence across Indian languages. The field name
          match is a suggestion; ISG contract governs what data may actually flow.
        </p>
        <div style={styles.mlGrid}>
          {mlExamples.map((ex, i) => (
            <div key={i} style={styles.mlCard}>
              <div style={styles.mlLang}>{ex.source_language}</div>
              <div style={styles.mlText}>{ex.source_text}</div>
              <div style={styles.mlArrow}>↓ {(ex.confidence * 100).toFixed(0)}% confidence</div>
              <code style={styles.mlField}>{ex.target_field}</code>
              <div style={styles.mlMethod}>{ex.method}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Schema Drift */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Schema Drift Detection</div>
        <p style={styles.sectionDesc}>
          When a connected system changes its schema without notice, ISG detects the drift
          and quarantines the affected contract until revalidation.
        </p>
        <div style={styles.driftPanel}>
          <div style={styles.driftStatus}>
            Status:{' '}
            <span style={{ color: driftStatus?.drift_detected ? '#f87171' : '#4ade80', fontWeight: 700 }}>
              {driftStatus?.drift_detected ? 'DRIFT DETECTED' : 'STABLE'}
            </span>
          </div>

          {driftStatus?.drift_detected && (
            <div style={styles.driftDetails}>
              <div style={styles.driftSystem}>System: {driftStatus.system} — {driftStatus.old_version} → {driftStatus.new_version}</div>
              <div style={styles.driftContractStatus}>{driftStatus.contract_status}</div>
              <div style={styles.driftAction}>{driftStatus.isg_action}</div>
              {driftStatus.changes?.map((c: any, i: number) => (
                <div key={i} style={styles.changeRow}>
                  <span style={{ ...styles.badge, background: '#7c2d12' }}>{c.type}</span>
                  <span style={styles.changeDetail}>
                    {c.old_field} → {c.new_field || c.new_fields?.join(', ')}
                  </span>
                  <span style={{ ...styles.badge, background: c.impact === 'HIGH' ? '#7f1d1d' : '#374151' }}>
                    {c.impact}
                  </span>
                  <span style={styles.changeContracts}>Affects: {c.affected_contracts.join(', ')}</span>
                </div>
              ))}
            </div>
          )}

          <button style={{
            ...styles.driftBtn,
            background: driftStatus?.drift_detected ? '#1e3a5f' : '#7f1d1d',
          }} onClick={toggleDrift} disabled={driftLoading}>
            {driftLoading ? 'Working…' : driftStatus?.drift_detected ? 'Reset (Restore C-017)' : 'Simulate Schema Drift in REV-001'}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '0 0 32px' },
  title: { fontSize: 20, fontWeight: 700, color: '#f9fafb', margin: '0 0 8px' },
  subtitle: { color: '#9ca3af', margin: '0 0 16px', fontSize: 14, lineHeight: 1.6 },
  invariantBanner: {
    background: '#1c1917', border: '1px solid #f87171', borderRadius: 8,
    padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'flex-start',
    color: '#fca5a5', fontSize: 13, marginBottom: 24, lineHeight: 1.5,
  },
  invariantIcon: { fontSize: 18, flexShrink: 0 },
  section: { background: '#1f2937', borderRadius: 8, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 700, color: '#93c5fd', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  sectionDesc: { color: '#9ca3af', fontSize: 13, margin: '0 0 12px', lineHeight: 1.5 },
  controls: { display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 440 },
  label: { fontSize: 12, color: '#9ca3af', fontWeight: 600 },
  segmented: { display: 'flex', gap: 0, borderRadius: 6, overflow: 'hidden', border: '1px solid #374151' },
  seg: { flex: 1, padding: '8px 0', background: '#111827', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 13 },
  segActive: { background: '#3b82f6', color: '#fff', fontWeight: 700 },
  input: { background: '#111827', border: '1px solid #374151', borderRadius: 6, padding: '8px 12px', color: '#f9fafb', fontSize: 14 },
  runBtn: {
    background: '#3b82f6', border: 'none', borderRadius: 6, padding: '10px 16px',
    color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 13,
  },
  result: { marginTop: 20 },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  panel: { background: '#111827', borderRadius: 8, padding: 16, border: '1px solid #374151' },
  panelTitle: { fontSize: 13, fontWeight: 700, color: '#f9fafb', marginBottom: 8 },
  panelConfidence: { fontSize: 12, color: '#9ca3af', marginBottom: 6 },
  transformBox: { background: '#374151', borderRadius: 4, padding: '8px 10px', fontFamily: 'monospace', fontSize: 12, color: '#93c5fd', marginBottom: 8 },
  reasoning: { fontSize: 12, color: '#9ca3af', lineHeight: 1.5, marginBottom: 10 },
  authTag: { display: 'inline-block', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 12 },
  verdict: { fontSize: 20, fontWeight: 900, marginBottom: 6 },
  checksTitle: { fontSize: 11, color: '#6b7280', textTransform: 'uppercase', marginBottom: 6 },
  checkRow: { display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 4 },
  checkResult: { fontSize: 10, fontWeight: 700, minWidth: 50 },
  checkName: { fontSize: 12, color: '#d1d5db', flex: 1 },
  checkNote: { fontSize: 11, color: '#6b7280' },
  mlGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 },
  mlCard: { background: '#111827', borderRadius: 6, padding: 12 },
  mlLang: { fontSize: 10, color: '#9ca3af', marginBottom: 4 },
  mlText: { fontSize: 16, color: '#f9fafb', marginBottom: 4 },
  mlArrow: { fontSize: 11, color: '#60a5fa', marginBottom: 4 },
  mlField: { background: '#374151', padding: '1px 5px', borderRadius: 3, fontFamily: 'monospace', fontSize: 12, color: '#93c5fd' },
  mlMethod: { fontSize: 10, color: '#6b7280', marginTop: 4 },
  driftPanel: { background: '#111827', borderRadius: 8, padding: 16 },
  driftStatus: { fontSize: 14, color: '#e5e7eb', marginBottom: 12 },
  driftDetails: { marginBottom: 16 },
  driftSystem: { fontSize: 13, color: '#fbbf24', marginBottom: 4 },
  driftContractStatus: { fontSize: 12, color: '#f87171', marginBottom: 4 },
  driftAction: { fontSize: 12, color: '#9ca3af', marginBottom: 10 },
  changeRow: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' },
  badge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, color: '#fff' },
  changeDetail: { fontSize: 12, fontFamily: 'monospace', color: '#e5e7eb' },
  changeContracts: { fontSize: 11, color: '#9ca3af' },
  driftBtn: { border: 'none', borderRadius: 6, padding: '8px 14px', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 13 },
};
