// Read models built on the server. Raw PII never leaves through these: names/phones/emails are
// masked, report text is redacted; the reveal endpoint is the only (logged) way to see a value.

import { slaStatus } from './sla.js';
import { viewLevel } from './permissions.js';
import { requiredCapability, automationEligibility } from './routing.js';
import { QUEUES, USERS, EXEC_ACTIONS, CAPABILITIES, POLICY_VERSION } from './catalog.js';
import { redactText, maskName, maskPhone, maskEmail, maskPlate } from '../pii.js';
import { policyById } from '../policy.js';
import { recommend } from './assess.js';

const DAY = 864e5;
const userName = (id) => USERS[id]?.name || id || null;

export const confidenceBand = (c) => (c < 0.6 ? 'low' : c < 0.8 ? 'medium' : 'high');
const decisionAt = (s) => s.clocks.decided_at || s.clocks.resolved_at;

// ---------- filters ----------
export const FILTER_KEYS = ['date_from', 'date_to', 'date_basis', 'region', 'country', 'product', 'language', 'reporter_persona', 'severity', 'severity_basis', 'workflow',
  'owner', 'queue', 'escalation_reason', 'evidence_gap', 'repeat_flag', 'confidence_band', 'automation_outcome', 'policy_version', 'lane', 'q'];

export function applyFilters(states, f = {}) {
  const from = f.date_from ? Date.parse(f.date_from) : null;
  const to = f.date_to ? Date.parse(f.date_to) + (f.date_to.length <= 10 ? DAY : 0) : null;
  const basis = f.severity_basis || 'current';
  const q = (f.q || '').toLowerCase();
  return states.filter((s) => {
    if (from != null || to != null) {
      const t = f.date_basis === 'decision' ? (decisionAt(s) ? Date.parse(decisionAt(s)) : null) : s.received_ms;
      if (t == null || (from != null && t < from) || (to != null && t >= to)) return false;
    }
    if (f.region && s.region !== f.region) return false;
    if (f.country && s.country !== f.country) return false;
    if (f.product && s.product !== f.product) return false;
    if (f.language && s.language !== f.language) return false;
    if (f.reporter_persona && s.reporter_persona !== f.reporter_persona) return false;
    if (f.severity && sevBy(s, basis) !== f.severity) return false;
    if (f.workflow && s.workflow !== f.workflow) return false;
    if (f.lane && s.lane !== f.lane) return false;
    if (f.owner && (f.owner === 'unowned' ? s.owner : s.owner !== f.owner)) return false;
    if (f.queue && s.queue !== f.queue) return false;
    if (f.escalation_reason && s.escalation_reason !== f.escalation_reason) return false;
    if (f.evidence_gap && (f.evidence_gap === 'any' ? s.evidence_completeness === 'complete' && s.understanding.supported : s.evidence_completeness !== f.evidence_gap)) return false;
    if (f.repeat_flag && (f.repeat_flag === 'yes') !== s.flags.includes('prior_flags')) return false;
    if (f.confidence_band && confidenceBand(s.confidence) !== f.confidence_band) return false;
    if (f.automation_outcome && s.automation.state !== f.automation_outcome) return false;
    if (f.policy_version && s.policy.version !== f.policy_version) return false;
    if (q && !(s.case_id.toLowerCase().includes(q) || s.city.toLowerCase().includes(q) || (s.ai?.category || '').includes(q) || s.trip_id.toLowerCase().includes(q))) return false;
    return true;
  });
}
export const sevBy = (s, basis) => (basis === 'proposed' ? s.severity.proposed : basis === 'reviewed' ? (s.severity.reviewed || 'not_reviewed') : s.severity.current);

