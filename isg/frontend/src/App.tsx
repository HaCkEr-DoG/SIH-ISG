import React, { useEffect, useState, useCallback } from 'react';
import { listTransactions, getDecisionCapsule } from './api/isg';
import type { Transaction, DecisionCapsule } from './api/isg';

const STATUS_STYLE: Record<string, { bg: string; text: string; border: string; label: string }> = {
  SUCCESS:      { bg: 'bg-[#e8f5e9]',  text: 'text-[#1b5e20]', border: 'border-[#138808]', label: 'COMPLETED' },
  QUARANTINED:  { bg: 'bg-[#fff3e0]',  text: 'text-[#e65100]', border: 'border-[#FF9933]', label: 'REVIEW' },
  REJECTED:     { bg: 'bg-[#ffebee]',  text: 'text-[#b71c1c]', border: 'border-[#e53935]', label: 'BLOCKED' },
  FAILED:       { bg: 'bg-[#f5f5f5]',  text: 'text-[#757575]', border: 'border-[#e5e5e5]', label: 'UNKNOWN' },
  PENDING:      { bg: 'bg-[#fff8ed]',  text: 'text-[#c65c00]', border: 'border-[#FFB566]', label: 'PENDING' },
  COMPENSATED:  { bg: 'bg-[#fafafa]',  text: 'text-[#525252]', border: 'border-[#e5e5e5]', label: 'COMPENSATED' },
  CANCELLED:    { bg: 'bg-[#f5f5f5]',  text: 'text-[#757575]', border: 'border-[#e5e5e5]', label: 'CANCELLED' },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.FAILED;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase border ${s.bg} ${s.text} ${s.border}`}>
      {s.label}
    </span>
  );
}

function DonutChart({ txns }: { txns: Transaction[] }) {
  const total = txns.length;
  if (total === 0) return <div className="h-36 flex items-center justify-center text-slate-400 font-mono text-sm">No data</div>;

  const counts = {
    completed: txns.filter(t => t.status === 'SUCCESS').length,
    review:    txns.filter(t => t.status === 'QUARANTINED').length,
    pending:   txns.filter(t => t.status === 'PENDING').length,
    blocked:   txns.filter(t => t.status === 'REJECTED').length,
    unknown:   txns.filter(t => ['FAILED','COMPENSATED','CANCELLED','EXPIRED'].includes(t.status)).length,
  };

  const r = 38;
  const circ = 2 * Math.PI * r;
  const slices = [
    { count: counts.completed, color: '#FF9933' },
    { count: counts.pending,   color: '#FFB566' },
    { count: counts.review,    color: '#ffd4a0' },
    { count: counts.blocked,   color: '#e53935' },
    { count: counts.unknown,   color: '#d4d4d4' },
  ];

  let offset = 0;
  const paths = slices.map((s, i) => {
    const dash = (s.count / total) * circ;
    const el = (
      <circle key={i} cx="50" cy="50" r={r} fill="transparent" stroke={s.color} strokeWidth="16"
        strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={-offset}
        style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }} />
    );
    offset += dash;
    return el;
  });

  return (
    <div className="flex items-center gap-6 py-2">
      <div className="relative w-36 h-36 flex-shrink-0">
        <svg viewBox="0 0 100 100" className="w-full h-full">
          <circle cx="50" cy="50" r={r} fill="transparent" stroke="#e5e5e5" strokeWidth="16" />
          {paths}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold text-slate-900 font-serif leading-none">{total}</span>
          <span className="text-[10px] text-slate-500 uppercase font-bold font-mono mt-0.5">TOTAL</span>
        </div>
      </div>
      <div className="space-y-1.5 flex-1 text-xs">
        {[
          { label: 'Completed', color: '#FF9933', count: counts.completed },
          { label: 'Pending',   color: '#FFB566', count: counts.pending },
          { label: 'Review',    color: '#ffd4a0', count: counts.review },
          { label: 'Blocked',   color: '#e53935', count: counts.blocked },
          { label: 'Unknown',   color: '#d4d4d4', count: counts.unknown },
        ].map(item => (
          <div key={item.label} className="flex items-center justify-between py-1 border-b border-[#e5e5e5] last:border-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="w-2.5 h-2.5 rounded flex-shrink-0" style={{ background: item.color }} />
              <span className="text-slate-800 font-medium truncate">{item.label}</span>
            </div>
            <span className="font-mono text-slate-900 font-bold whitespace-nowrap ml-1.5 flex-shrink-0">
              {item.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InspectorDrawer({ txnId, onClose }: { txnId: string | null; onClose: () => void }) {
  const [capsule, setCapsule] = useState<DecisionCapsule | null>(null);
  const [loading, setLoading] = useState(false);
  const [remediationChoice, setRemediationChoice] = useState('transform');

  useEffect(() => {
    if (!txnId) return;
    setCapsule(null);
    setLoading(true);
    getDecisionCapsule(txnId).then(r => {
      setCapsule(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [txnId]);

  if (!txnId) return null;
  const stateStyle = capsule ? (STATUS_STYLE[capsule.final_state] || STATUS_STYLE.FAILED) : null;

  return (
    <>
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-slate-50 border-l border-slate-200 shadow-2xl flex flex-col z-50">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-white flex-shrink-0">
          <div className="flex items-center gap-3">
            {capsule && stateStyle ? (
              <span className={`px-2.5 py-1 text-xs font-bold font-mono tracking-wider rounded border ${stateStyle.bg} ${stateStyle.text} ${stateStyle.border}`}>
                {capsule.final_state === 'QUARANTINED' ? 'REVIEW REQUIRED' : stateStyle.label}
              </span>
            ) : (
              <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-bold font-mono rounded border border-blue-200">LOADING</span>
            )}
            <div>
              <h4 className="text-base font-bold text-slate-900 font-serif">{txnId}</h4>
              {capsule && (
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  {capsule.applicant_name} · {new Date(capsule.submitted_at).toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
          <button className="p-1.5 border border-[#e5e5e5] rounded bg-[#f5f5f5] text-[#555555] hover:bg-[#e5e5e5] transition" onClick={onClose}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading ? (
            <div className="flex items-center justify-center h-40 text-slate-400 font-mono text-sm">Loading transaction…</div>
          ) : capsule ? (
            <>
              {(capsule.final_state === 'QUARANTINED' || capsule.safety_decision === 'QUARANTINE') && (
                <div className="p-4 bg-white border border-red-200 rounded shadow-sm flex items-start gap-3">
                  <div className="p-1.5 bg-red-50 text-red-600 rounded border border-red-200 flex-shrink-0">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-red-700 font-serif mb-1">Issue Flagged</div>
                    <p className="text-xs text-slate-700 leading-relaxed">{capsule.quarantine_reason || 'This transaction was flagged and paused. A human operator must review it.'}</p>
                  </div>
                </div>
              )}

              {/* Cryptographic evidence */}
              <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-[#161616] text-[#f4f4f4] text-xs font-bold font-mono uppercase tracking-wider flex justify-between">
                  <span>Security Record</span>
                  <span className="text-blue-300">STATE v{capsule.state_version}</span>
                </div>
                <div className="p-4">
                  <div className="p-3 bg-[#161616] rounded font-mono text-[#f4f4f4] text-[11px] space-y-1.5">
                    <div><span className="text-slate-400">FINAL_STATE    :</span> <span className="font-bold">{capsule.final_state}</span></div>
                    <div><span className="text-slate-400">SAFETY_DECISION:</span> <span className="font-bold">{capsule.safety_decision}</span></div>
                    <div><span className="text-slate-400">EFFECT_AUTH    :</span> <span className={capsule.effect_authorized ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{capsule.effect_authorized ? 'TRUE' : 'FALSE'}</span></div>
                    <div><span className="text-slate-400">EFFECT_OBS     :</span> <span className={capsule.effect_observed ? 'text-emerald-400 font-bold' : 'text-slate-500'}>{capsule.effect_observed ? 'TRUE' : 'FALSE'}</span></div>
                    {capsule.audit_trail[0] && (
                      <div><span className="text-slate-400">PAYLOAD_HASH   :</span> <span className="text-blue-300 text-[10px]">{capsule.audit_trail[0].payload_hash.slice(0, 48)}…</span></div>
                    )}
                  </div>
                </div>
              </div>

              {/* Audit trail */}
              <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
                <div className="px-4 py-2.5 bg-[#161616] text-[#f4f4f4] text-xs font-bold font-mono uppercase tracking-wider">
                  Audit Trail — {capsule.audit_trail.length} Events
                </div>
                <div className="divide-y divide-slate-100 max-h-56 overflow-y-auto">
                  {capsule.audit_trail.slice(0, 12).map(ev => (
                    <div key={ev.sequence} className="flex items-start gap-3 px-4 py-2.5 text-xs hover:bg-slate-50 transition">
                      <span className="font-mono text-slate-400 min-w-[20px]">{ev.sequence}</span>
                      <span className="font-mono text-[#1a237e] min-w-[140px] text-[11px]">{ev.stage}</span>
                      <span className={`font-bold min-w-[70px] text-[11px] font-mono ${
                        ev.result === 'PASS' || ev.result === 'SUCCESS' ? 'text-emerald-600' :
                        ev.result === 'QUARANTINED' || ev.result === 'FAIL' ? 'text-red-600' : 'text-amber-600'
                      }`}>{ev.result}</span>
                      <span className="text-slate-500 leading-tight">{ev.detail}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Remediation — only for QUARANTINED */}
              {capsule.final_state === 'QUARANTINED' && (
                <div className="space-y-2">
                  <div className="text-slate-800 font-bold uppercase text-[11px] tracking-wider font-mono">Operator Remediation Action</div>
                  <div className="space-y-2">
                    {[
                      { id: 'transform', title: 'Approve & Forward',         desc: 'Convert the data to the required format and send it to the destination. A tamper-proof receipt is generated.', recommended: true },
                      { id: 'request',   title: 'Ask Citizen to Resubmit',  desc: 'Send the citizen a notification via DigiLocker or SMS asking them to provide updated documents.', recommended: false },
                      { id: 'reject',    title: 'Reject & Block',           desc: 'Mark this transaction as failed and alert the source system that it cannot proceed.', recommended: false },
                    ].map(opt => (
                      <label key={opt.id} className={`flex items-start justify-between p-3.5 bg-white rounded cursor-pointer transition ${remediationChoice === opt.id ? 'border-2 border-blue-600 shadow-sm' : 'border border-slate-200 hover:bg-slate-50'}`}>
                        <div className="flex items-start gap-3">
                          <input type="radio" name="remediation" value={opt.id} checked={remediationChoice === opt.id} onChange={() => setRemediationChoice(opt.id)} className="mt-0.5 text-[#1a237e] border-slate-300 focus:ring-blue-600" />
                          <div>
                            <div className={`text-xs font-bold font-serif ${opt.id === 'reject' ? 'text-red-700' : 'text-slate-900'}`}>{opt.title}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5">{opt.desc}</div>
                          </div>
                        </div>
                        {opt.recommended && <span className="ml-2 text-[10px] font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 flex-shrink-0">RECOMMENDED</span>}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-40 text-slate-400 font-mono text-sm">Could not load transaction details.</div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
          <button className="px-4 py-2 text-xs font-bold font-mono uppercase text-slate-700 bg-slate-100 hover:bg-slate-200 transition border border-slate-200 rounded" onClick={onClose}>CLOSE</button>
          {capsule?.final_state === 'QUARANTINED' && (
            <button
              className="px-4 py-2 text-xs font-bold font-mono uppercase bg-[#FF9933] hover:bg-[#e6880a] text-[#111111] transition flex items-center gap-2 rounded shadow-sm"
              onClick={() => { alert(`Safety action '${remediationChoice}' applied for ${txnId}. Audit ledger updated.`); onClose(); }}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /></svg>
              CONFIRM & SEND
            </button>
          )}
        </div>
      </div>
    </>
  );
}

type NavItem = 'overview' | 'transactions' | 'systems' | 'review' | 'reconciliation' | 'audit' | 'settings';

export default function App() {
  const [activeNav, setActiveNav] = useState<NavItem>('overview');
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const load = useCallback(async () => {
    try {
      const r = await listTransactions();
      setTxns(r.data);
      setLastRefresh(new Date());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const reviewCount  = txns.filter(t => t.status === 'QUARANTINED').length;
  const blockedCount = txns.filter(t => t.status === 'REJECTED').length;
  const unknownCount = txns.filter(t => ['FAILED','COMPENSATED','EXPIRED','CANCELLED'].includes(t.status)).length;

  const filtered = txns.filter(t => {
    const q = search.toLowerCase();
    return (!search || t.transaction_id.toLowerCase().includes(q) || t.applicant_name.toLowerCase().includes(q))
      && (!statusFilter || t.status === statusFilter);
  });

  const attentionTxns = txns.filter(t => ['QUARANTINED','REJECTED','FAILED'].includes(t.status)).slice(0, 5);

  return (
    <div className="h-screen flex overflow-hidden bg-slate-50 font-sans">

      {/* ── Sidebar ── */}
      <aside className="w-60 flex-shrink-0 bg-[#111111] border-r border-[#222222] flex flex-col select-none z-10">
        <div className="flex-1 flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-[#222222] flex items-center gap-3">
            <div className="w-7 h-7 bg-[#FF9933] rounded flex items-center justify-center text-[#111111] flex-shrink-0">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold text-white leading-none">ISG</div>
              <div className="text-[11px] text-[#888888] leading-tight mt-1">Interoperability Gateway</div>
            </div>
          </div>
          <nav className="p-3 space-y-1 flex-1 text-xs">
            {([
              { id: 'overview',       label: 'Overview',       badge: null },
              { id: 'transactions',   label: 'Transactions',   badge: null },
              { id: 'systems',        label: 'Systems',        badge: null },
              { id: 'review',         label: 'Review Queue',   badge: reviewCount  > 0 ? String(reviewCount)  : null },
              { id: 'reconciliation', label: 'Reconciliation', badge: unknownCount > 0 ? String(unknownCount) : null },
              { id: 'audit',          label: 'Audit',          badge: null },
              { id: 'settings',       label: 'Settings',       badge: null },
            ] as { id: NavItem; label: string; badge: string | null }[]).map(item => (
              <button
                key={item.id}
                onClick={() => setActiveNav(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded font-medium transition text-left ${activeNav === item.id ? 'bg-[#FF9933] text-[#111111] border-l-2 border-[#FF9933] font-semibold' : 'text-[#888888] hover:bg-[#222222] hover:text-[#ffffff]'}`}
              >
                <span>{item.label}</span>
                {item.badge && <span className="text-[11px] font-mono bg-[#222222] text-[#888888] px-1.5 py-0.5 rounded border border-[#333333] font-medium">{item.badge}</span>}
              </button>
            ))}
          </nav>
        </div>
        <div className="p-3 border-t border-[#222222]">
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-8 h-8 rounded-full bg-[#222222] border border-[#333333] text-[#888888] flex items-center justify-center font-semibold text-xs font-mono flex-shrink-0">TB</div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-white truncate">Tharun B S</div>
              <div className="text-[11px] text-[#888888] truncate mt-0.5">System Operator</div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">

        {/* Header */}
        <header className="h-16 border-b border-slate-200 flex items-center justify-between px-6 bg-white flex-shrink-0 shadow-sm">
          <span className="text-xs font-mono font-medium text-slate-500">Monitor interoperability transactions and system health</span>
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-slate-400">{lastRefresh.toLocaleTimeString()}</span>
            <button onClick={load} className="p-2 text-slate-500 bg-white border border-slate-200 rounded hover:bg-slate-50 hover:text-[#1a237e] transition shadow-sm" title="Refresh">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
            </button>
            <div className="relative">
              <button className="p-2 text-slate-500 bg-white border border-slate-200 rounded hover:bg-slate-50 transition shadow-sm">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </button>
              {(reviewCount + blockedCount) > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-bold font-mono">{reviewCount + blockedCount}</span>
              )}
            </div>
          </div>
        </header>

        {/* Dashboard content */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* ── Review Queue view ── */}
          {activeNav === 'review' && (
            <section className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900 font-serif">Review Queue</h2>
                <span className="text-xs font-mono font-bold bg-blue-50 text-blue-700 px-3 py-1 rounded border border-blue-200">{txns.filter(t => t.status === 'QUARANTINED').length} REQUIRING ATTENTION</span>
              </div>
              <div className="bg-white border border-slate-200 rounded shadow-sm p-5 space-y-4">
                <p className="text-xs text-slate-500 font-mono border-l-4 border-amber-400 pl-3">These transactions are paused for human review. Once a decision is made, it cannot be changed.</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">Transaction ID</th>
                      <th className="pb-2 font-bold text-left">Applicant</th>
                      <th className="pb-2 font-bold text-left">Quarantine Reason</th>
                      <th className="pb-2 font-bold text-left">State v</th>
                      <th className="pb-2 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr><td colSpan={5} className="py-8 text-center text-slate-400 font-mono text-sm">Loading…</td></tr>
                    ) : txns.filter(t => t.status === 'QUARANTINED').length === 0 ? (
                      <tr><td colSpan={5} className="py-8 text-center text-emerald-600 font-mono text-sm">✓ No transactions in review queue</td></tr>
                    ) : txns.filter(t => t.status === 'QUARANTINED').map(t => (
                      <tr key={t.transaction_id} className="hover:bg-slate-50 transition cursor-pointer" onClick={() => setSelectedTxnId(t.transaction_id)}>
                        <td className="py-3 text-[#1a237e] font-mono font-bold hover:underline">{t.transaction_id}</td>
                        <td className="py-3 text-slate-800 font-medium">{t.applicant_name}</td>
                        <td className="py-3 text-slate-500 text-[11px] max-w-xs truncate">{t.quarantine_reason || '—'}</td>
                        <td className="py-3 text-slate-600 font-mono">{t.state_version}</td>
                        <td className="py-3 text-right"><button className="px-3 py-1 bg-[#FF9933] text-[#111111] text-xs font-bold font-mono rounded hover:bg-[#e6880a] transition shadow-sm" onClick={e=>{e.stopPropagation();setSelectedTxnId(t.transaction_id);}}>REVIEW</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Transactions view ── */}
          {activeNav === 'transactions' && (
            <section className="space-y-4">
              <h2 className="text-xl font-bold text-slate-900 font-serif">All Transactions</h2>
              <div className="bg-white border border-slate-200 rounded shadow-sm p-5 space-y-4">
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="relative">
                    <input type="text" placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)}
                      className="w-48 pl-8 pr-3 py-1.5 bg-white border border-[#e5e5e5] rounded text-xs text-[#111111] placeholder-[#aaaaaa] focus:bg-white focus:border-[#FF9933] focus:ring-1 focus:ring-[#FF9933] font-mono" />
                    <svg className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /></svg>
                  </div>
                  <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                    className="bg-white border border-[#e5e5e5] rounded text-xs text-[#111111] py-1.5 pl-2.5 pr-8 focus:ring-[#FF9933] focus:border-[#FF9933] font-mono font-semibold">
                    <option value="">All States</option>
                    <option value="SUCCESS">Completed</option>
                    <option value="QUARANTINED">Review</option>
                    <option value="PENDING">Pending</option>
                    <option value="REJECTED">Blocked</option>
                    <option value="FAILED">Unknown</option>
                  </select>
                  <span className="text-xs font-mono text-slate-500 ml-auto">{filtered.length} of {txns.length}</span>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">Transaction ID</th>
                      <th className="pb-2 font-bold text-left">Applicant</th>
                      <th className="pb-2 font-bold text-left">State</th>
                      <th className="pb-2 font-bold text-left">Safety</th>
                      <th className="pb-2 font-bold text-center">Auth</th>
                      <th className="pb-2 font-bold text-center">Obs</th>
                      <th className="pb-2 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr><td colSpan={7} className="py-8 text-center text-slate-400 font-mono">Loading…</td></tr>
                    ) : filtered.length === 0 ? (
                      <tr><td colSpan={7} className="py-8 text-center text-slate-400 font-mono">No transactions found.</td></tr>
                    ) : filtered.map(t => (
                      <tr key={t.transaction_id} className={`hover:bg-slate-50 transition cursor-pointer ${selectedTxnId === t.transaction_id ? 'bg-blue-50/40' : ''}`} onClick={() => setSelectedTxnId(t.transaction_id)}>
                        <td className="py-2.5 text-[#1a237e] font-mono font-bold">{t.transaction_id}</td>
                        <td className="py-2.5 text-slate-800 font-medium">{t.applicant_name}</td>
                        <td className="py-2.5"><StatusBadge status={t.status} /></td>
                        <td className="py-2.5"><span className={`font-mono text-[11px] font-bold ${t.safety_decision === 'QUARANTINE' ? 'text-amber-600' : t.safety_decision === 'PASS' ? 'text-emerald-600' : 'text-slate-300'}`}>{t.safety_decision || '—'}</span></td>
                        <td className="py-2.5 text-center"><span className={t.effect_authorized ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_authorized ? '✓' : '—'}</span></td>
                        <td className="py-2.5 text-center"><span className={t.effect_observed ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_observed ? '✓' : '—'}</span></td>
                        <td className="py-2.5 text-right"><button className="px-2.5 py-1 bg-white border border-slate-200 text-slate-800 rounded font-bold hover:bg-slate-50 shadow-sm transition uppercase font-mono text-xs" onClick={e=>{e.stopPropagation();setSelectedTxnId(t.transaction_id);}}>VIEW</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Systems view ── */}
          {activeNav === 'systems' && (
            <section className="space-y-6">
              <h2 className="text-xl font-bold text-slate-900 font-serif">System Connectivity</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { id: 'REV-001', name: 'Income Tax Department',  color: '#3366cc', owner: 'Ministry of Finance / CBDT', schema: 'v2.4', caps: ['income_fetch','income_verify','annual_certificate'] },
                  { id: 'EDU-001', name: 'Education Department',  color: '#0891b2', owner: 'UGC / Academic Bank of Credits', schema: 'v1.8', caps: ['enrollment_verify','marks_fetch','institution_verify'] },
                  { id: 'IDN-001', name: 'Identity Registry',     color: '#7c3aed', owner: 'NIC / Aadhaar Authority',         schema: 'v3.1', caps: ['identity_verify','dob_fetch','name_match'] },
                  { id: 'SCH-001', name: 'Scholarship & Welfare', color: '#059669', owner: 'Dept. of Social Welfare',         schema: 'v1.2', caps: ['eligibility_check','disbursement_auth','status_update'] },
                ].map(sys => (
                  <div key={sys.id} className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full" style={{ background: sys.color }} />
                      <div>
                        <div className="text-xs font-mono font-bold text-slate-500">{sys.id}</div>
                        <div className="text-sm font-bold text-slate-900 font-serif">{sys.name}</div>
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-500">{sys.owner}</div>
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 text-emerald-700 font-bold text-[10px] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono uppercase">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> ONLINE
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">Schema {sys.schema}</span>
                    </div>
                    <div className="border-t border-slate-100 pt-3">
                      <div className="text-[10px] font-mono font-bold text-slate-400 uppercase mb-1.5">Capabilities</div>
                      <div className="flex flex-wrap gap-1">
                        {sys.caps.map(c => <span key={c} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">{c}</span>)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Reconciliation view ── */}
          {activeNav === 'reconciliation' && (
            <section className="space-y-6">
              <h2 className="text-xl font-bold text-slate-900 font-serif">Reconciliation</h2>
              <div className="bg-white border border-slate-200 rounded shadow-sm p-5 space-y-4">
                <p className="text-xs text-slate-500 font-mono border-l-4 border-slate-300 pl-3">These transactions have outcomes that could not be confirmed. They need manual follow-up.</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">Transaction ID</th>
                      <th className="pb-2 font-bold text-left">Applicant</th>
                      <th className="pb-2 font-bold text-left">State</th>
                      <th className="pb-2 font-bold text-center">Auth</th>
                      <th className="pb-2 font-bold text-center">Observed</th>
                      <th className="pb-2 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr><td colSpan={6} className="py-8 text-center text-slate-400 font-mono">Loading…</td></tr>
                    ) : txns.filter(t => ['FAILED','COMPENSATED','EXPIRED','CANCELLED'].includes(t.status)).length === 0 ? (
                      <tr><td colSpan={6} className="py-8 text-center text-emerald-600 font-mono">✓ No transactions pending reconciliation</td></tr>
                    ) : txns.filter(t => ['FAILED','COMPENSATED','EXPIRED','CANCELLED'].includes(t.status)).map(t => (
                      <tr key={t.transaction_id} className="hover:bg-slate-50 transition cursor-pointer" onClick={() => setSelectedTxnId(t.transaction_id)}>
                        <td className="py-2.5 text-[#1a237e] font-mono font-bold">{t.transaction_id}</td>
                        <td className="py-2.5 text-slate-800 font-medium">{t.applicant_name}</td>
                        <td className="py-2.5"><StatusBadge status={t.status} /></td>
                        <td className="py-2.5 text-center"><span className={t.effect_authorized ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_authorized ? '✓' : '—'}</span></td>
                        <td className="py-2.5 text-center"><span className={t.effect_observed ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_observed ? '✓' : '—'}</span></td>
                        <td className="py-2.5 text-right"><button className="px-3 py-1 bg-white border border-slate-200 text-slate-800 rounded font-bold hover:bg-slate-50 shadow-sm transition uppercase font-mono text-xs" onClick={e=>{e.stopPropagation();setSelectedTxnId(t.transaction_id);}}>VIEW</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Audit view ── */}
          {activeNav === 'audit' && (
            <section className="space-y-6">
              <h2 className="text-xl font-bold text-slate-900 font-serif">Audit Log</h2>
              <div className="bg-white border border-slate-200 rounded shadow-sm p-5 space-y-3">
                <p className="text-xs text-slate-500 font-mono border-l-4 border-slate-800 pl-3">A permanent record of all transactions. Click any row to view its full audit trail.</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">Transaction ID</th>
                      <th className="pb-2 font-bold text-left">Applicant</th>
                      <th className="pb-2 font-bold text-left">Final State</th>
                      <th className="pb-2 font-bold text-left">Safety Decision</th>
                      <th className="pb-2 font-bold text-left">State v</th>
                      <th className="pb-2 font-bold text-right">Record</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr><td colSpan={6} className="py-8 text-center text-slate-400 font-mono">Loading…</td></tr>
                    ) : txns.map(t => (
                      <tr key={t.transaction_id} className="hover:bg-slate-50 transition cursor-pointer" onClick={() => setSelectedTxnId(t.transaction_id)}>
                        <td className="py-2.5 text-[#1a237e] font-mono font-bold text-[11px]">{t.transaction_id}</td>
                        <td className="py-2.5 text-slate-800 font-medium">{t.applicant_name}</td>
                        <td className="py-2.5"><StatusBadge status={t.status} /></td>
                        <td className="py-2.5"><span className={`font-mono text-[11px] font-bold ${t.safety_decision === 'QUARANTINE' ? 'text-amber-600' : t.safety_decision === 'PASS' ? 'text-emerald-600' : 'text-slate-300'}`}>{t.safety_decision || '—'}</span></td>
                        <td className="py-2.5 font-mono text-slate-600">{t.state_version}</td>
                        <td className="py-2.5 text-right"><button className="px-2.5 py-1 bg-[#f5f5f5] text-[#111111] border border-[#e5e5e5] rounded font-bold hover:bg-[#e5e5e5] shadow-sm transition uppercase font-mono text-[10px]" onClick={e=>{e.stopPropagation();setSelectedTxnId(t.transaction_id);}}>OPEN</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Settings view ── */}
          {activeNav === 'settings' && (
            <section className="space-y-6">
              <h2 className="text-xl font-bold text-slate-900 font-serif">Settings</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { label: 'Gateway Version', value: '2.0.0-prototype' },
                  { label: 'Safety Kernel', value: 'DETERMINISTIC v1 — ai_was_final_authority: ALWAYS FALSE' },
                  { label: 'Prototype Disclaimer', value: 'SIH 2026 PS26129 — NSP Eligibility Verification Demo' },
                  { label: 'Environment', value: 'SIMULATION — No real government systems connected' },
                ].map(item => (
                  <div key={item.label} className="bg-white border border-slate-200 rounded p-4 shadow-sm">
                    <div className="text-[10px] font-mono font-bold text-slate-400 uppercase mb-1">{item.label}</div>
                    <div className="text-sm text-slate-800 font-medium">{item.value}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Overview (default) ── */}
          {(activeNav === 'overview') && <>

          {/* Metric cards */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Transactions Requiring Review', value: reviewCount,  trend: '↓ 18%', trendCls: 'text-[#c65c00] bg-[#fff8ed] border-[#FFB566]' },
              { label: 'Unknown External Outcomes',     value: unknownCount, trend: '↓ 8%',  trendCls: 'text-slate-600 bg-slate-100 border-slate-200' },
              { label: 'Blocked Transactions',          value: blockedCount, trend: '↓ 13%', trendCls: 'text-red-700 bg-red-50 border-red-100' },
              { label: 'System Issues',                 value: 1,            trend: '↓ 67%', trendCls: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
            ].map(m => (
              <div key={m.label} className="bg-white border border-slate-200 rounded p-5 shadow-sm hover:border-[#FF9933] transition">
                <div className="text-[11px] text-slate-500 font-bold uppercase tracking-wider mb-2">{m.label}</div>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-3xl font-bold text-slate-900 font-serif">{loading ? '…' : m.value}</span>
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded border font-mono ${m.trendCls}`}>{m.trend}</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono uppercase">vs previous 7 days</div>
              </div>
            ))}
          </section>

          {/* Charts row */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">

            {/* Donut */}
            <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-serif">Transaction States</h3>
                <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded border border-slate-200">{txns.length} TOTAL</span>
              </div>
              {loading ? <div className="h-36 flex items-center justify-center text-slate-400 font-mono text-sm">Loading…</div> : <DonutChart txns={txns} />}
            </div>

            {/* Bar chart */}
            <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-serif">Source System Volume</h3>
              </div>
              <div className="relative h-44 flex items-end justify-between px-3 pt-6 pb-2 border-b border-slate-200 bg-slate-50 rounded">
                {[
                  { label: 'Revenue',       count: Math.max(txns.length, 4),    color: '#FF9933' },
                  { label: 'Identity & Edu',count: Math.max(Math.round(txns.length * 0.77), 3), color: '#FFB566' },
                  { label: 'Scholarship',   count: Math.max(Math.round(txns.length * 0.46), 2), color: '#ffd4a0' },
                  { label: 'Others',        count: 1,                            color: '#e5e5e5' },
                ].map((b, i) => {
                  const h = Math.min(Math.round((b.count / (txns.length + 4)) * 130), 120);
                  return (
                    <div key={i} className="flex flex-col items-center gap-1.5 z-10 w-1/4">
                      <span className="text-xs font-mono font-bold text-slate-900">{b.count}</span>
                      <div className="w-9 rounded-t shadow-sm" style={{ height: `${Math.max(h, 8)}px`, background: b.color }} />
                    </div>
                  );
                })}
              </div>
              <div className="grid grid-cols-4 text-center text-[10px] font-bold uppercase tracking-tight text-slate-500 pt-2 leading-tight">
                <span>Revenue</span><span>Id &amp; Edu</span><span>Scholar</span><span>Others</span>
              </div>
            </div>

            {/* System connectivity */}
            <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-5 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3 pb-3 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-serif">System Connectivity</h3>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">System</th>
                      <th className="pb-2 font-bold text-left">Status</th>
                      <th className="pb-2 font-bold text-right">Env</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {['Revenue Department','Identity & Education','Scholarship & Welfare'].map(sys => (
                      <tr key={sys}>
                        <td className="py-2.5 text-slate-900 font-semibold">{sys}</td>
                        <td className="py-2.5">
                          <span className="inline-flex items-center gap-1.5 text-emerald-700 font-bold text-[10px] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono uppercase">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> ONLINE
                          </span>
                        </td>
                        <td className="py-2.5 text-right text-slate-800 font-mono text-[11px] font-bold">SIM</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono">
                <span className="flex items-center gap-1.5 font-bold text-emerald-600 uppercase">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" /> 3 / 3 BRIDGES OK
                </span>
                <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200 font-bold">PING: 14MS</span>
              </div>
            </div>
          </section>

          {/* Attention + Activity */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">

            <div className="lg:col-span-7 bg-white border border-slate-200 rounded p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 uppercase tracking-wider font-serif">
                  Transactions Requiring Attention
                  {attentionTxns.length > 0 && (
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200 font-mono font-bold text-[10px]">{attentionTxns.length} PRIORITY</span>
                  )}
                </h3>
              </div>
              {loading ? (
                <div className="h-32 flex items-center justify-center text-slate-400 font-mono text-sm">Loading…</div>
              ) : attentionTxns.length === 0 ? (
                <div className="h-32 flex items-center justify-center text-emerald-600 font-mono text-sm">✓ No transactions requiring attention</div>
              ) : (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                      <th className="pb-2 font-bold text-left">Transaction ID</th>
                      <th className="pb-2 font-bold text-left">Reason</th>
                      <th className="pb-2 font-bold text-left">State</th>
                      <th className="pb-2 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {attentionTxns.map(t => (
                      <tr key={t.transaction_id} className="hover:bg-slate-50 transition cursor-pointer" onClick={() => setSelectedTxnId(t.transaction_id)}>
                        <td className="py-2.5 text-[#1a237e] font-mono font-bold hover:underline">{t.transaction_id}</td>
                        <td className="py-2.5 text-slate-500 text-[11px] max-w-[160px] truncate">{t.quarantine_reason || '—'}</td>
                        <td className="py-2.5"><StatusBadge status={t.status} /></td>
                        <td className="py-2.5 text-right">
                          <button className="px-2.5 py-1 text-xs bg-[#FF9933] font-bold text-[#111111] rounded hover:bg-[#e6880a] transition uppercase font-mono shadow-sm" onClick={e => { e.stopPropagation(); setSelectedTxnId(t.transaction_id); }}>VIEW</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="lg:col-span-5 bg-white border border-slate-200 rounded p-5 shadow-sm flex flex-col">
              <div className="mb-4 pb-3 border-b border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-serif">Recent Activity</h3>
              </div>
              <div className="flex-1 overflow-y-auto">
                {loading ? (
                  <div className="h-24 flex items-center justify-center text-slate-400 font-mono text-sm">Loading…</div>
                ) : (
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-slate-100">
                      {txns.slice(0, 8).map(t => (
                        <tr key={t.transaction_id} className="hover:bg-slate-50 transition cursor-pointer" onClick={() => setSelectedTxnId(t.transaction_id)}>
                          <td className="py-2 text-slate-500 font-mono text-[11px] min-w-[70px]">{new Date(t.created_at).toLocaleTimeString()}</td>
                          <td className="py-2 text-slate-800 font-medium">
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: t.status === 'SUCCESS' ? '#138808' : t.status === 'QUARANTINED' ? '#FF9933' : t.status === 'REJECTED' ? '#e53935' : '#aaaaaa' }} />
                              {t.status === 'SUCCESS' ? 'Transaction completed' : t.status === 'QUARANTINED' ? 'Moved to review queue' : t.status === 'REJECTED' ? 'Transaction blocked' : 'Transaction created'}
                            </span>
                          </td>
                          <td className="py-2 text-right font-mono text-[#1a237e] font-bold text-[11px]">{t.transaction_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono font-medium uppercase">
                <span className="flex items-center gap-1.5 text-slate-500"><span className="w-2 h-2 rounded-full bg-emerald-500" /> AUDIT LOG: LOCKED</span>
                <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200 text-slate-600">SYNC: 5S</span>
              </div>
            </div>
          </section>

          {/* Master transactions table */}
          <section className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-serif">All Transactions</h3>
                <span className="text-xs font-mono font-bold bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded border border-blue-200">{txns.length} TOTAL</span>
              </div>
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="relative">
                  <input type="text" placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)}
                    className="w-44 pl-8 pr-3 py-1.5 bg-white border border-[#e5e5e5] rounded text-xs text-[#111111] placeholder-[#aaaaaa] focus:bg-white focus:border-[#FF9933] focus:ring-1 focus:ring-[#FF9933] font-mono" />
                  <svg className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" /></svg>
                </div>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                  className="bg-white border border-[#e5e5e5] rounded text-xs text-[#111111] py-1.5 pl-2.5 pr-8 focus:ring-[#FF9933] focus:border-[#FF9933] font-mono font-semibold">
                  <option value="">All States</option>
                  <option value="SUCCESS">Completed</option>
                  <option value="QUARANTINED">Review</option>
                  <option value="PENDING">Pending</option>
                  <option value="REJECTED">Blocked</option>
                  <option value="FAILED">Unknown</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-200 font-mono uppercase text-[10px]">
                    <th className="pb-2 font-bold text-left">Transaction ID</th>
                    <th className="pb-2 font-bold text-left">Applicant</th>
                    <th className="pb-2 font-bold text-left">State</th>
                    <th className="pb-2 font-bold text-left">Safety Decision</th>
                    <th className="pb-2 font-bold text-center">Auth</th>
                    <th className="pb-2 font-bold text-center">Observed</th>
                    <th className="pb-2 font-bold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr><td colSpan={7} className="py-8 text-center text-slate-400 font-mono text-sm">Loading transactions…</td></tr>
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={7} className="py-8 text-center text-slate-400 font-mono text-sm">No transactions found.</td></tr>
                  ) : filtered.map(t => (
                    <tr key={t.transaction_id}
                      className={`hover:bg-slate-50 transition cursor-pointer ${selectedTxnId === t.transaction_id ? 'bg-blue-50/40' : ''}`}
                      onClick={() => setSelectedTxnId(t.transaction_id)}>
                      <td className="py-2.5 text-[#1a237e] font-mono font-bold hover:underline">{t.transaction_id}</td>
                      <td className="py-2.5 text-slate-800 font-medium">{t.applicant_name}</td>
                      <td className="py-2.5"><StatusBadge status={t.status} /></td>
                      <td className="py-2.5">
                        {t.safety_decision
                          ? <span className={`font-mono text-[11px] font-bold ${t.safety_decision === 'QUARANTINE' ? 'text-amber-600' : t.safety_decision === 'PASS' ? 'text-emerald-600' : 'text-slate-500'}`}>{t.safety_decision}</span>
                          : <span className="text-slate-300 font-mono">—</span>}
                      </td>
                      <td className="py-2.5 text-center"><span className={t.effect_authorized ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_authorized ? '✓' : '—'}</span></td>
                      <td className="py-2.5 text-center"><span className={t.effect_observed ? 'text-emerald-600 font-bold' : 'text-slate-300'}>{t.effect_observed ? '✓' : '—'}</span></td>
                      <td className="py-2.5 text-right">
                        <button className="px-2.5 py-1 text-xs bg-white border border-slate-200 text-slate-800 rounded font-bold hover:bg-slate-50 shadow-sm transition uppercase font-mono"
                          onClick={e => { e.stopPropagation(); setSelectedTxnId(t.transaction_id); }}>VIEW</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-xs text-slate-600">
              <div className="font-mono">Showing <span className="font-bold text-slate-900">{filtered.length}</span> of <span className="font-bold text-slate-900">{txns.length}</span> transactions</div>
            </div>
          </section>

          </>}

        </main>
      </div>

      <InspectorDrawer txnId={selectedTxnId} onClose={() => setSelectedTxnId(null)} />
    </div>
  );
}
