// Structured case records, human decisions, access log, retention and export.
// Persistence: browser localStorage in the prototype (per-device). Raw case data and PII are
// never persisted — only decisions and audit events keyed by case_id.

import { rank, ACTIONS, TIERS } from './policy.js';
import { ROLES } from './pii.js';

export const RETENTION_DAYS = { decisions: 365, audit: 400 };
const KEY = 'ridenova.v1';
const DAY = 864e5;

export const EXPORT_COLUMNS = ['case_id', 'predicted_tier', 'predicted_action', 'confidence', 'flags', 'rationale', 'human_decision', 'human_reason', 'decided_at',
  'final_tier', 'final_action', 'decided_by_role', 'lane', 'ai_mode', 'ai_tier', 'ai_action', 'policy_refs', 'region', 'country', 'language', 'submitted_utc', 'deadline_utc', 'parent_case'];

export class Store {
  constructor(storage = globalThis.localStorage, now = () => Date.now()) {
    this.storage = storage; this.now = now;
    this.state = { decisions: {}, audit: [] };
    try { const raw = storage?.getItem(KEY); if (raw) this.state = JSON.parse(raw); } catch { /* private mode etc. */ }
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

  row(rec) {
    const d = this.state.decisions[rec.case_id] || {};
    return {
      case_id: rec.case_id, predicted_tier: rec.predicted_tier, predicted_action: rec.predicted_action, confidence: rec.confidence,
      flags: rec.flags.join('|'), rationale: rec.rationale, human_decision: d.human_decision || (rec.auto_resolved ? 'auto_resolved' : ''),
      human_reason: d.human_reason || '', decided_at: d.decided_at || '', final_tier: d.final_tier || '', final_action: d.final_action || '',
      decided_by_role: d.decided_by_role || '', lane: rec.lane, ai_mode: rec.ai.mode, ai_tier: rec.ai.tier, ai_action: rec.ai.action,
      policy_refs: rec.policy_refs.join('|'), region: rec.region, country: rec.country, language: rec.language,
      submitted_utc: rec.submitted_utc, deadline_utc: rec.deadline_utc, parent_case: rec.parent_case || '',
    };
  }
}

const csvCell = (v) => { const s = String(v ?? ''); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
export function toCSV(rows) {
  return [EXPORT_COLUMNS.join(','), ...rows.map((r) => EXPORT_COLUMNS.map((c) => csvCell(r[c])).join(','))].join('\n');
}
