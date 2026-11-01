// Case state is the fold of an ordered event list. The reducer only applies facts; decisions
// about WHAT should happen (alerts, routing, validation) live in workbench.js.
// Severity, danger, lane, workflow, ownership, decision and execution are separate fields.

import { maxTier, rank } from './catalog.js';
import { submittedUtcMs } from '../tz.js';
import { pseudonym } from '../pii.js';

export function createState(c) {
  const received = submittedUtcMs(c);
  return {
    case_id: c.case_id, trip_id: c.trip_id, incident_id: null, reporter_ref: pseudonym(c.reporter_id),
    region: c.region_group, country: c.country, country_name: c.country_name, city: c.city, product: c.trip_context?.product || 'unknown',
    language: c.language, channel: c.channel, reporter_persona: c.reporter_role, reported_party_role: c.reported_party_role,
    received_ms: received, report_text_hint: '',
    sources: [], evidence_completeness: 'unknown', understanding: { language: c.language, supported: false, translation: 'pending' },
    ai: null, ai_history: [], confidence: 0, flags: [],
    severity: { proposed: null, current: null, reviewed: null, max_held: 'L1', provisional: true },
    danger: { status: 'none', signals: [], alerts: [], first_detected_at: null },
    policy: { version: null, applicable: [], conditions: [], mandatory_human_checks: [], conflicts: [], missing: [], not_covered: false, gap: null },
    recommendation: null,
    lane: null, queue: null, owner: null, workflow: 'awaiting_triage', escalation_reason: null,
    automation: { mode_at_routing: null, eligible: false, reasons: [], state: 'not_applicable', release_required: false },
    decisions: [], executions: [], steps: [], reassessments: [],
    handoff: { status: 'none' },
    clocks: { received_at: new Date(received).toISOString(), alert_created_at: null, alert_acknowledged_at: null, assigned_at: null, first_response_at: null, decided_at: null, executed_at: null, resolved_at: null },
    links: { candidates: [] }, link_due_ms: null,
    version: 0, history: [],
  };
}

const LIFECYCLE_FLAGS = new Set(['automation_exception', 'execution_failed', 'reopened', 'ai_disagrees_with_review']);
const setOnce = (o, k, v) => { if (!o[k]) o[k] = v; };