// ---------- overview ----------
export function overview(states, f, now) {
  const pop = applyFilters(states, f);
  const n = pop.length;
  const cnt = (arr, fn) => arr.reduce((m, x) => { const k = fn(x); m[k] = (m[k] || 0) + 1; return m; }, {});
  const open = pop.filter((s) => s.workflow !== 'resolved');
  const newWindowStart = now - DAY;
  const sla = {};
  for (const t of ['L4', 'L3', 'L2', 'L1']) sla[t] = { on_track: 0, approaching: 0, breached: 0, met: 0, missed: 0, closed_without_response: 0 };
  for (const s of pop) { const st = slaStatus(s, now).status; sla[s.severity.max_held][st]++; }
  return {
    population: n,
    new_tickets: { count: pop.filter((s) => s.received_ms >= newWindowStart && s.received_ms <= now).length, denominator: 'received in the last 24h of the replay clock (within filters)' },
    open_backlog: { count: open.length, denominator: 'not resolved at the replay clock (within filters)' },
    severity: { proposed: cnt(pop, (s) => s.severity.proposed), current: cnt(pop, (s) => s.severity.current), reviewed: cnt(pop, (s) => s.severity.reviewed || 'not_reviewed') },
    provisional: pop.filter((s) => s.severity.provisional).length,
    handling: cnt(pop, (s) => s.lane),
    workflow: cnt(pop, (s) => s.workflow),
    alerts_unacknowledged: pop.filter((s) => s.danger.alerts.some((a) => !a.acknowledged_at)).length,
    alerts_total: pop.reduce((n2, s) => n2 + s.danger.alerts.length, 0),
    sla_by_tier: sla, sla_tier_basis: 'highest tier held (deadline never loosens)',
    automation: cnt(pop, (s) => s.automation.state),
    exceptions: { automation_exceptions: pop.filter((s) => s.flags.includes('automation_exception')).length, execution_failures: pop.filter((s) => s.executions.some((x) => x.status === 'failed')).length, reopened: pop.filter((s) => s.reopened).length },
    evidence_gaps: { missing_material: pop.filter((s) => s.evidence_completeness === 'missing_material').length, language_not_understood: pop.filter((s) => !s.understanding.supported).length },
    confidence_bands: cnt(pop, (s) => confidenceBand(s.confidence)),
  };
}

export function filterOptions(states) {
  const uniq = (fn) => [...new Set(states.map(fn).filter(Boolean))].sort();
  return { region: uniq((s) => s.region), country: uniq((s) => s.country), product: uniq((s) => s.product), language: uniq((s) => s.language), reporter_persona: uniq((s) => s.reporter_persona),
    workflow: uniq((s) => s.workflow), queue: uniq((s) => s.queue), owner: uniq((s) => s.owner), escalation_reason: uniq((s) => s.escalation_reason), automation_outcome: uniq((s) => s.automation.state),
    policy_version: uniq((s) => s.policy.version) };
}

// ---------- list + case views ----------
export function listItem(s, now) {
  const sla = slaStatus(s, now);
  return { case_id: s.case_id, severity: s.severity.current, proposed: s.severity.proposed, provisional: s.severity.provisional, lane: s.lane, queue: s.queue, owner: s.owner, owner_name: userName(s.owner), workflow: s.workflow,
    summary: s.ai?.summary, category: s.ai?.category, city: s.city, country: s.country, language: s.language, received_at: s.clocks.received_at, sla, danger: s.danger.status,
    unacked: s.danger.alerts.some((a) => !a.acknowledged_at), handoff: s.handoff.status, flags: s.flags };
}

