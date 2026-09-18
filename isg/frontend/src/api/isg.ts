import axios from 'axios';

const BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: BASE });

export type Scenario = 'VALID' | 'SEMANTIC_MISMATCH' | 'IDENTITY_MISMATCH' | 'CONSENT_FAILURE' | 'TIMEOUT' | 'RECOVERY' | 'REPLAY';

export interface Stage {
  stage: string;
  result: string;
  detail: string;
}

export interface ScenarioResult {
  scenario: string;
  transaction_id: string;
  status: string;
  decision: string;
  primary_reason: string;
  explanation: string;
  technical_code: string;
  stages: Stage[];
  replay_detected?: boolean;
}

export interface AuditEvent {
  sequence: number;
  stage: string;
  result: string;
  detail: string;
  evidence: Record<string, unknown>;
  payload_hash: string;
  recorded_at: string;
}

export interface DecisionCapsule {
  transaction_id: string;
  application_id: string;
  applicant_name: string;
  submitted_at: string;
  final_state: string;
  safety_decision: string;
  quarantine_reason: string | null;
  rejection_reason: string | null;
  effect_authorized: boolean;
  effect_observed: boolean;
  effect_verified: boolean;
  state_version: number;
  audit_trail: AuditEvent[];
  summary: Record<string, unknown>;
  prototype_disclaimer: string;
}

export interface Transaction {
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

export const runScenario = (scenario: Scenario) =>
  api.post<ScenarioResult>('/api/demo/run', { scenario });

export const resetDemo = () =>
  api.post('/api/demo/reset');

export const listApplications = () =>
  api.get('/api/demo/applications');

export const listTransactions = () =>
  api.get<Transaction[]>('/api/audit/transactions');

export const getDecisionCapsule = (txId: string) =>
  api.get<DecisionCapsule>(`/api/audit/capsule/${txId}`);

export const getTransactionAudit = (txId: string) =>
  api.get(`/api/audit/transaction/${txId}`);

// ── Governance ────────────────────────────────────────────────────────────────

export const listPassports = () => api.get('/api/governance/passports');
export const getPassport = (id: string) => api.get(`/api/governance/passports/${id}`);
export const listContracts = () => api.get('/api/governance/contracts');
export const getContract = (id: string) => api.get(`/api/governance/contracts/${id}`);

export const getAIMappingSuggestion = (req: {
  source_period: string;
  source_value: number;
  source_unit?: string;
  target_period?: string;
  period_reference?: string;
}) => api.post('/api/governance/ai/mapping-suggestion', req);

export const getMultilingualExamples = () =>
  api.get('/api/governance/ai/multilingual-examples');

export const simulateSchemaDrift = () =>
  api.post('/api/governance/schema-drift/simulate');
export const resetSchemaDrift = () =>
  api.post('/api/governance/schema-drift/reset');
export const getSchemaDriftStatus = () =>
  api.get('/api/governance/schema-drift/status');

// ── Safety Suite ──────────────────────────────────────────────────────────────

export const listSafetyTests = () => api.get('/api/safety/tests');
export const runSafetyTests = () => api.post('/api/safety/run-tests');
