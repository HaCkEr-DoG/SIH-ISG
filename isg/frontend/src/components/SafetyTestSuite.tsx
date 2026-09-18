import React, { useEffect, useState } from 'react';
import { listSafetyTests, runSafetyTests } from '../api/isg';

interface SafetyTest {
  id: string;
  name: string;
  category: string;
  description: string;
  expected: string;
  status?: string;
}

interface RunResult {
  total: number;
  passed: number;
  failed: number;
  all_passed: boolean;
  results: SafetyTest[];
  summary: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  SEMANTIC: '#8b5cf6',
  IDENTITY: '#3b82f6',
  CONSENT: '#14b8a6',
  POLICY: '#f59e0b',
  AI_GOVERNANCE: '#ec4899',
  STATE_MACHINE: '#6b7280',
  AUTHORIZATION: '#10b981',
  IDEMPOTENCY: '#f97316',
  EFFECT: '#84cc16',
};

export default function SafetyTestSuite() {
  const [tests, setTests] = useState<SafetyTest[]>([]);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listSafetyTests().then(r => { setTests(r.data.tests); setLoading(false); });
  }, []);

  const run = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const r = await runSafetyTests();
      setRunResult(r.data);
    } finally {
      setRunning(false);
    }
  };

  const displayTests = runResult?.results || tests;

  if (loading) return <div style={styles.loading}>Loading safety tests…</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Safety Test Suite</h2>
          <p style={styles.subtitle}>
            These tests prove the safety properties of the ISG. Each test exercises a specific
            invariant that must hold for the gateway to be trustworthy in a production context.
          </p>
        </div>
        <button style={{ ...styles.runBtn, opacity: running ? 0.7 : 1 }} onClick={run} disabled={running}>
          {running ? (
            <><span style={styles.spinner}>⟳</span> Running…</>
          ) : (
            '▶ Run All Safety Tests'
          )}
        </button>
      </div>

      {runResult && (
        <div style={{
          ...styles.resultBanner,
          background: runResult.all_passed ? '#052e16' : '#450a0a',
          borderColor: runResult.all_passed ? '#4ade80' : '#f87171',
        }}>
          <span style={{ fontSize: 24, marginRight: 12 }}>
            {runResult.all_passed ? '✓' : '✗'}
          </span>
          <div>
            <div style={{ fontWeight: 700, color: runResult.all_passed ? '#4ade80' : '#f87171', fontSize: 16 }}>
              {runResult.all_passed ? 'ALL SAFETY INVARIANTS VERIFIED' : `${runResult.failed} TEST(S) FAILED`}
            </div>
            <div style={{ color: '#9ca3af', fontSize: 13 }}>{runResult.summary}</div>
          </div>
        </div>
      )}

      <div style={styles.testGrid}>
        {displayTests.map(t => {
          const color = CATEGORY_COLORS[t.category] || '#6b7280';
          const status = t.status;
          return (
            <div key={t.id} style={{
              ...styles.testCard,
              borderLeftColor: color,
              ...(status === 'FAIL' ? { background: '#1c0a0a' } : {}),
            }}>
              <div style={styles.testTop}>
                <span style={{ ...styles.testId, color }}>{t.id}</span>
                <span style={{ ...styles.catBadge, background: color + '33', color }}>
                  {t.category}
                </span>
                {status && (
                  <span style={{
                    ...styles.statusBadge,
                    background: status === 'PASS' ? '#052e16' : '#450a0a',
                    color: status === 'PASS' ? '#4ade80' : '#f87171',
                  }}>
                    {status === 'PASS' ? '✓ PASS' : '✗ FAIL'}
                  </span>
                )}
              </div>
              <div style={styles.testName}>{t.name}</div>
              <div style={styles.testDesc}>{t.description}</div>
              <div style={styles.expected}>
                Expected: <span style={{ color: '#fbbf24' }}>{t.expected}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: '0 0 32px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, gap: 16 },
  title: { fontSize: 20, fontWeight: 700, color: '#f9fafb', margin: '0 0 8px' },
  subtitle: { color: '#9ca3af', margin: 0, fontSize: 14, lineHeight: 1.6 },
  loading: { padding: 32, color: '#9ca3af', textAlign: 'center' },
  runBtn: {
    background: '#4f46e5', border: 'none', borderRadius: 8, padding: '12px 20px',
    color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 14, whiteSpace: 'nowrap',
    flexShrink: 0,
  },
  spinner: { display: 'inline-block', animation: 'spin 1s linear infinite' },
  resultBanner: {
    border: '1px solid', borderRadius: 8, padding: '16px 20px',
    display: 'flex', alignItems: 'center', marginBottom: 20,
  },
  testGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 },
  testCard: {
    background: '#1f2937', borderLeft: '3px solid', borderRadius: 8,
    padding: 14, transition: 'transform 0.1s',
  },
  testTop: { display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 },
  testId: { fontFamily: 'monospace', fontWeight: 700, fontSize: 12 },
  catBadge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4 },
  statusBadge: { fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, marginLeft: 'auto' },
  testName: { fontSize: 14, fontWeight: 600, color: '#f9fafb', marginBottom: 4 },
  testDesc: { fontSize: 12, color: '#9ca3af', lineHeight: 1.5, marginBottom: 6 },
  expected: { fontSize: 11, color: '#6b7280' },
};