export function applyEvent(s, ev) {
  const p = ev.payload || {};
  s.version += 1;
  s.history.push({ seq: ev.seq, type: ev.type, at: ev.at, actor: ev.actor, summary: ev.summary || null });
  switch (ev.type) {
    case 'intake.received':
      s.sources = p.sources; s.evidence_completeness = p.evidence_completeness; s.understanding = p.understanding; s.report_text_hint = p.hint || '';
      s.links.candidates = p.candidates || []; s.incident_id = p.incident_id || null; s.link_due_ms = p.link_due_ms ?? null;
      break;
    case 'danger.detected':
      for (const sig of p.signals) if (!s.danger.signals.some((x) => x.signal === sig.signal && x.detected_at === ev.at)) s.danger.signals.push({ ...sig, detected_at: ev.at });
      s.danger.status = 'detected';
      setOnce(s.danger, 'first_detected_at', ev.at);
      break;
    case 'alert.created':
      s.danger.alerts.push({ id: p.alert_id, reason: p.reason, created_at: ev.at, acknowledged_at: null, acknowledged_by: null });
      setOnce(s.clocks, 'alert_created_at', ev.at);
      break;
    case 'alert.acknowledged': {
      const a = s.danger.alerts.find((x) => x.id === p.alert_id);
      if (a) { a.acknowledged_at = ev.at; a.acknowledged_by = ev.actor; }
      setOnce(s.clocks, 'alert_acknowledged_at', ev.at);
      s.owner = ev.actor; setOnce(s.clocks, 'assigned_at', ev.at);
      if (s.workflow !== 'resolved') s.workflow = 'under_review';
      break;
    }
    case 'ai.assessed': {
      const a = p.assessment;
      if (s.ai) s.ai_history.push(s.ai);
      s.ai = { ...a.ai, at: ev.at };
      s.policy = a.policy; s.confidence = a.confidence; s.understanding = a.understanding;
      s.flags = [...new Set([...a.flags, ...s.flags.filter((f) => LIFECYCLE_FLAGS.has(f))])];
      s.severity.proposed = a.ai.severity;
      // A new AI assessment never silently overwrites a human-reviewed severity.
      if (!s.severity.reviewed) { s.severity.current = a.floor_tier; s.severity.provisional = a.provisional; }
      else if (a.floor_tier !== s.severity.reviewed) s.flags.push('ai_disagrees_with_review');
      s.severity.max_held = maxTier(s.severity.max_held, s.severity.current);
      break;
    }
    case 'severity.raised':
      s.severity.current = p.to; s.severity.max_held = maxTier(s.severity.max_held, p.to);
      break;
    case 'routed':
      s.lane = p.lane; s.queue = p.queue; s.escalation_reason = p.reason;
      s.automation.mode_at_routing = p.mode;
      if (p.eligibility) { s.automation.eligible = p.eligibility.eligible; s.automation.reasons = p.eligibility.reasons; }
      if (p.lane === 'automation') s.automation.state = 'eligible';
      else if (p.eligibility?.eligible && p.mode === 'shadow') s.automation.state = 'shadow_eligible';
      if (s.workflow === 'awaiting_triage' || s.workflow === 'reopened') s.workflow = 'assigned';
      if (p.clear_owner) s.owner = null;
      s.recommendation = p.recommendation || s.recommendation;
      break;
    case 'automation.state':
      s.automation.state = p.state;
      if (p.state === 'sent_to_review') { s.flags = [...new Set([...s.flags, 'automation_exception'])]; s.automation.release_required = true; }
      break;
    case 'case.assigned':
      s.owner = p.owner; if (p.queue) s.queue = p.queue;
      setOnce(s.clocks, 'assigned_at', ev.at);
      if (s.workflow === 'assigned' || s.workflow === 'reopened') s.workflow = 'under_review';
      if (s.handoff.status === 'pending' && p.accept_handoff) { s.handoff.status = 'accepted'; s.handoff.accepted_at = ev.at; s.handoff.accepted_by = p.owner; }
      break;
    case 'decision.recorded':
      s.decisions.push({ ...p, at: ev.at, by: ev.actor });
      setOnce(s.clocks, 'decided_at', ev.at);
      if (p.decision === 'request_info') s.workflow = 'awaiting_information';
      break;
    case 'execution.queued':
      s.executions.push({ id: p.exec_id, action: p.action, key: p.key, status: 'queued', simulated: true, by: ev.actor, history: [{ status: 'queued', at: ev.at }] });
      break;
    case 'execution.running': case 'execution.completed': case 'execution.failed': {
      const x = s.executions.find((e) => e.id === p.exec_id);
      const st = ev.type.split('.')[1];
      if (x) { x.status = st; x.history.push({ status: st, at: ev.at, error: p.error || null }); if (p.error) x.error = p.error; if (p.receipt) x.receipt = p.receipt; }
      if (st === 'failed') s.flags = [...new Set([...s.flags, 'execution_failed'])];
      if (st === 'completed') {
        setOnce(s.clocks, 'executed_at', ev.at);
        if (p.reporter_facing) setOnce(s.clocks, 'first_response_at', ev.at);
      }
      break;
    }
    case 'response.step':
      s.steps.push({ step: p.step, value: p.value, at: ev.at, by: ev.actor });
      if (p.step === 'contact_reporter' && p.value === 'reached') setOnce(s.clocks, 'first_response_at', ev.at);
      break;
    case 'handoff.requested':
      s.handoff = { status: 'pending', from: ev.actor, to_queue: p.to_queue, kind: p.kind, reason: p.reason, requested_at: ev.at };
      break;
    case 'reassessment.recorded':
      s.reassessments.push({ ...p, at: ev.at, by: ev.actor });
      s.severity.current = p.to; s.severity.reviewed = p.to;
      s.danger.status = p.danger_assessment; // signals and alerts are preserved
      s.automation.release_required = true; s.automation.eligible = false;
      s.severity.max_held = maxTier(s.severity.max_held, p.to); // never loosens the clock
      break;
    case 'severity.reviewed':
      s.severity.reviewed = p.tier;
      break;
    case 'link.decided': {
      const l = s.links.candidates.find((x) => x.case_id === p.case_id);
      if (l) l.status = p.status;
      break;
    }
    case 'case.resolved':
      s.workflow = 'resolved'; setOnce(s.clocks, 'resolved_at', ev.at); s.resolution = { outcome: p.outcome, reason: p.reason, by: ev.actor, at: ev.at };
      if (p.danger_status) s.danger.status = p.danger_status;
      break;
    case 'case.reopened':
      s.workflow = 'reopened'; s.clocks.resolved_at = null; s.flags = [...new Set([...s.flags, 'reopened'])]; s.reopened = (s.reopened || 0) + 1;
      s.automation.release_required = true; s.owner = null;
      break;
    default: break;
  }
  return s;
}

export const isOpen = (s) => s.workflow !== 'resolved';
export const tierAtLeast = (t, min) => rank(t) >= rank(min);
