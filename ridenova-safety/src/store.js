// Structured case records, human decisions, access log, retention and export.
// Persistence: browser localStorage in the prototype (per-device). Raw case data and PII are
// never persisted — only decisions and audit events keyed by case_id.

import { rank, ACTIONS, TIERS } from './policy.js';
import { ROLES } from './pii.js';

export const RETENTION_DAYS = { decisions: 365, audit: 400 };
const KEY = 'ridenova.v1';
const DAY = 864e5;

export const EXPORT_COLUMNS = ['case_id', 'predicted_tier', 'predicted_action', 'confidence', 'flags', 'rationale', 'human_decision', 'human_reason', 'decided_at',
  'final_tier', 'final_action', 'decided_by_role', 'lane', 'ai_mode', 'ai_tier', 'ai_action', 'policy_refs', 'region', 'country', 'language', 'submitted_utc', 'deadline_utc', 'parent_case',
  'l4_acknowledged_at', 'l4_reporter_contact', 'l4_emergency_services', 'l4_protective_action', 'l4_outcome'];

// L4 response: escalation already happened at intake, so the human's job is to act, not to re-triage.
// Steps are recorded in order with timestamps; the outcome closes the case.
export const L4_STEPS = {
  ack:       { label: 'Acknowledge alert', options: null },
  contact:   { label: 'Contact the reporter', options: { reached: 'Reached', no_answer: 'No answer — retrying', not_possible: 'No contact channel' } },
  emergency: { label: 'Emergency services', options: { contacted: 'Contacted', not_needed: 'Not needed', declined: 'Declined by reporter' } },
  protect:   { label: 'Protect the reporter', options: { account_suspended: 'Reported party suspended', rematch_blocked: 'Re-matching blocked', none_needed: 'None needed' } },
  outcome:   { label: 'Outcome', options: { safe_no_further_action: 'Reporter safe — no further action', action_taken: 'Safe — account action taken', referred_law_enforcement: 'Referred to law enforcement', transferred_investigations: 'Transferred to investigations' } },
};
const RESPONDERS = new Set(['specialist', 'duty']);

export class Store {
  constructor(storage = globalThis.localStorage, now = () => Date.now()) {
    this.storage = storage; this.now = now;
    this.state = { decisions: {}, audit: [], responses: {} };
    try { const raw = storage?.getItem(KEY); if (raw) this.state = { responses: {}, ...JSON.parse(raw) }; } catch { /* private mode etc. */ }
    this.purgeExpired();
  }
  save() { try { this.storage?.setItem(KEY, JSON.stringify(this.state)); } catch { /* quota/private */ } }

  log(role, event, case_id = null, detail = {}) {
    this.state.audit.push({ ts: new Date(this.now()).toISOString(), role, event, case_id, detail });
    this.save();
  }

  purgeExpired() {
    const t = this.now();
    const before = this.state.audit.length;
    this.state.audit = this.state.audit.filter((e) => t - Date.parse(e.ts) < RETENTION_DAYS.audit * DAY);
    for (const [id, d] of Object.entries(this.state.decisions)) if (t - Date.parse(d.decided_at) > RETENTION_DAYS.decisions * DAY) delete this.state.decisions[id];
    if (before !== this.state.audit.length) this.save();
  }

  // Validate and record a human decision. Returns { ok, error }.
  decide(record, { decision, tier, action, reason }, role) {
    const r = (reason || '').trim();
    if (!['approve', 'override', 'escalate'].includes(decision)) return { ok: false, error: 'Unknown decision.' };
    if (r.length < 8) return { ok: false, error: 'A reason (8+ characters) is required for every decision.' };
    if (role === 'auditor') return { ok: false, error: 'Auditors cannot decide cases.' };
    if (rank(record.predicted_tier) > rank(ROLES[role].maxTier)) return { ok: false, error: `${ROLES[role].label} cannot decide ${record.predicted_tier} cases — escalate to a specialist.` };
    let finalTier = record.predicted_tier, finalAction = record.predicted_action;
    if (decision === 'override') {
      if (!TIERS[tier] || !ACTIONS.includes(action)) return { ok: false, error: 'Choose a tier and an action.' };
      if (record.locked && rank(tier) < rank(record.predicted_tier) && role !== 'duty') return { ok: false, error: 'Only a duty manager can downgrade a danger-signal (SP-7) case.' };
      if (action === 'AUTO_RESOLVE_L1' && tier !== 'L1') return { ok: false, error: 'Only L1 cases can be resolved with AUTO_RESOLVE_L1.' };
      finalTier = tier; finalAction = action;
    }
    if (decision === 'escalate') {
      finalTier = rank(record.predicted_tier) >= 3 ? 'L4' : 'L3';
      finalAction = finalTier === 'L4' ? 'ESCALATE_L4_IMMEDIATE' : 'ROUTE_L3_REVIEW';
    }
    const d = { human_decision: decision, human_reason: r, final_tier: finalTier, final_action: finalAction, decided_by_role: role, decided_at: new Date(this.now()).toISOString() };
    this.state.decisions[record.case_id] = d;
    this.log(role, 'decision', record.case_id, { decision, from: `${record.predicted_tier}/${record.predicted_action}`, to: `${finalTier}/${finalAction}` });
    return { ok: true, decision: d };
  }