export function caseView(s, raw, user, now, revealed = {}) {
  const level = viewLevel(user, s);
  if (!level) return null;
  if (level === 'handoff_status') {
    return { case_id: s.case_id, limited: true, severity: s.severity.current, lane: s.lane, queue: QUEUES[s.queue]?.label, workflow: s.workflow, handoff: { ...s.handoff, accepted_by: userName(s.handoff.accepted_by) }, owner_name: userName(s.owner) };
  }
  const p = raw.pii || {};
  const party = (x, key) => x ? { name: revealed[`${key}.name`] ? x.name : maskName(x.name), phone: revealed[`${key}.phone`] ? x.phone : maskPhone(x.phone), email: revealed[`${key}.email`] ? x.email : maskEmail(x.email),
    ...(x.vehicle_plate ? { vehicle_plate: revealed[`${key}.vehicle_plate`] ? x.vehicle_plate : maskPlate(x.vehicle_plate) } : {}) } : null;
  const sla = slaStatus(s, now);
  const rec = s.workflow === 'resolved' ? s.recommendation : recommend(s);
  return {
    case_id: s.case_id, trip_id: s.trip_id, incident_id: s.incident_id, version: s.version,
    region: s.region, country: s.country, country_name: s.country_name, city: s.city, product: s.product, channel: s.channel, language: s.language,
    reporter_persona: s.reporter_persona, reported_party_role: s.reported_party_role,
    report: { text: revealed.report_text ? raw.report_text : redactText(raw.report_text, raw), redacted: !revealed.report_text, original_language: raw.language,
      translation: s.ai?.translation ? { text: s.ai.translation, source: s.ai.mode === 'live' ? `Live: ${s.ai.model}` : 'fixture' } : null },
    parties: { reporter: party(p.reporter, 'reporter'), reported_party: party(p.reported_party, 'reported_party'),
      addresses: p.pickup_address ? (revealed.addresses ? `${p.pickup_address} → ${p.dropoff_address}` : `••• ${p.pickup_address.split(',').pop().replace('(fictional)', '').trim()} → •••`) : null },
    sources: s.sources.map((x) => ({ ...x, facts: x.facts.map((f) => ({ ...f, value: redactText(f.value, raw) })) })),
    evidence_completeness: s.evidence_completeness, understanding: s.understanding,
    ai: s.ai && { ...s.ai, translation: undefined }, ai_history_count: s.ai_history.length, confidence: s.confidence, confidence_band: confidenceBand(s.confidence),
    severity: s.severity, danger: s.danger, flags: s.flags,
    policy: { ...s.policy, applicable: s.policy.applicable.map((id) => ({ id, title: policyById[id]?.title, text: policyById[id]?.text })) },
    recommendation: rec && { ...rec, exec_labels: rec.exec_actions.map((a) => EXEC_ACTIONS[a]?.label) },
    lane: s.lane, queue: s.queue, queue_label: QUEUES[s.queue]?.label, required_capability: requiredCapability(s), capability_label: CAPABILITIES[requiredCapability(s)],
    owner: s.owner, owner_name: userName(s.owner), workflow: s.workflow, escalation_reason: s.escalation_reason, handoff: { ...s.handoff, from_name: userName(s.handoff.from), accepted_by_name: userName(s.handoff.accepted_by) },
    automation: { ...s.automation, live_eligibility: automationEligibility(s) },
    decisions: s.decisions.map((d) => ({ ...d, by_name: userName(d.by) })), executions: s.executions.map((x) => ({ ...x, label: EXEC_ACTIONS[x.action]?.label })),
    steps: s.steps.map((x) => ({ ...x, by_name: userName(x.by) })), reassessments: s.reassessments.map((x) => ({ ...x, by_name: userName(x.by) })),
    clocks: s.clocks, sla, links: s.links, resolution: s.resolution || null,
    history: s.history.map((h) => ({ ...h, actor_name: userName(h.actor) || h.actor })),
  };
}

// ---------- export (no PII) ----------
export const EXPORT_COLUMNS = ['case_id', 'predicted_tier', 'predicted_action', 'confidence', 'flags', 'rationale', 'human_decision', 'human_reason', 'decided_at',
  'current_severity', 'reviewed_severity', 'danger_status', 'lane', 'queue', 'owner', 'workflow', 'execution_status', 'automation_state', 'policy_version', 'evidence_completeness',
  'received_at', 'alert_created_at', 'alert_acknowledged_at', 'first_response_at', 'resolved_at', 'sla_due_at', 'sla_status', 'region', 'country', 'language', 'incident_id'];

export function exportRow(s, now) {
  const d = s.decisions[s.decisions.length - 1] || {};
  const r = s.reassessments[s.reassessments.length - 1];
  const sla = slaStatus(s, now);
  return {
    case_id: s.case_id, predicted_tier: s.severity.proposed, predicted_action: s.recommendation?.proposed_action || '', confidence: s.confidence, flags: s.flags.join('|'), rationale: s.ai?.rationale || '',
    human_decision: r ? `reassess ${r.from}->${r.to}` : d.decision || (s.automation.state === 'completed' ? 'automated' : ''), human_reason: r ? r.reason : d.reason || '', decided_at: r ? r.at : d.at || '',
    current_severity: s.severity.current, reviewed_severity: s.severity.reviewed || '', danger_status: s.danger.status, lane: s.lane, queue: s.queue, owner: s.owner || '', workflow: s.workflow,
    execution_status: s.executions.map((x) => `${x.action}:${x.status}`).join('|'), automation_state: s.automation.state, policy_version: s.policy.version || POLICY_VERSION, evidence_completeness: s.evidence_completeness,
    received_at: s.clocks.received_at, alert_created_at: s.clocks.alert_created_at || '', alert_acknowledged_at: s.clocks.alert_acknowledged_at || '', first_response_at: s.clocks.first_response_at || '',
    resolved_at: s.clocks.resolved_at || '', sla_due_at: sla.due_at, sla_status: sla.status, region: s.region, country: s.country, language: s.language, incident_id: s.incident_id || '',
  };
}
const cell = (v) => { const x = String(v ?? ''); return /[",\n]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x; };
export const toCSV = (rows) => [EXPORT_COLUMNS.join(','), ...rows.map((r) => EXPORT_COLUMNS.map((c) => cell(r[c])).join(','))].join('\n');