  // Record one L4 response step. Returns { ok, error }.
  respond(record, step, { value, reason } = {}, role) {
    if (!record.alert && record.predicted_tier !== 'L4') return { ok: false, error: 'The response checklist applies to L4 cases only.' };
    if (!RESPONDERS.has(role)) return { ok: false, error: 'Only a specialist or duty manager can respond to an L4 case.' };
    const def = L4_STEPS[step];
    if (!def) return { ok: false, error: 'Unknown step.' };
    const r = this.state.responses[record.case_id] || {};
    if (r.outcome) return { ok: false, error: 'Case already closed.' };
    if (step !== 'ack' && !r.ack) return { ok: false, error: 'Acknowledge the alert first.' };
    if (def.options && !def.options[value]) return { ok: false, error: `Choose an option for “${def.label}”.` };
    if (step === 'outcome') {
      const missing = ['contact', 'emergency', 'protect'].filter((k) => !r[k]);
      if (missing.length) return { ok: false, error: 'Complete first: ' + missing.map((k) => L4_STEPS[k].label.toLowerCase()).join(', ') + '.' };
      if (r.contact.value === 'no_answer') return { ok: false, error: 'Reporter not reached yet — keep trying (or record "No contact channel") before closing.' };
      if ((reason || '').trim().length < 8) return { ok: false, error: 'A reason (8+ characters) is required to close.' };
    }
    const at = new Date(this.now()).toISOString();
    r[step] = { value: value ?? true, role, at, ...(step === 'outcome' ? { reason: reason.trim() } : {}) };
    this.state.responses[record.case_id] = r;
    this.log(role, step === 'ack' ? 'alert_ack' : `l4_${step}`, record.case_id, { value: value ?? null });
    if (step === 'outcome') {
      this.state.decisions[record.case_id] = { human_decision: 'l4_response_closed', human_reason: reason.trim(), final_tier: 'L4', final_action: 'ESCALATE_L4_IMMEDIATE', decided_by_role: role, decided_at: at };
      this.log(role, 'decision', record.case_id, { decision: 'l4_response_closed', outcome: value });
    }
    this.save();
    return { ok: true, response: r };
  }

  row(rec) {
    const d = this.state.decisions[rec.case_id] || {};
    const l4 = this.state.responses[rec.case_id] || {};
    return {
      case_id: rec.case_id, predicted_tier: rec.predicted_tier, predicted_action: rec.predicted_action, confidence: rec.confidence,
      flags: rec.flags.join('|'), rationale: rec.rationale, human_decision: d.human_decision || (rec.auto_resolved ? 'auto_resolved' : ''),
      human_reason: d.human_reason || '', decided_at: d.decided_at || '', final_tier: d.final_tier || '', final_action: d.final_action || '',
      decided_by_role: d.decided_by_role || '', lane: rec.lane, ai_mode: rec.ai.mode, ai_tier: rec.ai.tier, ai_action: rec.ai.action,
      policy_refs: rec.policy_refs.join('|'), region: rec.region, country: rec.country, language: rec.language,
      submitted_utc: rec.submitted_utc, deadline_utc: rec.deadline_utc, parent_case: rec.parent_case || '',
      l4_acknowledged_at: l4.ack?.at || '', l4_reporter_contact: l4.contact?.value || '', l4_emergency_services: l4.emergency?.value || '',
      l4_protective_action: l4.protect?.value || '', l4_outcome: l4.outcome?.value || '',
    };
  }
}

const csvCell = (v) => { const s = String(v ?? ''); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
export function toCSV(rows) {
  return [EXPORT_COLUMNS.join(','), ...rows.map((r) => EXPORT_COLUMNS.map((c) => csvCell(r[c])).join(','))].join('\n');
}
